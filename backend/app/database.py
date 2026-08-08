"""Database engine/session setup.

SQLite for local dev by default (see architecture.md for why); the models use
SQLAlchemy's ORM in a way that migrates to Postgres without a rewrite if that's
ever needed.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path(os.environ.get("PROCESS_PRINTER_DB", Path(__file__).parent.parent / "process_printer.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Idempotent — safe to call on every startup."""
    from app.models import (  # noqa: F401  (import registers models on Base)
        document,
        claim,
        process_map,
        change_request,
        review_session,
        issue,
        validation,
        agentic_workflow,
    )

    Base.metadata.create_all(bind=engine)


def use_test_db(db_path) -> None:
    """Rebind the module-level engine/SessionLocal to a fresh SQLite file and
    (re)create all tables there.

    Deliberately does NOT re-import the model modules or recreate the Base class —
    doing that per-test (via sys.modules deletion) causes SQLAlchemy ORM instances
    from one Base to be inserted against tables created under a different Base's
    metadata, which silently drops columns from the generated INSERT (discovered
    the hard way in this project's own test suite — see docs/evidence for task 8).
    Models are a singleton import for the life of the test process; only the
    engine/session/tables are swapped per test.
    """
    global engine, SessionLocal, DATABASE_URL, DB_PATH

    DB_PATH = db_path
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal.configure(bind=engine)

    from app.models import (  # noqa: F401
        document, claim, process_map, change_request, review_session, issue, validation, agentic_workflow,
    )

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
