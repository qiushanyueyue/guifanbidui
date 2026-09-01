import importlib

import pytest

from app.models.models import StandardModel


def _matcher():
    module = importlib.import_module("app.services.standard_matcher")
    matcher = getattr(module, "assess_standard_match", None)
    assert callable(matcher), "assess_standard_match is required"
    return matcher


def _standard(**overrides):
    values = {
        "code": "GB 50016-2014",
        "normalized_code": "GB 50016-2014",
        "name": "建筑设计防火规范",
        "normalized_name": "建筑设计防火规范",
        "edition": None,
        "revision_year": None,
        "status": "current",
        "verification_level": "single_source",
    }
    values.update(overrides)
    return StandardModel(**values)


def test_missing_current_revision_has_actionable_recommendation():
    result = _matcher()(
        input_code="GB 50016-2014",
        input_name="建筑设计防火规范",
        standard=_standard(edition="2018年版", revision_year="2018"),
    )
    assert result.match_type == "revision_missing"
    assert result.recommended_citation == "《建筑设计防火规范》GB 50016-2014（2018年版）"


def test_jgj_type_mismatch_recommends_jgj_t_code():
    result = _matcher()(
        input_code="JGJ 67-2019",
        input_name="办公建筑设计标准",
        standard=_standard(
            code="JGJ/T 67-2019",
            normalized_code="JGJ/T 67-2019",
            name="办公建筑设计标准",
            normalized_name="办公建筑设计标准",
        ),
    )
    assert result.match_type == "code_type_mismatch"
    assert result.recommended_citation == "《办公建筑设计标准》JGJ/T 67-2019"


@pytest.mark.parametrize(
    ("status", "expected"),
    [("abolished", "obsolete"), ("replaced", "replaced"), ("conflict", "source_conflict")],
)
def test_status_decision_has_precedence(status, expected):
    result = _matcher()(
        input_code="GB 50016-2014",
        input_name="建筑设计防火规范",
        standard=_standard(status=status),
    )
    assert result.match_type == expected


def test_exact_reference_is_not_reduced_to_percentage():
    result = _matcher()(
        input_code="GB 50016-2014",
        input_name="建筑设计防火规范",
        standard=_standard(),
    )
    assert result.match_type == "exact"
    assert result.confidence == 1.0


def test_unknown_status_does_not_hide_an_exact_identity_match():
    result = _matcher()(
        input_code="GB 50016-2014",
        input_name="建筑设计防火规范",
        standard=_standard(status="unknown"),
    )
    assert result.match_type == "exact"
    assert result.message == "引用与来源记录完全一致；规范状态暂无法确认"


def test_explicit_current_edition_is_exact():
    result = _matcher()(
        input_code="GB 50016-2014（2018年版）",
        input_name="建筑设计防火规范",
        standard=_standard(edition="2018年版", revision_year="2018"),
    )
    assert result.match_type == "exact"


def test_local_amendment_is_included_in_recommended_citation():
    result = _matcher()(
        input_code="GB 50016-2014（2018年版）",
        input_name="建筑设计防火规范",
        standard=_standard(edition="2018年版", revision_year="2018", amendment="2024年局部修订"),
    )
    assert result.match_type == "revision_missing"
    assert result.recommended_citation == "《建筑设计防火规范》GB 50016-2014（2018年版+2024年局部修订）"
    assert result.message == "规范现行，但引用需采用2018年版+2024年局部修订"
