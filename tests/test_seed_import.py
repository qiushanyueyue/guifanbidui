import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.models import StagingStandardModel, StandardV2Model, StandardV2SourceModel
from scripts import import_v2_seed


ROOT = Path(__file__).resolve().parents[1]


def test_seed_payload_is_imported_with_batched_staging_evidence():
    payload = json.loads((ROOT / "data" / "standards_v2_seed.json").read_text(encoding="utf-8"))
    payload["standards"] = payload["standards"][:2]
    payload["relations"] = []
    payload["normative_documents"] = []
    expected_sources = sum(len(item["sources"]) for item in payload["standards"])

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        result = import_v2_seed.import_seed_payload(db, payload)

        assert result == {"standards": 2, "relations": 0, "normative_documents": 0}
        assert db.query(StandardV2Model).count() == 2
        assert db.query(StagingStandardModel).count() == expected_sources
        assert db.query(StandardV2SourceModel).count() == expected_sources

        second_result = import_v2_seed.import_seed_payload(db, payload)
        assert second_result == result
        assert db.query(StandardV2Model).count() == 2
        assert db.query(StagingStandardModel).count() == expected_sources
        assert db.query(StandardV2SourceModel).count() == expected_sources
