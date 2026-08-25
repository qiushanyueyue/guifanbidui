from __future__ import annotations

import importlib
import json
from pathlib import Path


CATALOG_PATH = Path("/Volumes/yue/Download/规范目录库20251011.xlsx")
SEED_PATH = Path("data/standards_v2_seed.json")


def _audit_callable():
    try:
        module = importlib.import_module("app.services.excel_catalog_audit")
    except ModuleNotFoundError:
        return None
    return getattr(module, "audit_catalog", None)


def _normative_classifier():
    try:
        module = importlib.import_module("app.services.excel_catalog_audit")
    except ModuleNotFoundError:
        return None
    return getattr(module, "classify_unparseable_documents", None)


def _normative_merger():
    try:
        module = importlib.import_module("scripts.stage_excel_normative_documents")
    except ModuleNotFoundError:
        return None
    return getattr(module, "merge_normative_documents", None)


def _pre_merge_seed(tmp_path: Path) -> Path:
    """Recreate the reviewed seed before this task's normative-document append."""

    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    payload["normative_documents"] = [
        item
        for item in payload["normative_documents"]
        if item.get("source_name") != "excel_catalog_20251011"
    ]
    path = tmp_path / "seed-before-normative-merge.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_catalog_audit_conserves_all_excel_rows_and_keeps_traceability():
    audit_catalog = _audit_callable()
    assert callable(audit_catalog)
    report = audit_catalog(CATALOG_PATH, seed_path=SEED_PATH)

    assert report.total_rows == 1585
    assert len(report.rows) == report.total_rows
    assert {row.excel_row for row in report.rows} == set(range(2, 1587))
    assert report.summary["total_rows"] == 1585
    assert sum(report.summary[key] for key in report.CLASSIFICATIONS) == 1585


def test_catalog_audit_normalizes_codes_and_preserves_version_semantics():
    audit_catalog = _audit_callable()
    assert callable(audit_catalog)
    report = audit_catalog(CATALOG_PATH, seed_path=SEED_PATH)

    by_code = {row.normalized_code: row for row in report.rows if row.normalized_code}
    assert by_code["GB 50016-2014"].edition == "2018年版"
    assert by_code["JGJ/T 67-2019"].name == "办公建筑设计标准"
    assert by_code["GB 50157-2013"].normalized_code == "GB 50157-2013"

    assert by_code["GB 50016-2014"].classification == "existing"
    assert by_code["JGJ/T 67-2019"].classification == "existing"
    assert by_code["GB 50157-2013"].classification == "existing"


def test_catalog_audit_distinguishes_version_and_name_conflicts(tmp_path):
    audit_catalog = _audit_callable()
    assert callable(audit_catalog)
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed["standards"] = [
        item for item in seed["standards"] if item["base_code"] != "GB 50046-2018"
    ]
    comparison_seed = tmp_path / "comparison-seed.json"
    comparison_seed.write_text(json.dumps(seed, ensure_ascii=False), encoding="utf-8")
    report = audit_catalog(CATALOG_PATH, seed_path=comparison_seed)

    version_conflict = next(row for row in report.rows if row.excel_row == 1524)
    assert version_conflict.classification == "version_conflict"
    assert version_conflict.verification_status == "unknown"
    assert version_conflict.verification_level == "unverified"
    assert next(row for row in report.rows if row.excel_row == 1564).classification == "name_conflict"
    assert next(row for row in report.rows if row.excel_row == 1577).classification == "name_conflict"


def test_excel_only_candidates_are_not_reported_as_current():
    audit_catalog = _audit_callable()
    assert callable(audit_catalog)
    report = audit_catalog(CATALOG_PATH, seed_path=SEED_PATH)

    for row in report.rows:
        if row.classification == "missing":
            assert row.verification_status == "unknown"
            assert row.verification_level == "unverified"

    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    unknown_codes = {"RFJ 02-2009", "DB/T 29-176-2016", "DB 29-20-2017"}
    for item in seed["standards"]:
        if item["base_code"] in unknown_codes:
            assert item["status"] == "unknown"
            assert item["verification_level"] == "unverified"


