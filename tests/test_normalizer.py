from app.services.extractor import extract_standards_from_text
from app.services.standard_normalizer import normalize_standard_code, parse_edition


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


def test_edition_parser_does_not_leak_to_next_reference():
    result = extract_standards_from_text("GB/T 50010-2010（2024年版）以及 JGJ 18-2012")
    assert result[0].edition == "2024年版"
    assert result[1].edition is None
