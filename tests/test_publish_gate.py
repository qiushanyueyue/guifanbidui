from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.models import QuarantinedStandardModel, StagingStandardModel, StandardV2Model
from app.sync.v2_pipeline import publish_staging, stage_record

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rebuild_v2.py"
spec = importlib.util.spec_from_file_location("rebuild_v2_under_test", SCRIPT)
rebuild_v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebuild_v2)


@pytest.fixture
def factory(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(rebuild_v2, "SessionLocal", session_factory)
    return session_factory


def _stage(db, code, name, *, relation=None, status="现行"):
    stage_record(
        db,
        source_name="csres",
        source_url=f"https://example.test/{code}",
        raw_code=code,
        raw_name=name,
        raw_status=status,
        raw_text="公开目录元数据",
        raw_relation_text=relation,
    )


def _run(monkeypatch, tmp_path, *args):
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["rebuild_v2.py", "--output", str(output), *args])
    code = rebuild_v2.main()
    return code, json.loads(output.read_text(encoding="utf-8"))


def test_clean_publication_is_committed(factory, monkeypatch, tmp_path):
    with factory() as db:
        _stage(db, "GB 50016-2014", "建筑设计防火规范")
        db.commit()
    code, report = _run(monkeypatch, tmp_path)
    assert code == 0
    assert report["publication"] == "committed"
    with factory() as db:
        assert db.query(StandardV2Model).count() == 1


def test_failed_gate_rolls_back_and_names_the_bad_edge(factory, monkeypatch, tmp_path):
    with factory() as db:
        _stage(db, "GB 50016-2014", "建筑设计防火规范", status="现行")
        db.commit()
        publish_staging(db)
        _stage(db, "GB 50001-2020", "新版规范", relation="被 GB 50002-2010 替代", status="废止")
        _stage(db, "GB 50002-2010", "旧版规范")
        db.commit()
    code, report = _run(monkeypatch, tmp_path)
    assert code == 2
    assert report["publishable"] is False
    assert report["publication"] == "rolled_back"
    assert report["relation_issues"]["reverse_chronology"] == [
        {"from": "GB 50001-2020", "to": "GB 50002-2010", "raw_relation_text": "被 GB 50002-2010 替代"}
    ]
    with factory() as db:
        # Previously published data stays; the rejected batch stays staged for a retry.
        assert [row.base_code for row in db.query(StandardV2Model).all()] == ["GB 50016-2014"]
        assert db.query(StagingStandardModel).count() == 3


def test_failed_gate_also_reverts_quarantine_retry(factory, monkeypatch, tmp_path):
    with factory() as db:
        _stage(db, "GB 50001-2020", "新版规范", relation="被 GB 50002-2010 替代", status="废止")
        _stage(db, "GB 50002-2010", "旧版规范")
        db.add(QuarantinedStandardModel(normalized_code="X", reason_code="invalid_code", reason_detail="retry me"))
        db.commit()
    code, _report = _run(monkeypatch, tmp_path, "--retry-quarantine")
    assert code == 2
    with factory() as db:
        assert db.query(QuarantinedStandardModel).one().resolved_at is None
        assert db.query(StandardV2Model).count() == 0
