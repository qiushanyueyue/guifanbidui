import pytest

from app.services.extractor import extract_standards_from_text
from app.services.standard_normalizer import (
    extract_standard_codes,
    normalize_standard_code,
    normalized_name,
    parse_edition,
    parse_standard_code,
)


def test_code_variants_are_canonicalized():
    assert normalize_standard_code("GB50010-2010") == "GB 50010-2010"
    assert normalize_standard_code("GB/T 50010-2010") == "GB/T 50010-2010"
    assert normalize_standard_code("JGJ l8-2012") == "JGJ 18-2012"
    assert normalize_standard_code("DB/T29-176-2016") == "DB/T 29-176-2016"
    assert normalize_standard_code("T/xxxx") == "T/XXXX"


def test_non_standard_prefix_is_not_ocr_corrupted():
    assert normalize_standard_code("ISO 9001") == "ISO 9001"


def test_edition_is_separate_from_base_code():
    result = extract_standards_from_text("《混凝土结构设计标准》GB/T 50010-2010（2024年版）")
    assert len(result) == 1
    assert result[0].code == "GB/T 50010-2010"
    assert result[0].base_code == "GB/T 50010-2010"
    assert result[0].edition == "2024年版"
    assert result[0].revision_year == "2024"


def test_edition_is_detected_after_wrapped_code_parentheses():
    result = extract_standards_from_text("（GB/T 50010-2010）（2024年版）")

    assert len(result) == 1
    assert result[0].code == "GB/T 50010-2010"
    assert result[0].edition == "2024年版"


def test_edition_parser_does_not_leak_to_next_reference():
    result = extract_standards_from_text("GB/T 50010-2010（2024年版）以及 JGJ 18-2012")
    assert result[0].edition == "2024年版"
    assert result[1].edition is None


def test_compact_recommended_standard_prefix_is_canonicalized():
    assert normalize_standard_code("JGJT67-2019") == "JGJ/T 67-2019"


def test_dbj_standard_is_parsed_into_components():
    parsed = parse_standard_code("DBJ 01-62-2002")
    assert parsed is not None
    assert parsed.prefix == "DBJ"
    assert parsed.serial == "01-62"
    assert parsed.year == "2002"


def test_name_normalization_keeps_meaningful_engineering_terms():
    assert normalized_name("《混凝土结构设计标准》（附条文说明）") == "混凝土结构设计标准"


def test_name_normalization_moves_revision_out_of_name():
    assert normalized_name("建筑设计防火规范(2018年版)") == "建筑设计防火规范"


def test_legacy_two_digit_year_is_preserved():
    parsed = parse_standard_code("GB50157-92")
    assert parsed is not None
    assert parsed.normalized == "GB 50157-92"
    assert parsed.year == "92"


def test_name_normalization_removes_embedded_code_and_clause_note():
    assert normalized_name("体育建筑设计规范 JGJ31-2003(附条文说明)") == "体育建筑设计规范"
    assert normalized_name("住宅项目规范（含条文说明）") == "住宅项目规范"


def test_isolated_gb_prefix_is_not_extracted_as_a_standard_code():
    text = "设计采用建筑设计防火规范，编号为 GB五零零一六二零一四。"
    codes = extract_standard_codes(text)

    assert [item.normalized for item in codes] == []
    assert extract_standards_from_text(text) == []


def test_atlas_reference_keeps_its_numeric_prefix():
    assert normalize_standard_code("22G101-1") == "22G101-1"

    codes = extract_standard_codes("梁配筋详图参见 22G101-1。")

    assert [item.normalized for item in codes] == ["22G101-1"]


def test_logical_item_boundaries_keep_name_only_and_editions_separate():
    text = (
        "《A》（DB/T29-176-2016）\n"
        "（27）《城市轨道交通工程设计文件编制深度规定》（2014年版）\n"
        "（28）《建筑工程抗浮技术标准》（JGJ476-2019）"
    )

    result = extract_standards_from_text(text)
    by_code = {item.code: item for item in result if item.code}
    name_only = [item for item in result if not item.code]

    assert len(result) == 3
    assert by_code["DB/T 29-176-2016"].edition is None
    assert by_code["JGJ 476-2019"].name == "建筑工程抗浮技术标准"
    assert len(name_only) == 1
    assert name_only[0].name == "城市轨道交通工程设计文件编制深度规定"
    assert name_only[0].edition == "2014年版"


def test_same_line_consecutive_references_keep_each_name():
    result = extract_standards_from_text(
        "《甲标准》GB/T 50010-2010（2024年版）；《乙标准》JGJ 18-2012"
    )

    assert [(item.code, item.name) for item in result] == [
        ("GB/T 50010-2010", "甲标准"),
        ("JGJ 18-2012", "乙标准"),
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("JGJ476－2019", "JGJ 476-2019"),
        ("CJJ／T 269-2017", "CJJ/T 269-2017"),
        ("DB13(J)185-2020", "DB 13(J)185-2020"),
        ("DBJ/T15-110-2015", "DBJ/T 15-110-2015"),
        ("DBJ61/T93-2014", "DBJ 61/T93-2014"),
        ("JT/T 1392-2021", "JT/T 1392-2021"),
        ("T/CECS 884-2021", "T/CECS 884-2021"),
    ],
)
def test_directory_code_families_and_fullwidth_punctuation(raw, expected):
    assert normalize_standard_code(raw) == expected
    assert normalized_name("混凝土结构施工验收规范") != normalized_name("混凝土结构设计规范")
