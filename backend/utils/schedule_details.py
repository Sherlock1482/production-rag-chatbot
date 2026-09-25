from utils.datetime_extractor import extract_datetime_details


DEFAULT_DURATION_MINUTES = 60


def get_missing_schedule_details(query: str):
    """
    Extract scheduling details and determine what information is missing.
    """

    details = extract_datetime_details(query)

    missing = []

    if not details["date"]:
        missing.append("date")

    if not details["time"]:
        missing.append("time")

    # Use 60 minutes as the default interview duration.
    if not details["duration_minutes"]:
        details["duration_minutes"] = DEFAULT_DURATION_MINUTES

    return {
        "details": details,
        "missing": missing,
        "complete": len(missing) == 0,
    }
