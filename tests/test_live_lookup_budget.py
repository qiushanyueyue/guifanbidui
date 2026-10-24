from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import endpoints
from app.models.base import Base
from app.models.enums import StandardStatus, VerificationLevel
from app.models.models import LiveLookupAttemptModel, StandardV2Model
from app.models.schemas import VerifyRequest
from app.services.live_verification import LiveVerification, attempt_outcome, verify_live
from app.sources.base import HttpSource, RequestTimeout, SourceRecord


class RecordingSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.timeouts: list[float] = []

    def request(self, method, url, **kwargs):
        self.timeouts.append(kwargs["timeout"])
        raise requests.Timeout("simulated slow source")


class SlowSource(HttpSource):
    name = "csres"

    def search(self, query):
        self._request("GET", "https://example.invalid/search", params={"q": query})
        return []


def test_query_deadline_bounds_timeout_and_disables_retries():
    session = RecordingSession()
    source = SlowSource(session=session, min_interval=0)
    source.max_retries = 0
    source.deadline = time.monotonic() + 2
    with pytest.raises(RequestTimeout):
        source.search("GB 50016-2014")
    assert len(session.timeouts) == 1
    assert session.timeouts[0] <= 2


def test_exhausted_deadline_skips_network_entirely():
    session = RecordingSession()
    source = SlowSource(session=session, min_interval=0)
    source.deadline = time.monotonic() - 1
    with pytest.raises(RequestTimeout):
        source.search("GB 50016-2014")
    assert session.timeouts == []


def test_scheduled_sync_keeps_default_retries(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    session = RecordingSession()
    source = SlowSource(session=session, min_interval=0)
    with pytest.raises(RequestTimeout):
        source.search("GB 50016-2014")
    assert len(session.timeouts) == 4
    assert all(timeout == 10.0 for timeout in session.timeouts)


def test_verify_live_applies_deadline_to_http_adapters():
    built: list[SlowSource] = []

    def factory(name):
        source = SlowSource(session=RecordingSession(), min_interval=0)
        source.name = name
        built.append(source)
        return source

    deadline = time.monotonic() + 5
    standard = StandardV2Model(code="GB 50016-2014", normalized_code="GB 50016-2014", name="建筑设计防火规范")
    assert verify_live(standard, factory=factory, deadline=deadline) is None
    assert built and all(source.deadline == deadline and source.max_retries == 0 for source in built)


def test_attempt_outcome_distinguishes_budget_exhaustion():
    found = LiveVerification(StandardStatus.CURRENT, VerificationLevel.SINGLE_SOURCE, ())
    assert attempt_outcome(found, time.monotonic() - 1) == "found"
    assert attempt_outcome(None, time.monotonic() - 1) == "budget_exhausted"
    assert attempt_outcome(None, time.monotonic() + 60) == "miss"
    assert attempt_outcome(None, None) == "miss"


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _unknown_standard() -> StandardV2Model:
    return StandardV2Model(
        code="GB 50016-2014",
        normalized_code="GB 50016-2014",
        base_code="GB 50016-2014",
        standard_prefix="GB",
        standard_number="50016",
        standard_year="2014",
        name="建筑设计防火规范",
        normalized_name="建筑设计防火规范",
        status="unknown",
        verification_level="unverified",
        revision_status="original",
        mandatory_clause_status="unknown",
        data_quality_status="publishable",
    )


@pytest.fixture
def live_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "true")
    monkeypatch.setenv("STANDARDS_DATASET", "v2")
    monkeypatch.setenv("LIVE_LOOKUP_RETRY_HOURS", "24")


def test_unresolved_standard_is_not_refreshed_again_within_retry_window(monkeypatch, live_enabled):
    db = _db()
    db.add(_unknown_standard())
    db.commit()
    calls = []

    def fake_verify_live(standard, *, source_urls=None, deadline=None):
        calls.append(deadline)
        return None

    monkeypatch.setattr(endpoints, "verify_live", fake_verify_live)
    request = VerifyRequest(code="GB 50016-2014", name="建筑设计防火规范")

    first = endpoints.verify_standard(request, db)
    second = endpoints.verify_standard(request, db)

    assert len(calls) == 1 and calls[0] is not None
    assert first.status == second.status == StandardStatus.UNKNOWN
    attempt = db.query(LiveLookupAttemptModel).one()
    assert attempt.lookup_key == "code:GB 50016-2014"
    assert attempt.outcome == "miss"

    attempt.attempted_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=25)
    db.commit()
    endpoints.verify_standard(request, db)
    assert len(calls) == 2


def test_missing_code_discovery_is_not_repeated_within_retry_window(monkeypatch, live_enabled):
    db = _db()
    db.add(_unknown_standard())  # keep the V2 dataset selected
    db.commit()
    calls = []

    def fake_discover_live(*, code, name, deadline=None):
        calls.append(code)
        return None

    monkeypatch.setattr(endpoints, "discover_live", fake_discover_live)
    request = VerifyRequest(code="GB 99999-2020")

    assert endpoints.verify_standard(request, db).match_type == "not_found"
    assert endpoints.verify_standard(request, db).match_type == "not_found"
    assert calls == ["GB 99999-2020"]


def test_successful_discovery_is_persisted_and_recorded(monkeypatch, live_enabled):
    db = _db()
    db.add(_unknown_standard())
    db.commit()
    record = SourceRecord(
        source_name="csres",
        code="GB 50308-2017",
        name="城市轨道交通工程测量规范",
        source_status="现行",
        source_url="http://www.csres.com/detail/300264.html",
    )
    outcome = LiveVerification(StandardStatus.CURRENT, VerificationLevel.SINGLE_SOURCE, (record,))
    monkeypatch.setattr(endpoints, "discover_live", lambda **_kwargs: outcome)

    response = endpoints.verify_standard(VerifyRequest(code="GB 50308-2017"), db)

    assert response.status == StandardStatus.CURRENT
    assert db.query(LiveLookupAttemptModel).one().outcome == "found"
