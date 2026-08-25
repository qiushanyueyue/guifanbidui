from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.models import StandardModel
from app.repositories.standard_repo import StandardRepo


def test_code_search_prefers_requested_edition():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all(
        [
            StandardModel(
                code="GB/T 50010-2010",
                normalized_code="GB/T 50010-2010",
                name="混凝土结构设计标准",
                normalized_name="混凝土结构设计标准",
                revision_year="2010",
                status="unknown",
                verification_level="unverified",
            ),
            StandardModel(
                code="GB/T 50010-2010",
                normalized_code="GB/T 50010-2010",
                name="混凝土结构设计标准",
                normalized_name="混凝土结构设计标准",
                edition="2024年版",
                revision_year="2024",
                status="unknown",
                verification_level="unverified",
            ),
        ]
    )
    session.commit()

    matches = StandardRepo.search(session, "GB/T 50010-2010（2024年版）")

    assert len(matches) == 1
    assert matches[0].edition == "2024年版"
    session.close()
