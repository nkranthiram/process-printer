"""Environment/config loading — single place responsible for making
backend/.env visible to the rest of the app via os.environ.

Import this module first (before anything reads os.environ.get(...)) in any
entrypoint: app.main (API server), and any standalone pipeline script run
directly. Safe to import multiple times — load_dotenv() is idempotent and
won't override a variable already set in the real environment (e.g. by a
shell `export`), so an explicit `export ANTHROPIC_API_KEY=...` always wins
over what's in .env.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)
