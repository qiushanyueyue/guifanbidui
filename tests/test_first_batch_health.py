from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints import _health_payload
from app.models.base import Base
from app.models.models import StandardV2Model, SyncRunModel
from scripts import check_sync_health, verify_v2_csres


def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def standard(status='current'):
    return StandardV2Model(code='GB 1-2020', normalized_code='GB 1-2020', base_code='GB 1-2020',
                           standard_prefix='GB', standard_number='1', standard_year='2020',
                           name='测试规范', normalized_name='测试规范', status=status,
                           data_quality_status='publishable')


def batch(found=25, failed=0, status='success', days=0):
    finished = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    return SyncRunModel(source='csres', status=status, found=found, failed=failed,
                        started_at=finished, finished_at=finished)


@pytest.mark.parametrize('found,failed,status,expected', [
    (25,25,'partial',False), (25,2,'partial',True), (100,50,'partial',True),
    (100,51,'partial',False), (0,0,'success',True), (0,0,'failed',False),
    (0,0,'partial',False), (1,0,'running',False), (10,11,'partial',False),
])
def test_batch_quality_gate(found, failed, status, expected):
    assert check_sync_health.batch_is_healthy(batch(found, failed, status), 0.5) is expected


def test_quality_gate_checks_the_requested_batch_not_latest(monkeypatch, tmp_path):
    db = db_session()
    bad = batch(25,25,'partial')
    good = batch()
    db.add_all([bad,good]); db.commit()
    run_file = tmp_path/'run-id'; run_file.write_text(str(bad.id))
    monkeypatch.setattr(check_sync_health, 'SessionLocal', lambda: db)
    monkeypatch.setattr('sys.argv', ['check_sync_health', '--run-id-file', str(run_file)])
    assert check_sync_health.main() == 1


def test_verify_writes_batch_id_and_all_failures_remain_available_for_gate(monkeypatch, tmp_path):
    db = db_session()
    run_file = tmp_path/'run-id'
    monkeypatch.setattr(verify_v2_csres, 'SessionLocal', lambda: db)
    monkeypatch.setattr(verify_v2_csres.CsresSource, 'search', lambda self, code: [])
    monkeypatch.setattr('sys.argv', ['verify_v2_csres', '--code', 'GB 1-2020', '--run-id-file', str(run_file)])
    assert verify_v2_csres.main() == 0  # allow publishing before quality failure
    run = db.get(SyncRunModel, int(run_file.read_text()))
    assert run.found == run.failed == 1
    assert not check_sync_health.batch_is_healthy(run, 0.5)


def test_health_separates_serving_api_from_poor_coverage(monkeypatch):
    monkeypatch.setenv('STANDARDS_DATASET','v2')
    db = db_session(); db.add_all([standard('unknown'), batch(25,25,'partial')]); db.commit()
    health = _health_payload(db)
    assert health.status == health.database == 'ok'
    assert health.data.status == 'degraded'
    assert health.data.unknown_rate == health.data.latest_sync_failure_rate == 1.0
    assert 'high_unknown_rate' in health.data.reasons
    assert 'unhealthy_latest_sync' in health.data.reasons


@pytest.mark.parametrize('days,reason', [(None,'no_successful_sync'), (8,'stale_sync')])
def test_health_reports_missing_or_stale_refresh(monkeypatch, days, reason):
    monkeypatch.setenv('STANDARDS_DATASET','v2')
    db=db_session(); db.add(standard())
    if days is not None: db.add(batch(days=days))
    db.commit()
    assert reason in _health_payload(db).data.reasons


def test_empty_database_is_not_healthy_and_zero_candidate_run_does_not_refresh(monkeypatch):
    monkeypatch.setenv('STANDARDS_DATASET','v2')
    db=db_session(); db.add(batch(found=0)); db.commit()
    health = _health_payload(db)
    assert health.data.status == 'degraded'
    assert set(health.data.reasons) == {'empty_dataset','no_successful_sync'}


def test_recent_partial_batch_with_usable_evidence_can_be_healthy(monkeypatch):
    monkeypatch.setenv('STANDARDS_DATASET','v2')
    db=db_session(); db.add_all([standard(),batch(25,2,'partial')]); db.commit()
    health=_health_payload(db)
    assert health.data.status == 'ok'
    assert health.data.last_successful_sync is not None


def test_database_error_returns_degraded_health_without_internal_error(monkeypatch):
    db=db_session()
    monkeypatch.setattr(db,'execute',lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('private connection detail')))
    health=_health_payload(db)
    assert health.database == 'error'
    assert health.data.reasons == ['database_unavailable']
    assert 'private connection detail' not in health.model_dump_json()
