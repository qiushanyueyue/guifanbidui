from pathlib import Path

from app.services.extractor import extract_standards_deepseek
from app.services.excel_import import iter_legacy_records


def test_remote_extraction_is_off_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_REMOTE_EXTRACTION", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert extract_standards_deepseek("internal design text") == []


def test_legacy_excel_import_is_unverified():
    rows = list(iter_legacy_records(Path("backend/standards_data.xlsx")))
    assert rows
    assert rows[0]["code"].startswith(("GB", "JGJ", "CJJ", "CJ", "DB", "T", "建标"))
