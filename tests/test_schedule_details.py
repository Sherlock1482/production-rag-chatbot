# pyrefly: ignore [missing-import]
from utils.schedule_details import get_missing_schedule_details


def test_schedule_details_complete():
    query = "Schedule Rajuu Sharma on October 2 at 3 PM for 30 minutes"
    result = get_missing_schedule_details(query)
    assert result["complete"] is True
    assert len(result["missing"]) == 0
    assert result["details"]["date"] is not None
    assert result["details"]["time"] is not None


def test_schedule_details_missing_time():
    query = "Schedule Rajuu Sharma on October 2"
    result = get_missing_schedule_details(query)
    assert result["complete"] is False
    assert "time" in result["missing"]


def test_schedule_details_missing_date():
    query = "Schedule Rajuu Sharma at 3 PM"
    result = get_missing_schedule_details(query)
    assert result["complete"] is False
    assert "date" in result["missing"]


def test_schedule_details_missing_all():
    query = "Schedule Rajuu Sharma's interview"
    result = get_missing_schedule_details(query)
    assert result["complete"] is False
    assert "date" in result["missing"]
    assert "time" in result["missing"]
