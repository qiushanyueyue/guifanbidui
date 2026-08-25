#!/usr/bin/env python3
"""Conservatively enrich staged Soujianzhu candidates with CSRES metadata."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.base import SessionLocal  # noqa: E402
from app.models.models import StagingStandardModel, SyncCheckpointModel, SyncRunModel  # noqa: E402
from app.services.standard_normalizer import normalize_standard_code, normalized_name  # noqa: E402
from app.sources.base import SourceError  # noqa: E402
from app.sources.csres import CsresSource, SEARCH_URL  # noqa: E402
from app.sync.v2_pipeline import stage_record  # noqa: E402


def resume_start(*, candidate_count: int, checkpoint_offset: int | None) -> int:
    """Return a bounded cursor and start a new verification cycle at EOF."""

    if candidate_count <= 0:
        return 0
    offset = max(0, checkpoint_offset or 0)
    return 0 if offset >= candidate_count else offset


def _best_exact(records, code: str, expected_name: str):
    exact = [row for row in records if row.normalized_code == code]
    if not exact:
        return None
    non_translations = [row for row in exact if "英文版" not in row.name]
    candidates = non_translations or exact
    wanted_name = normalized_name(expected_name)
    return sorted(candidates, key=lambda row: (normalized_name(row.name) != wanted_name, len(row.name)))[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--code",
        action="append",
        default=[],
        help="verify one exact code (repeatable), including codes absent from Soujianzhu",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    delay = float(os.getenv("CRAWLER_DELAY_SECONDS", "1.2"))
    adapter = CsresSource(min_interval=max(0.8, delay), timeout=12)
    with SessionLocal() as db:
        candidates = (
            db.query(StagingStandardModel)
            .filter(StagingStandardModel.source_name == "soujianzhu")
            .filter(StagingStandardModel.raw_code.isnot(None))
            .order_by(StagingStandardModel.id)
            .all()
        )
        unique: dict[str, StagingStandardModel] = {}
        for candidate in candidates:
            code = normalize_standard_code(candidate.raw_code)
            if code:
                unique.setdefault(code, candidate)
        explicit_codes = [normalize_standard_code(code) for code in args.code]
        codes = list(dict.fromkeys(code for code in explicit_codes if code)) or list(unique)
        checkpoint = (
            db.query(SyncCheckpointModel)
            .filter(SyncCheckpointModel.source_name == "csres")
            .filter(SyncCheckpointModel.scope == "verify_v2")
            .first()
        )
        explicit_mode = bool(explicit_codes)
        start = 0 if explicit_mode or not args.resume else resume_start(
            candidate_count=len(codes),
            checkpoint_offset=checkpoint.page_number if checkpoint else None,
        )
        selected = codes[start : start + max(1, args.limit)]
        run = SyncRunModel(
            source="csres",
            mode="verify_v2_explicit" if explicit_mode else "verify_v2",
            status="running",
            found=len(selected),
        )
        db.add(run)
        db.commit()
        for offset, code in enumerate(selected, start=start):
            candidate = unique.get(code)
            expected_name = candidate.raw_name if candidate is not None else ""
            try:
                search_rows = adapter.search(code)
                record = _best_exact(search_rows, code, expected_name or "")
                if record is None:
                    failed, _ = stage_record(
                        db,
                        source_name="csres",
                        source_url=f"{SEARCH_URL}?keyword={code}",
                        raw_code=code,
                        raw_name=expected_name,
                        raw_text="search returned no exact code",
                        sync_run_id=run.id,
                    )
                    failed.parse_status = "not_found"
                    failed.parse_error = "NotFound: exact normalized code absent"
                    run.failed += 1
                else:
                    search_status = record.source_status
                    if record.source_url:
                        try:
                            detail = adapter.fetch_detail(record.source_url)
                            if detail is not None:
                                detail.source_status = detail.source_status or search_status
                                if expected_name and normalized_name(detail.name) != normalized_name(expected_name):
                                    detail.name = record.name
                                record = detail
                        except SourceError as exc:
                            logging.warning("CSRES detail fallback code=%s error=%s", code, exc.category)
                    staged, inserted = stage_record(
                        db,
                        source_name="csres",
                        source_url=record.source_url,
                        source_record_id=(record.source_url or "").rsplit("/", 1)[-1],
                        raw_code=record.normalized_code,
                        raw_name=record.name,
                        raw_edition=record.edition,
                        raw_status=str(record.source_status or ""),
                        raw_text=json.dumps(record.raw_payload, ensure_ascii=False, sort_keys=True),
                        raw_publish_date=record.publish_date,
                        raw_implement_date=record.implement_date,
                        raw_abolish_date=record.abolish_date,
                        raw_relation_text=(record.raw_payload or {}).get("raw_replacement_text"),
                        sync_run_id=run.id,
                    )
                    staged.parse_status = "pending"
                    run.inserted += int(inserted)
                    run.unchanged += int(not inserted)
            except SourceError as exc:
                failed, _ = stage_record(
                    db,
                    source_name="csres",
                    source_url=f"{SEARCH_URL}?keyword={code}",
                    raw_code=code,
                    raw_name=expected_name,
                    raw_text=f"source error: {exc.category}",
                    sync_run_id=run.id,
                )
                failed.parse_status = "failed"
                failed.parse_error = f"{exc.category}: {exc.__class__.__name__}"
                run.failed += 1
            if not explicit_mode:
                if checkpoint is None:
                    checkpoint = SyncCheckpointModel(source_name="csres", scope="verify_v2")
                    db.add(checkpoint)
                checkpoint.page_number = offset + 1
                checkpoint.last_record_id = code
                checkpoint.status = "running"
                checkpoint.updated_at = datetime.utcnow()
            db.commit()
        run.finished_at = datetime.utcnow()
        run.status = "success" if run.failed == 0 else "partial"
        if checkpoint is not None and not explicit_mode:
            checkpoint.status = "complete" if start + len(selected) >= len(codes) else "running"
        db.commit()
        print(
            {
                "selected": run.found,
                "inserted": run.inserted,
                "unchanged": run.unchanged,
                "failed": run.failed,
                "next_offset": start + len(selected),
                "total_candidates": len(codes),
            }
        )
        return 0 if run.status in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
