"""Vercel/Python entrypoint."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

__all__ = ["app"]
