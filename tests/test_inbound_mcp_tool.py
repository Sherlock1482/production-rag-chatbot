import pytest
from utils.inbound_resume_manager import InboundResumeManager
from mcp_server import fetch_inbound_resumes, deny_inbound_resumes, ingest_inbound_resumes


def test_fetch_inbound_resumes_mcp():
    res = fetch_inbound_resumes()
    assert res["success"] is True
    assert "total_pending" in res
    assert isinstance(res["items"], list)


def test_deny_and_ingest_mcp():
    # Fetch first
    fetch_res = fetch_inbound_resumes()
    if fetch_res["items"]:
        first_id = fetch_res["items"][0]["id"]
        # Test denying
        deny_res = deny_inbound_resumes([first_id])
        assert deny_res["success"] is True
        assert deny_res["denied_count"] == 1
