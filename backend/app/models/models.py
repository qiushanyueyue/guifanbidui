"""Portable SQLAlchemy schema for versioned standard metadata."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.models.base import Base


_STATUS_VALUES = "'current','upcoming','abolished','replaced','partially_amended','unknown','conflict'"
_VERIFICATION_VALUES = "'official','cross_verified','single_source','unverified','conflict'"


class StandardModel(Base):
    __tablename__ = "standards"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="ck_standards_status"),
        CheckConstraint(
            f"verification_level IN ({_VERIFICATION_VALUES})",
            name="ck_standards_verification_level",
        ),
        Index("ix_standards_normalized_code_edition", "normalized_code", "edition"),
        Index("ix_standards_normalized_name", "normalized_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # ``code`` is a display/raw value, not a unique identity.  The same base
    # code can have multiple editions, amendments, or source records.
    code = Column(String(120), nullable=False, index=True)
    normalized_code = Column(String(120), nullable=False, default="", index=True)
    name = Column(String(500), nullable=False, default="")
    normalized_name = Column(String(500), nullable=False, default="")
    edition = Column(String(80), nullable=True)
    revision_year = Column(String(4), nullable=True)
    amendment = Column(String(200), nullable=True)
    standard_type = Column(String(80), nullable=True)
    status = Column(String(32), nullable=False, default="unknown", server_default="unknown")
    publish_date = Column(String(40), nullable=True)
    implement_date = Column(String(40), nullable=True)
    abolish_date = Column(String(40), nullable=True)
    replaces = Column(Text, nullable=True)
    replaced_by = Column(Text, nullable=True)
    # Reserved metadata for the distinction between whole-standard status and
    # clause-level/mandatory-clause changes (for example GB 550xx adoption).
    article_status = Column(Text, nullable=True)
    mandatory_clause_status = Column(Text, nullable=True)
    issuing_authority = Column(String(300), nullable=True)
    canonical_source = Column(String(80), nullable=True)
    canonical_url = Column(String(1000), nullable=True)
    soujianzhu_url = Column(String(1000), nullable=True)
    source_conflict = Column(Boolean, nullable=False, default=False, server_default="0")
    conflict_details = Column(Text, nullable=True)
    verification_level = Column(
        String(32), nullable=False, default="unverified", server_default="unverified"
    )
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    last_verified_at = Column(DateTime, nullable=True, index=True)
    source_updated_at = Column(String(80), nullable=True)
    record_updated_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    # Compatibility fields retained for older scripts and clients.
    year = Column(String(4), nullable=True)
    publishing_department = Column(String(300), nullable=True)
    implementation_date = Column(String(40), nullable=True)
    url = Column(String(1000), nullable=True)
    last_updated = Column(DateTime, nullable=True)


class StandardSourceModel(Base):
    __tablename__ = "standard_sources"
    __table_args__ = (
        UniqueConstraint(
            "standard_id", "source_name", "source_code", name="uq_standard_source_identity"
        ),
        Index("ix_standard_sources_standard_id", "standard_id"),
        Index("ix_standard_sources_content_hash", "content_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False)
    source_name = Column(String(80), nullable=False)
    source_url = Column(String(1000), nullable=True)
    source_code = Column(String(120), nullable=True)
    source_name_text = Column(String(500), nullable=True)
    source_status = Column(String(200), nullable=True)
    publish_date = Column(String(40), nullable=True)
    implement_date = Column(String(40), nullable=True)
    abolish_date = Column(String(40), nullable=True)
    replaces = Column(Text, nullable=True)
    replaced_by = Column(Text, nullable=True)
    source_updated_at = Column(String(80), nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    content_hash = Column(String(64), nullable=True)
    parse_status = Column(String(32), nullable=False, default="ok", server_default="ok")
    parse_error = Column(Text, nullable=True)
    raw_payload = Column(Text, nullable=True)


class StandardRelationModel(Base):
    __tablename__ = "standard_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_standard_id",
            "target_standard_id",
            "relation_type",
            name="uq_standard_relation",
        ),
        Index("ix_standard_relations_source", "source_standard_id"),
        Index("ix_standard_relations_target", "target_standard_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_standard_id = Column(
        Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False
    )
    target_standard_id = Column(
        Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False
    )
    relation_type = Column(String(40), nullable=False)
    evidence_source_id = Column(
        Integer, ForeignKey("standard_sources.id", ondelete="SET NULL"), nullable=True
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SyncRunModel(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (Index("ix_sync_runs_source_started", "source", "started_at"),)

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(80), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="running")
    found = Column(Integer, nullable=False, default=0)
    inserted = Column(Integer, nullable=False, default=0)
    updated = Column(Integer, nullable=False, default=0)
    unchanged = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)


class StandardHistoryModel(Base):
    __tablename__ = "standard_history"
    __table_args__ = (Index("ix_standard_history_standard_changed", "standard_id", "changed_at"),)

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    field_name = Column(String(80), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    source = Column(String(80), nullable=True)


# Reserved layers for a future standards-text knowledge base.  They contain
# metadata only; this phase deliberately does not ingest copyrighted bodies.
class StandardDocumentModel(Base):
    __tablename__ = "standard_documents"

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False)
    source_url = Column(String(1000), nullable=True)
    title = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True)
    ingestion_status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StandardArticleModel(Base):
    __tablename__ = "standard_articles"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("standard_documents.id", ondelete="CASCADE"), nullable=False)
    article_number = Column(String(80), nullable=True)
    title = Column(String(500), nullable=True)
    body_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StandardChunkModel(Base):
    __tablename__ = "standard_chunks"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("standard_articles.id", ondelete="CASCADE"), nullable=False)
    ordinal = Column(Integer, nullable=True)
    content = Column(Text, nullable=True)
    embedding_ref = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
