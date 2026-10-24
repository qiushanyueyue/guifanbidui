from __future__ import annotations

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import endpoints
from app.main import InMemoryRateLimitMiddleware
from app.models.base import Base
from app.models.models import LiveLookupAttemptModel, StandardV2Model, StandardV2RelationModel, SyncRunModel
from app.repositories.standard_repo import contains_pattern
from app.repositories.standard_v2_repo import StandardV2Repo
from app.services.live_verification import recently_attempted


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _v2(code: str, name: str, **overrides) -> StandardV2Model:
    prefix, _, rest = code.partition(" ")
    number, _, year = rest.partition("-")
    values = dict(
        code=code, normalized_code=code, base_code=code, standard_prefix=prefix,
        standard_number=number, standard_year=year, name=name, normalized_name=name,
        status="current", verification_level="single_source", revision_status="original",
        mandatory_clause_status="unknown", data_quality_status="publishable",
    )
    values.update(overrides)
    return StandardV2Model(**values)


def test_like_wildcards_in_user_input_are_literal():
    assert contains_pattern("50%_\\") == "%50\\%\\_\\\\%"
    db = _db()
    db.add(_v2("GB 50016-2014", "建筑设计防火规范"))
    db.commit()
    assert StandardV2Repo.search(db, "%") == []
    assert StandardV2Repo.search(db, "_") == []


def test_public_sync_status_does_not_expose_error_messages():
    db = _db()
    db.add(SyncRunModel(source="csres", status="failed", error_message="Traceback: http://internal/secret-path"))
    db.commit()
    run = db.query(SyncRunModel).one()
    run.finished_at = run.started_at
    db.commit()
    latest = endpoints.get_sync_status(db).latest
    assert "error_message" not in latest
    assert latest["status"] == "failed"


def test_missing_attempts_table_does_not_break_lookup():
    db = _db()
    LiveLookupAttemptModel.__table__.drop(db.get_bind())
    assert recently_attempted(db, "code:GB 50016-2014") is False


def test_replaced_by_codes_are_loaded_in_relation_order():
    db = _db()
    old = _v2("GB 50045-95", "高层民用建筑设计防火规范", status="replaced", standard_year="95")
    first = _v2("GB 50016-2014", "建筑设计防火规范")
    second = _v2("GB 55037-2022", "建筑防火通用规范")
    db.add_all([old, first, second])
    db.flush()
    db.add_all([
        StandardV2RelationModel(source_standard_id=old.id, target_standard_id=first.id, relation_type="replaced_by"),
        StandardV2RelationModel(source_standard_id=old.id, target_standard_id=second.id, relation_type="replaced_by"),
    ])
    db.commit()
    assert endpoints._result_v2(db, old).replaced_by == "GB 50016-2014; GB 55037-2022"


def test_dataset_probe_runs_once_per_session(monkeypatch):
    monkeypatch.setenv("STANDARDS_DATASET", "auto")
    db = _db()
    calls = []
    monkeypatch.setattr(StandardV2Repo, "has_data", staticmethod(lambda _db: calls.append(1) or True))
    assert endpoints._use_v2(db) and endpoints._use_v2(db)
    assert len(calls) == 1


async def _call(middleware, headers=None, client=("10.0.0.1", 1234)):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "path": "/api/search", "headers": headers or [], "client": client}
    await middleware(scope, receive, send)
    return next(message["status"] for message in sent if message["type"] == "http.response.start")


async def _ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def test_rate_limit_uses_platform_client_ip_when_trusted():
    middleware = InMemoryRateLimitMiddleware(_ok_app, limit=1, trust_proxy_ip=True)
    proxy = ("10.0.0.1", 1234)
    assert asyncio.run(_call(middleware, [(b"x-real-ip", b"203.0.113.5")], proxy)) == 200
    assert asyncio.run(_call(middleware, [(b"x-real-ip", b"203.0.113.6")], proxy)) == 200
    assert asyncio.run(_call(middleware, [(b"x-real-ip", b"203.0.113.5")], proxy)) == 429


def test_rate_limit_ignores_spoofable_headers_when_not_trusted():
    middleware = InMemoryRateLimitMiddleware(_ok_app, limit=1)
    assert asyncio.run(_call(middleware, [(b"x-real-ip", b"203.0.113.5")])) == 200
    assert asyncio.run(_call(middleware, [(b"x-real-ip", b"203.0.113.6")])) == 429


def test_idle_rate_limit_keys_are_swept():
    middleware = InMemoryRateLimitMiddleware(_ok_app, limit=5, window_seconds=1)
    asyncio.run(_call(middleware, client=("198.51.100.1", 1)))
    middleware.events["198.51.100.1"][0] -= 5
    middleware._last_sweep -= 5
    asyncio.run(_call(middleware, client=("198.51.100.2", 1)))
    assert "198.51.100.1" not in middleware.events
