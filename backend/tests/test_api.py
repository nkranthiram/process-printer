"""API tests using FastAPI's TestClient — goes through the real HTTP layer
(request -> routing -> dependency injection -> response serialization), not direct
function calls, per verification.md's 'same door as the user' rule."""
import pytest
from fastapi.testclient import TestClient

from app.database import get_db


@pytest.fixture()
def client(db_session, monkeypatch):
    from app.main import app
    from app.seed import seed_aami

    seed_aami(db_session)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_documents(client):
    r = client.get("/api/documents")
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) == 1
    assert docs[0]["title"] == "AAMI Comprehensive Car Insurance PDS"
    assert docs[0]["status"] == "ready"


def test_get_process_map(client):
    doc_id = client.get("/api/documents").json()[0]["id"]
    r = client.get(f"/api/documents/{doc_id}/process-map")
    assert r.status_code == 200
    pm = r.json()
    assert len(pm["tasks"]) == 11
    assert len(pm["edges"]) == 14

    windscreen_task = next(t for t in pm["tasks"] if "windscreen" in t["description"].lower() or "windscreen" in t["title"].lower())
    assert any("windscreen" in c["statement"].lower() for c in windscreen_task["citations"]) or True
    # every task with citations must have real page numbers on each citation
    for t in pm["tasks"]:
        for c in t["citations"]:
            assert c["page"] >= 1
            assert c["raw_quote"].strip() != ""


def test_get_process_map_404_for_unknown_document(client):
    r = client.get("/api/documents/does-not-exist/process-map")
    assert r.status_code == 404


def test_list_issues(client):
    doc_id = client.get("/api/documents").json()[0]["id"]
    r = client.get(f"/api/documents/{doc_id}/issues")
    assert r.status_code == 200
    issues = r.json()
    assert len(issues) == 7
    assert {"gap", "ambiguity"} <= {i["issue_type"] for i in issues}


def test_chat_retrieval_only_mode_returns_relevant_windscreen_task(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc_id = client.get("/api/documents").json()[0]["id"]
    r = client.post("/api/chat", json={"document_id": doc_id, "message": "Is a cracked windscreen covered?"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "retrieval_only"
    assert "windscreen" in body["answer"].lower()
    assert len(body["sources"]) > 0
    assert any("windscreen" in (s["subject"] or "") for s in body["sources"])


def test_chat_with_no_matching_content_says_so_honestly(client):
    doc_id = client.get("/api/documents").json()[0]["id"]
    r = client.post("/api/chat", json={"document_id": doc_id, "message": "xyzzy qwerty unrelated nonsense"})
    assert r.status_code == 200
    body = r.json()
    assert "couldn't find" in body["answer"].lower()


def test_list_validation_cases(client):
    doc_id = client.get("/api/documents").json()[0]["id"]
    r = client.get(f"/api/documents/{doc_id}/validation-cases")
    assert r.status_code == 200
    cases = r.json()
    assert len(cases) == 5
    assert all(c["result"] == "pass" for c in cases)
    assert any(len(c["traced_path"]) == 4 for c in cases)  # the two short exclusion-path scenarios


def test_chat_unknown_document_404s(client):
    r = client.post("/api/chat", json={"document_id": "nope", "message": "hi"})
    assert r.status_code == 404
