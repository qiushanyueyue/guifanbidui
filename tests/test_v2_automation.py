from pathlib import Path

from scripts import verify_v2_csres
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.models import StandardV2Model, StagingStandardModel, SyncCheckpointModel, SyncRunModel
from app.sources.base import SourceRecord


ROOT = Path(__file__).resolve().parents[1]


def test_completed_csres_checkpoint_wraps_to_first_candidate():
    assert verify_v2_csres.resume_start(candidate_count=120, checkpoint_offset=120) == 0


def test_partial_csres_checkpoint_resumes_from_saved_offset():
    assert verify_v2_csres.resume_start(candidate_count=120, checkpoint_offset=25) == 25


def test_unknown_cycle_skips_codes_with_an_already_verified_edition():
    assert verify_v2_csres.unresolved_unknown_codes(
        {"GB 50038-2005", "GB 50096-2011"},
        {"GB 50038-2005"},
    ) == {"GB 50096-2011"}


def test_scheduled_workflows_publish_v2_only():
    workflow_names = ["standards-daily.yml", "standards-weekly.yml", "standards-monthly.yml"]
    contents = [
        (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        for name in workflow_names
    ]

    for content in contents:
        assert "scripts/verify_v2_csres.py" in content
        assert "scripts/rebuild_v2.py" in content
        assert "--run-id-file" in content
        assert "scripts/check_sync_health.py" in content
        assert content.index("scripts/rebuild_v2.py") < content.index("scripts/check_sync_health.py")
        assert "scripts/sync_incremental.py" not in content
        assert "scripts/verify_existing.py" not in content
        assert "scripts/full_reconcile.py" not in content

    assert "--unknown-only" in contents[0]
    assert "--unknown-only" in contents[1]
    assert "--resume" in contents[0]
    assert "--resume" in contents[1]
    assert "--resume" in contents[2]


def test_hobby_cron_is_not_more_frequent_than_daily():
    config = (ROOT / "vercel.json").read_text(encoding="utf-8")
    assert '"schedule": "0 0 * * *"' in config


def test_unknown_cursor_survives_removed_records_and_wraps():
    assert verify_v2_csres.unknown_resume_start(['GB 1-2020', 'GB 3-2020'], 'GB 2-2020') == 1
    assert verify_v2_csres.unknown_resume_start(['GB 1-2020', 'GB 3-2020'], 'GB 3-2020') == 0
    assert verify_v2_csres.unknown_resume_start([], 'GB 3-2020') == 0


def test_unknown_batches_advance_past_failures_without_moving_monthly_cursor(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    for number in (1, 2, 3):
        code = f'GB {number}-2020'
        db.add(StagingStandardModel(source_name='soujianzhu', raw_code=code, raw_name='测试规范', content_hash=str(number)))
        db.add(StandardV2Model(code=code, normalized_code=code, base_code=code, standard_prefix='GB', standard_number=str(number), standard_year='2020', name='测试规范', normalized_name='测试规范', status='unknown'))
    db.add(SyncCheckpointModel(source_name='csres', scope='verify_v2', page_number=10, last_record_id='monthly'))
    db.commit()
    observed = []
    monkeypatch.setattr(verify_v2_csres, 'SessionLocal', lambda: db)
    monkeypatch.setattr(verify_v2_csres.CsresSource, 'search', lambda self, code: observed.append(code) or [])
    monkeypatch.setattr('sys.argv', ['verify_v2_csres', '--unknown-only', '--resume', '--limit', '2'])
    assert verify_v2_csres.main() == 0
    assert observed == ['GB 1-2020', 'GB 2-2020']
    assert verify_v2_csres.main() == 0
    assert observed == ['GB 1-2020', 'GB 2-2020', 'GB 3-2020']
    assert verify_v2_csres.main() == 0
    assert observed[-2:] == ['GB 1-2020', 'GB 2-2020']
    monthly = db.query(SyncCheckpointModel).filter_by(scope='verify_v2').one()
    assert (monthly.page_number, monthly.last_record_id) == (10, 'monthly')
    assert all(run.failed == run.found for run in db.query(SyncRunModel))
    monkeypatch.setattr('sys.argv', ['verify_v2_csres', '--code', 'GB 3-2020'])
    assert verify_v2_csres.main() == 0
    assert db.query(SyncCheckpointModel).filter_by(scope='verify_v2_unknown').one().last_record_id == 'GB 2-2020'


def test_best_exact_only_accepts_documented_gb_identity_evolution():
    alias = SourceRecord(source_name='csres', code='GB/T 50010-2010', name='混凝土结构设计标准（2024年版）')
    assert verify_v2_csres._best_exact([alias], 'GB 50010-2010', '') is alias
    assert verify_v2_csres._best_exact([alias], 'GB 50010-2002', '') is None
    assert verify_v2_csres._best_exact([alias], 'JGJ 50010-2010', '') is None
    exact = SourceRecord(source_name='csres', code='GB 50010-2010', name='混凝土结构设计规范')
    assert verify_v2_csres._best_exact([alias, exact], exact.code, '') is exact


def test_wrong_detail_identity_cannot_replace_search_evidence(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    search = SourceRecord(source_name='csres', code='GB 1-2020', name='正确规范', source_status='现行', source_url='http://www.csres.com/detail/1.html')
    detail = SourceRecord(source_name='csres', code='GB 2-2020', name='错误规范', source_status='废止')
    monkeypatch.setattr(verify_v2_csres, 'SessionLocal', lambda: db)
    monkeypatch.setattr(verify_v2_csres.CsresSource, 'search', lambda self, code: [search])
    monkeypatch.setattr(verify_v2_csres.CsresSource, 'fetch_detail', lambda self, url: detail)
    monkeypatch.setattr('sys.argv', ['verify_v2_csres', '--code', search.code])
    assert verify_v2_csres.main() == 0
    row = db.query(StagingStandardModel).one()
    assert (row.raw_code, row.raw_name, row.raw_status) == ('GB 1-2020', '正确规范', '现行')
