import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_pending_resumes_endpoint():
    response = client.get("/inbox/pending-resumes")
    assert response.status_code == 200
    data = response.json()
    assert "total_pending" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_sync_endpoint():
    response = client.post("/inbox/sync")
    assert response.status_code == 200
    data = response.json()
    assert "total_pending" in data


def test_deny_single_resume_endpoint():
    get_res = client.get("/inbox/pending-resumes")
    items = get_res.json()["items"]
    if items:
        target_id = items[0]["id"]
        deny_res = client.post("/inbox/deny", json={"resume_ids": [target_id]})
        assert deny_res.status_code == 200
        data = deny_res.json()
        assert data["success"] is True
        assert data["denied_count"] == 1
