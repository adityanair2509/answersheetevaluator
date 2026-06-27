"""
db/base.py

Shared SQLAlchemy DeclarativeBase — import this in every ORM model file
and in alembic/env.py so Alembic can discover all table metadata.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column


class Base(DeclarativeBase):
    """
    Project-wide declarative base.

    All ORM models inherit from this class. Alembic imports `Base.metadata`
    from here to auto-generate migrations.
    """

    # Every table gets an auto-managed `created_at` timestamp by default.
    # Individual models override this if they need different behaviour.
    pass


# Convenience re-export so other modules can do:
#   from db.base import Base, utcnow
def utcnow() -> datetime:
    """Return the current UTC datetime (usable as a column default)."""
    return datetime.utcnow()
