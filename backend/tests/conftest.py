import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture()
def db_session():
    """Fresh SQLite file + freshly-created tables per test, same model classes
    (singleton Base/models for the whole test process) rebound to a new engine —
    see database.use_test_db for why we don't re-import model modules per test."""
    import tempfile

    from app import database

    with tempfile.TemporaryDirectory() as tmp:
        db_file = Path(tmp) / "test.db"
        database.use_test_db(db_file)

        session = database.SessionLocal()
        try:
            yield session
        finally:
            session.close()
