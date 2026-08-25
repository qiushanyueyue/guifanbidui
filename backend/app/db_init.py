"""Schema bootstrap helpers used by the ASGI entrypoint and CLI scripts."""

from __future__ import annotations

import logging

from app.models.base import Base, engine
from app.models import models as _models  # noqa: F401 - register all tables

logger = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("database schema ready")
