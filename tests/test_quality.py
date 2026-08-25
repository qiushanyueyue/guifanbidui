import importlib


def _quality_module():
    return importlib.import_module("app.services.data_quality")


def test_relation_quality_rejects_self_relation():
    report = _quality_module().validate_relation_edges([(1, 1), (1, 2)])
    assert report.self_relations == [(1, 1)]
    assert report.is_publishable is False


def test_relation_quality_detects_cycle():
    report = _quality_module().validate_relation_edges([(1, 2), (2, 3), (3, 1)])
    assert report.cycles
    assert report.is_publishable is False


def test_relation_quality_accepts_linear_replacement_chain():
    report = _quality_module().validate_relation_edges([(1, 2), (2, 3)])
    assert report.self_relations == []
    assert report.cycles == []
    assert report.is_publishable is True


def test_relation_quality_reports_missing_targets():
    report = _quality_module().validate_relation_edges([(1, 2)], known_ids={1})
    assert report.missing_targets == [2]
    assert report.is_publishable is False
