import os
import sqlite3
import tempfile
import pytest
from pathlib import Path

from utils.inbound_resume_manager import (
    InboundResumeManager,
    PendingResumeItem,
    BatchIngestRequest,
    DenyResumeRequest,
)


@pytest.fixture
def temp_manager():
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "test_ta.db"
    staging_dir = Path(temp_dir.name) / "staging"
    uploads_dir = Path(temp_dir.name) / "uploads"
    
    manager = InboundResumeManager(
        db_path=str(db_path),
        staging_dir=str(staging_dir),
        uploads_dir=str(uploads_dir),
        enable_imap=False,
    )
    yield manager
    temp_dir.cleanup()


def test_init_db(temp_manager):
    # Verify table creation
    conn = sqlite3.connect(temp_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_resumes'")
    table = cursor.fetchone()
    conn.close()
    assert table is not None
    assert table[0] == "pending_resumes"


def test_seed_and_get_pending_resumes(temp_manager):
    # Seed mock resumes
    items = temp_manager.sync_inbound_resumes()
    assert len(items) >= 2
    
    # Retrieve pending resumes
    pending = temp_manager.get_pending_resumes()
    assert pending.total_pending >= 2
    assert any(item.source_channel == "LinkedIn" for item in pending.items)
    assert any(item.source_channel == "Gmail" for item in pending.items)


def test_duplicate_detection(temp_manager):
    # Seed initial items
    temp_manager.sync_inbound_resumes()
    
    # Check if duplicate is flagged when same candidate/file is introduced
    duplicate_item = temp_manager.add_pending_resume(
        candidate_name="Priya Patel", # Priya Patel is already a known candidate
        email_sender="priya.patel@example.com",
        source_channel="LinkedIn",
        filename="Priya_Patel_Resume.pdf",
        content_bytes=b"Sample resume for Priya Patel Backend Engineer",
    )
    assert duplicate_item.is_duplicate is True
    assert "duplicate" in (duplicate_item.duplicate_reason or "").lower()


def test_deny_resume(temp_manager):
    temp_manager.sync_inbound_resumes()
    pending = temp_manager.get_pending_resumes()
    initial_count = pending.total_pending
    assert initial_count > 0
    
    target_id = pending.items[0].id
    deny_res = temp_manager.deny_resumes(DenyResumeRequest(resume_ids=[target_id]))
    assert deny_res.success is True
    assert deny_res.denied_count == 1
    
    # Check count decreased
    updated_pending = temp_manager.get_pending_resumes()
    assert updated_pending.total_pending == initial_count - 1
    assert all(item.id != target_id for item in updated_pending.items)


def test_batch_ingest_resumes(temp_manager):
    temp_manager.sync_inbound_resumes()
    pending = temp_manager.get_pending_resumes()
    target_id = pending.items[0].id
    
    ingest_res = temp_manager.ingest_resumes(
        BatchIngestRequest(resume_ids=[target_id]),
        skip_qdrant=True, # For unit tests without running Qdrant
    )
    assert ingest_res.success is True
    assert ingest_res.ingested_count == 1
    assert ingest_res.results[0].status == "success"
    
    # Ingested item should no longer be pending
    updated_pending = temp_manager.get_pending_resumes()
    assert all(item.id != target_id for item in updated_pending.items)


def test_extract_candidate_name():
    # 1. Attachment filename has candidate name, email sender is different
    # e.g., Pitu Pednekar sending Khushi Chitari's resume
    name = InboundResumeManager.extract_candidate_name(
        filename="Khushi_Chitari Resume.pdf",
        sender_real_name="Pitu Pednekar",
        sender_email="pitupednekar@gmail.com",
    )
    assert name == "Khushi Chitari"

    # 2. Uppercase with hyphen/version in filename
    name_rajdeep = InboundResumeManager.extract_candidate_name(
        filename="RAJDEEP_PEDNEKAR_RESUME-1.pdf",
        sender_real_name="Pitu Pednekar",
        sender_email="pitupednekar@gmail.com",
    )
    assert name_rajdeep == "Rajdeep Pednekar"

    # 3. Filename with job role tokens
    name_devin = InboundResumeManager.extract_candidate_name(
        filename="Devin_Vance_Staff_Backend_Resume.txt",
        sender_real_name="Job Alerts",
        sender_email="applications@linkedin.com",
    )
    assert name_devin == "Devin Vance"

    # 4. Generic filename: Peeks inside content
    name_from_doc = InboundResumeManager.extract_candidate_name(
        filename="Resume.txt",
        sender_real_name="Recruiting Agency",
        sender_email="agency@example.com",
        content_bytes=b"Elena Rostova\nSenior Full Stack Developer\nEmail: elena@example.com",
    )
    assert name_from_doc == "Elena Rostova"

    # 5. Generic filename and no doc bytes: Falls back to sender display name
    name_fallback_sender = InboundResumeManager.extract_candidate_name(
        filename="Resume.pdf",
        sender_real_name="Alice Wonderland",
        sender_email="alice@wonderland.com",
    )
    assert name_fallback_sender == "Alice Wonderland"

