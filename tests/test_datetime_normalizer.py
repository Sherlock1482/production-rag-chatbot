from datetime import datetime
# pyrefly: ignore [missing-import]
from utils.datetime_normalizer import normalize_datetime


def test_normalize_datetime_iso_date():
    ref = datetime(2026, 9, 25, 10, 0)
    details = {
        "date": "2026-10-02",
        "time": "3pm",
        "duration_minutes": 60,
    }
    result = normalize_datetime(details, reference_datetime=ref)
    assert result["start_datetime"] is not None
    assert result["end_datetime"] is not None
    assert result["duration_minutes"] == 60
    assert result["start_datetime"].year == 2026
    assert result["start_datetime"].month == 10
    assert result["start_datetime"].day == 2
    assert result["start_datetime"].hour == 15


def test_normalize_datetime_with_timezone():
    ref = datetime(2026, 9, 25, 10, 0)
    details = {
        "date": "2026-10-02",
        "time": "3pm",
        "duration_minutes": 60,
        "timezone": "IST",
    }
    result = normalize_datetime(details, reference_datetime=ref)
    assert result["start_datetime"] is not None
    assert str(result["start_datetime"].tzinfo) == "Asia/Kolkata"


def test_normalize_datetime_relative_today():
    ref = datetime(2026, 9, 25, 10, 0)
    details = {
        "date": "today",
        "time": "4pm",
        "duration_minutes": 30,
    }
    result = normalize_datetime(details, reference_datetime=ref)
    assert result["start_datetime"] is not None
    assert result["start_datetime"].day == 25
    assert result["duration_minutes"] == 30


def test_normalize_datetime_relative_tomorrow():
    ref = datetime(2026, 9, 25, 10, 0)
    details = {
        "date": "tomorrow",
        "time": "11am",
        "duration_minutes": 45,
    }
    result = normalize_datetime(details, reference_datetime=ref)
    assert result["start_datetime"] is not None
    assert result["start_datetime"].day == 26


def test_normalize_datetime_missing_inputs():
    result = normalize_datetime({})
    assert result["start_datetime"] is None
    assert "error" in result


def test_normalize_datetime_day_month_ordinal():
    ref = datetime(2026, 9, 25, 10, 0)
    details = {
        "date": "7th october",
        "time": "9am",
        "duration_minutes": 60,
    }
    result = normalize_datetime(details, reference_datetime=ref)
    assert result["start_datetime"] is not None
    assert result["start_datetime"].year == 2026
    assert result["start_datetime"].month == 10
    assert result["start_datetime"].day == 7
    assert result["start_datetime"].hour == 9
    assert result["end_datetime"].hour == 10
