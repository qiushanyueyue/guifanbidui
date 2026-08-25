#!/usr/bin/env python3
"""Local-only receiver for metadata read through the user's logged-in browser.

The receiver never accepts cookies or credentials.  It binds to loopback,
requires a per-run token, and stores only directory metadata in staging.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", required=True)
    return parser.parse_args()


ARGS = parse_args()
database_path = Path(ARGS.database).resolve()
os.environ["SQLITE_DATABASE_PATH"] = str(database_path)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.base import Base, SessionLocal, engine  # noqa: E402
from app.models.models import SyncCheckpointModel, SyncRunModel  # noqa: E402
from app.services.standard_normalizer import clean_standard_name, split_standard_reference  # noqa: E402
from app.sync.v2_pipeline import stage_record  # noqa: E402

Base.metadata.create_all(bind=engine)


class State:
    inserted = 0
    unchanged = 0
    failed = 0
    run_id: int | None = None


def _start_run() -> None:
    with SessionLocal() as db:
        run = SyncRunModel(source="soujianzhu", mode="full", status="running")
        db.add(run)
        db.commit()
        State.run_id = run.id


def _name_from_title(title: str) -> str:
    quoted = re.search(r"《([^》]+)》", title)
    return clean_standard_name(quoted.group(1) if quoted else title)


class Handler(BaseHTTPRequestHandler):
    server_version = "StandardsStagingReceiver/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _authorized(self) -> bool:
        return self.headers.get("X-Ingest-Token", "") == ARGS.token

    def _json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self._json(404, {"error": "not_found"})
            return
        self._json(200, {"status": "ok", "database": database_path.name})

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._json(401, {"error": "unauthorized"})
            return
        if self.path == "/finish":
            self._finish()
            return
        if self.path != "/ingest":
            self._json(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            records = payload.get("records") or []
            scope = str(payload.get("scope") or "unknown")[:300]
            page = int(payload.get("page") or 1)
            with SessionLocal() as db:
                for item in records:
                    title = str(item.get("title") or "").strip()
                    name, code, edition = split_standard_reference(title)
                    row, inserted = stage_record(
                        db,
                        source_name="soujianzhu",
                        source_url=str(item.get("url") or "") or None,
                        source_record_id=str(item.get("record_id") or "") or None,
                        raw_code=code.normalized if code else None,
                        raw_name=name or _name_from_title(title),
                        raw_edition=edition.edition,
                        raw_status=None,
                        raw_text=title,
                        raw_implement_date=str(item.get("implement_date") or "") or None,
                        sync_run_id=State.run_id,
                    )
                    row.raw_text = json.dumps(item, ensure_ascii=False, sort_keys=True)
                    State.inserted += int(inserted)
                    State.unchanged += int(not inserted)
                checkpoint = (
                    db.query(SyncCheckpointModel)
                    .filter(SyncCheckpointModel.source_name == "soujianzhu")
                    .filter(SyncCheckpointModel.scope == scope)
                    .first()
                )
                if checkpoint is None:
                    checkpoint = SyncCheckpointModel(source_name="soujianzhu", scope=scope)
                    db.add(checkpoint)
                checkpoint.page_number = page
                checkpoint.cursor = str(payload.get("next_url") or "") or None
                checkpoint.status = "complete" if payload.get("is_last") else "running"
                checkpoint.updated_at = datetime.utcnow()
                db.commit()
            self._json(200, {"accepted": len(records), "inserted_total": State.inserted})
        except Exception as exc:
            State.failed += 1
            self._json(400, {"error": exc.__class__.__name__, "message": str(exc)[:300]})

    def _finish(self) -> None:
        with SessionLocal() as db:
            run = db.get(SyncRunModel, State.run_id)
            if run is not None:
                run.finished_at = datetime.utcnow()
                run.status = "success" if State.failed == 0 else "partial"
                run.found = State.inserted + State.unchanged
                run.inserted = State.inserted
                run.unchanged = State.unchanged
                run.failed = State.failed
                db.commit()
        self._json(
            200,
            {"status": "finished", "inserted": State.inserted, "unchanged": State.unchanged, "failed": State.failed},
        )
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def main() -> None:
    _start_run()
    server = ThreadingHTTPServer(("127.0.0.1", ARGS.port), Handler)
    print(f"receiver ready on 127.0.0.1:{ARGS.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
