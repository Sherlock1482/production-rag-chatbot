import re
from datetime import datetime


def extract_datetime_details(query: str):
    """
    Extract basic date, time, duration, and timezone information
    from a scheduling query.

    This step only extracts information.
    It does not validate or schedule anything yet.
    """

    result = {
        "date": None,
        "time": None,
        "duration_minutes": None,
        "timezone": None,
    }

    query_normalized = query.casefold()

    # -------------------------
    # Time
    # -------------------------
    time_patterns = [
        r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b",
        r"\b\d{1,2}\s*(?:am|pm)\b",
    ]

    for pattern in time_patterns:
        match = re.search(pattern, query_normalized)
        if match:
            result["time"] = match.group(0).replace(" ", "")
            break

    # -------------------------
    # Duration
    # -------------------------
    duration_match = re.search(
        r"\b(\d+)\s*(minutes?|mins?|hours?|hrs?)\b",
        query_normalized,
    )

    if duration_match:
        value = int(duration_match.group(1))
        unit = duration_match.group(2)

        if unit.startswith("hour") or unit.startswith("hr"):
            value *= 60

        result["duration_minutes"] = value

    # -------------------------
    # Timezone
    # -------------------------
    timezone_patterns = [
        r"\bUTC[+-]\d{1,2}(?::\d{2})?\b",
        r"\bIST\b",
        r"\bEST\b",
        r"\bPST\b",
        r"\bCST\b",
        r"\bMST\b",
    ]

    for pattern in timezone_patterns:
        match = re.search(pattern, query_normalized, re.IGNORECASE)
        if match:
            result["timezone"] = match.group(0).upper()
            break

    # -------------------------
    # Date
    # -------------------------
    month_regex = (
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
        r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    )

    date_patterns = [
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        # Day Month (e.g., 7th October, 7th of October, 7 Oct, 7 October 2026)
        r"\b\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+" + month_regex + r"(?:,?\s*\d{4})?\b",
        # Month Day (e.g., October 7th, Oct 7, October 7, 2026)
        r"\b" + month_regex + r"\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?\b",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, query_normalized)
        if match:
            result["date"] = match.group(0)
            break

    # Relative dates (tolerant of typos like tommorow, tomorow, tommrow)
    if re.search(r"\bday\s+after\s+tom+o*r+o*w?\b", query_normalized):
        result["date"] = "day after tomorrow"
    elif re.search(r"\btom+o*r+o*w?\b", query_normalized):
        result["date"] = "tomorrow"
    elif re.search(r"\btoday\b", query_normalized):
        result["date"] = "today"


    return result