def test_final_artifacts_match_seed_and_explain_the_excel_supplement_delta():
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    audit = json.loads(
        Path("artifacts/excel_catalog_audit_20251011.json").read_text(encoding="utf-8")
    )
    pre_import = json.loads(
        Path("artifacts/excel_catalog_audit_20251011_pre_import.json").read_text(encoding="utf-8")
    )
    normative_pre_import = json.loads(
        Path("artifacts/excel_catalog_audit_20251011_normative_pre_import.json").read_text(encoding="utf-8")
    )
    quality = json.loads(
        Path("artifacts/data_quality_report_excel_catalog.json").read_text(encoding="utf-8")
    )

    assert len(seed["standards"]) == 1738
    assert len(seed["relations"]) == 32
    assert len(seed["normative_documents"]) == 230
    assert quality["total_canonical"] == len(seed["standards"])
    assert quality["relations"] == len(seed["relations"])
    assert quality["normative_documents"] == len(seed["normative_documents"])
    assert quality["seed_snapshot"] == {
        "canonical": 1738,
        "relations": 32,
        "normative_documents": 230,
    }
    assert quality["normative_document_supplement"] == {
        "source_rows": 171,
        "existing_normative_document_rows_before_merge": 155,
        "staged_normative_document_rows_before_merge": 14,
        "unique_added": 13,
        "manual_review_rows": 2,
        "remaining_unentered_rows": [435, 448],
        "remaining_unentered_reason": "空白或无意义文本，未入库",
    }
    assert audit["total_rows"] == 1585
    assert audit["summary"]["total_rows"] == 1585
    assert pre_import["total_rows"] == 1585
    assert pre_import["summary"]["total_rows"] == 1585
    assert pre_import["summary"]["missing"] == 21

    normative_pre = normative_pre_import["normative_document_audit"]
    assert normative_pre["total_rows"] == 171
    assert normative_pre["summary"] == {
        "existing_normative_document": 155,
        "staged_normative_document": 14,
        "manual_review": 2,
    }
    assert len(normative_pre["staged_documents"]) == 13

    normative_audit = audit["normative_document_audit"]
    assert normative_audit["total_rows"] == 171
    assert normative_audit["summary"] == {
        "existing_normative_document": 169,
        "staged_normative_document": 0,
        "manual_review": 2,
    }
    manual_rows = {
        row["excel_row"]
        for row in normative_audit["rows"]
        if row["classification"] == "manual_review"
    }
    assert manual_rows == {435, 448}

    staged_titles = {
        item["title"]
        for item in seed["normative_documents"]
        if item["source_name"] == "excel_catalog_20251011"
    }
    assert {
        "电影院建筑设计规范",
        "城镇给水膜处理技术规程",
        "建筑防火封堵应用技术规程",
        "危险性较大的分部分项工程安全管理规定",
        "混凝土结构施工图平面整体表示方法制图规则和构造详图",
        "多、高层民用建筑钢结构节点构造详图",
        "钢结构施工图参数表示方法制图规则和构造详图",
    }.issubset(staged_titles)
    assert all(
        item["status"] == "unknown"
        and item["verification_level"] == "unverified"
        for item in seed["normative_documents"]
        if item["source_name"] == "excel_catalog_20251011"
    )

    delta = audit["supplement_delta"]
    assert quality["supplement_delta"] == delta
    assert delta["baseline_canonical"] == 1716
    assert delta["current_canonical"] == 1738
    assert delta["added_canonical"] == 22
    assert delta["components"] == {
        "unique_excel_missing": 20,
        "name_conflict_supplement": ["GB/T 37127-2018"],
        "version_conflict_candidate": ["GB 50046-2018"],
    }


def test_unparseable_rows_are_conserved_and_document_candidates_are_traced(tmp_path):
    classify_unparseable_documents = _normative_classifier()
    assert callable(classify_unparseable_documents)
    pre_merge_seed = _pre_merge_seed(tmp_path)
    result = classify_unparseable_documents(CATALOG_PATH, seed_path=pre_merge_seed)

    assert result.total_rows == 171
    assert sum(result.summary.values()) == 171
    assert result.summary == {
        "existing_normative_document": 155,
        "staged_normative_document": 14,
        "manual_review": 2,
    }
    assert set(result.summary) == {
        "existing_normative_document",
        "staged_normative_document",
        "manual_review",
    }
    assert {row.excel_row for row in result.rows} == {
        row["excel_row"]
        for row in json.loads(Path("artifacts/excel_catalog_audit_20251011.json").read_text(encoding="utf-8"))["rows"]
        if row["classification"] == "unparseable"
    }

    by_row = {row.excel_row: row for row in result.rows}
    assert by_row[432].classification == "staged_normative_document"
    assert by_row[1183].classification == "staged_normative_document"
    assert by_row[1347].classification == "staged_normative_document"
    assert by_row[1534].classification == "staged_normative_document"
    assert by_row[1522].classification == "staged_normative_document"
    assert by_row[1583].classification == "staged_normative_document"
    assert by_row[1584].classification == "staged_normative_document"
    assert by_row[435].classification == "manual_review"


def test_staged_normative_documents_are_unknown_and_not_ordinary_standards(tmp_path):
    classify_unparseable_documents = _normative_classifier()
    assert callable(classify_unparseable_documents)
    result = classify_unparseable_documents(
        CATALOG_PATH,
        seed_path=_pre_merge_seed(tmp_path),
    )

    for row in result.rows:
        if row.classification == "staged_normative_document":
            assert row.status == "unknown"
            assert row.verification_level == "unverified"
            assert row.document_kind in {"standard", "guideline", "method", "regulation", "notice"}
            assert row.normalized_name


def test_merging_normative_candidates_does_not_change_ordinary_standards(tmp_path):
    classify_unparseable_documents = _normative_classifier()
    merge_normative_documents = _normative_merger()
    assert callable(classify_unparseable_documents)
    assert callable(merge_normative_documents)
    pre_merge_seed = _pre_merge_seed(tmp_path)
    payload = json.loads(pre_merge_seed.read_text(encoding="utf-8"))
    standards_before = json.dumps(payload["standards"], ensure_ascii=False, sort_keys=True)
    result = classify_unparseable_documents(CATALOG_PATH, seed_path=pre_merge_seed)

    additions = merge_normative_documents(payload, result)

    assert len(additions) == 13
    assert len(payload["standards"]) == 1738
    assert json.dumps(payload["standards"], ensure_ascii=False, sort_keys=True) == standards_before
    assert len(payload["normative_documents"]) == 230
    assert all(item["source_name"] == "excel_catalog_20251011" for item in additions)
    assert all(item["status"] == "unknown" for item in additions)
    assert all(item["verification_level"] == "unverified" for item in additions)
