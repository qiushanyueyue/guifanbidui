import app.models.models as models


def test_v2_standard_has_quality_and_revision_dimensions():
    model = getattr(models, "StandardV2Model", None)
    assert model is not None, "standards_v2 model is required"
    columns = set(model.__table__.columns.keys())
    assert {
        "base_code",
        "standard_prefix",
        "standard_number",
        "standard_year",
        "revision_status",
        "mandatory_clause_status",
        "data_quality_status",
        "document_kind",
    } <= columns


def test_staging_model_preserves_raw_source_evidence():
    model = getattr(models, "StagingStandardModel", None)
    assert model is not None, "staging_standards model is required"
    columns = set(model.__table__.columns.keys())
    assert {
        "source_name",
        "source_url",
        "raw_code",
        "raw_name",
        "raw_edition",
        "raw_status",
        "raw_text",
        "content_hash",
        "parse_status",
    } <= columns


def test_sync_checkpoint_and_normative_document_models_exist():
    assert getattr(models, "SyncCheckpointModel", None) is not None
    assert getattr(models, "NormativeDocumentModel", None) is not None
