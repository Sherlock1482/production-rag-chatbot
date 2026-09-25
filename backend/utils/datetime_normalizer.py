from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


TIMEZONE_MAP = {
    "IST": "Asia/Kolkata",
    "UTC": "UTC",
    "EST": "America/New_York",
    "CST": "America/Chicago",
    "MST": "America/Denver",
    "PST": "America/Los_Angeles",
}


def normalize_datetime(
    details: dict,
    reference_datetime: datetime | None = None,
):
    """
    Convert extracted date/time values into timezone-aware
    normalized datetime values.

    Expected output:
        start_datetime
        end_datetime
        duration_minutes
        timezone
    """

    timezone_value = details.get("timezone") or "UTC"

    timezone_name = TIMEZONE_MAP.get(
        timezone_value.upper(),
        timezone_value,
    )

    try:
        timezone = ZoneInfo(timezone_name)
    except Exception:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "duration_minutes": details.get("duration_minutes") or 60,
            "timezone": timezone_value,
            "error": f"Unsupported timezone: {timezone_value}",
        }

    if reference_datetime is None:
        reference_datetime = datetime.now(timezone)

    elif reference_datetime.tzinfo is None:
        reference_datetime = reference_datetime.replace(
            tzinfo=timezone
        )

    date_value = details.get("date")
    time_value = details.get("time")
    duration_minutes = details.get("duration_minutes") or 60

    if not date_value or not time_value:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "duration_minutes": duration_minutes,
            "timezone": timezone_value,
            "error": "Date and time are required.",
        }

    # -------------------------
    # Parse date
    # -------------------------

    parsed_date = None

    date_formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%B %d",
        "%b %d, %Y",
        "%b %d",
    ]

    for date_format in date_formats:
        try:
            parsed_date = datetime.strptime(
                date_value.replace("st", "")
                .replace("nd", "")
                .replace("rd", "")
                .replace("th", ""),
                date_format,
            )
            break
        except ValueError:
            continue

    # Relative dates
    if not parsed_date:
        if date_value == "today":
            parsed_date = reference_datetime

        elif date_value == "tomorrow":
            parsed_date = reference_datetime + timedelta(days=1)

        elif date_value == "day after tomorrow":
            parsed_date = reference_datetime + timedelta(days=2)

    if not parsed_date:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "duration_minutes": duration_minutes,
            "timezone": timezone_value,
            "error": f"Unable to understand date: {date_value}",
        }

    # If year wasn't supplied, use reference year.
    if parsed_date.year == 1900:
        parsed_date = parsed_date.replace(
            year=reference_datetime.year
        )

    # -------------------------
    # Parse time
    # -------------------------

    parsed_time = None

    time_formats = [
        "%I:%M%p",
        "%I%p",
        "%H:%M",
    ]

    for time_format in time_formats:
        try:
            parsed_time = datetime.strptime(
                time_value.upper(),
                time_format,
            )
            break
        except ValueError:
            continue

    if not parsed_time:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "duration_minutes": duration_minutes,
            "timezone": timezone_value,
            "error": f"Unable to understand time: {time_value}",
        }

    # -------------------------
    # Combine date + time
    # -------------------------

    start_datetime = parsed_date.replace(
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=0,
        microsecond=0,
        tzinfo=timezone,
    )

    end_datetime = start_datetime + timedelta(
        minutes=duration_minutes
    )

    return {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "duration_minutes": duration_minutes,
        "timezone": timezone_value,
        "error": None,
    }