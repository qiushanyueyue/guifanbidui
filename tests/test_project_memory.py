from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_project_memory.py"
SPEC = importlib.util.spec_from_file_location("check_project_memory", SCRIPT)
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def test_repository_project_memory_contract_is_valid():
    assert CHECKER.validate_memory(ROOT) == []


def test_checker_rejects_secret_in_memory_fixture(tmp_path: Path):
    for relative in CHECKER.MEMORY_FILES:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    memory = tmp_path / "MEMORY.md"
    memory.write_text(
        memory.read_text(encoding="utf-8")
        + "\napi_key = sk_test_1234567890abcdefghijklmnop\n",
        encoding="utf-8",
    )

    errors = CHECKER.validate_memory(tmp_path)

    assert any("provider token" in error or "assigned secret" in error for error in errors)


def test_checker_scans_future_decision_records(tmp_path: Path):
    for relative in CHECKER.MEMORY_FILES:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    future_adr = tmp_path / "docs/project-memory/decisions/ADR-9999-example.md"
    future_adr.write_text(
        "# ADR-9999\n\napi_key = sk_test_1234567890abcdefghijklmnop\n",
        encoding="utf-8",
    )

    errors = CHECKER.validate_memory(tmp_path)

    assert any("ADR-9999-example.md" in error for error in errors)
