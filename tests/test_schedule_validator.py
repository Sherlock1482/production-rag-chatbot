from datetime import datetime, timedelta
from utils.schedule_validator import validate_schedule


def test_validate_schedule_valid():
    ref = datetime(2026, 9, 25, 10, 0)
    start = datetime(2026, 10, 2, 15, 0)
    end = start + timedelta(minutes=60)
    result = validate_schedule(start, end, 60, ref)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_schedule_past_date():
    ref = datetime(2026, 9, 25, 10, 0)
    start = datetime(2026, 9, 20, 15, 0)
    end = start + timedelta(minutes=60)
    result = validate_schedule(start, end, 60, ref)
    assert result["valid"] is False
    assert any("future" in err.lower() for err in result["errors"])


def test_validate_schedule_too_short():
    ref = datetime(2026, 9, 25, 10, 0)
    start = datetime(2026, 10, 2, 15, 0)
    end = start + timedelta(minutes=5)
    result = validate_schedule(start, end, 5, ref)
    assert result["valid"] is False
    assert any("at least" in err.lower() for err in result["errors"])


def test_validate_schedule_too_long():
    ref = datetime(2026, 9, 25, 10, 0)
    start = datetime(2026, 10, 2, 15, 0)
    end = start + timedelta(minutes=300)
    result = validate_schedule(start, end, 300, ref)
    assert result["valid"] is False
    assert any("cannot exceed" in err.lower() for err in result["errors"])
