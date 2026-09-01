from pathlib import Path

from scripts import verify_v2_csres


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
        assert "scripts/sync_incremental.py" not in content
        assert "scripts/verify_existing.py" not in content
        assert "scripts/full_reconcile.py" not in content

    assert "--unknown-only" in contents[0]
    assert "--unknown-only" in contents[1]
    assert "--resume" in contents[2]


def test_hobby_cron_is_not_more_frequent_than_daily():
    config = (ROOT / "vercel.json").read_text(encoding="utf-8")
    assert '"schedule": "0 0 * * *"' in config
