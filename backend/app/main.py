from __future__ import annotations

import app.config  # noqa: F401  (import first: loads backend/.env into os.environ)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.database import init_db
from app.seed import seed_aami

app = FastAPI(title="Process Printer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()
    # Seed the AAMI document on startup so the app has something to show without
    # a manual upload step first — see architecture.md for why this run uses the
    # manual-agent-pass extraction rather than a live LLM call.
    seed_aami()


@app.get("/api/health")
def health():
    return {"status": "ok"}
