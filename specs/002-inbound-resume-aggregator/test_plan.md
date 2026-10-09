# Test Plan: Inbound Resume Aggregator

## 1. Unit Tests (`tests/test_inbound_resume_manager.py`)
- **Test 1: SQLite Pending Table Initialization**
  - Verify that `init_inbound_resumes_table()` creates the table if not present.
- **Test 2: Save and Fetch Pending Resumes**
  - Save pending resumes into the database.
  - Verify `fetch_pending_resumes()` returns items matching `PendingResumeItem` schema.
- **Test 3: Duplicate Detection**
  - Simulate an existing candidate in Qdrant/SQLite.
  - Test `detect_duplicate_resume()` returns `is_duplicate=True` and appropriate reason.
  - Test non-duplicate resume returns `is_duplicate=False`.
- **Test 4: Batch Ingestion**
  - Call `batch_ingest_resumes(resume_ids)` with sample files.
  - Verify files are indexed and status transitions from `pending` to `ingested`.
- **Test 5: Deny / Remove Resume**
  - Call `deny_pending_resumes(resume_ids)`.
  - Verify status transitions from `pending` to `denied`.
  - Verify staging file is deleted/purged and item is not indexed.

## 2. FastMCP Tool Tests (`tests/test_inbound_mcp_tool.py`)
- **Test 6: FastMCP Tool Call `fetch_inbound_resumes`**
  - Test that the MCP server exposes and executes `fetch_inbound_resumes`.
  - Verify returned dictionary contains structured candidate list with filenames, channels, and metadata.

## 3. Integration & API Tests (`tests/test_inbox_api.py`)
- **Test 7: GET `/inbox/pending-resumes`**
  - Returns HTTP 200 with `PendingResumeResponse`.
- **Test 8: POST `/inbox/sync`**
  - Triggers MCP sync and returns updated pending count.
- **Test 9: POST `/inbox/ingest` & POST `/inbox/deny`**
  - Validates typed payload and updates database records.
