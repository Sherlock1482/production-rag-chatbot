from typing import Any, Dict, List, Optional
from utils.datetime_extractor import extract_datetime_details


DEFAULT_DURATION_MINUTES = 60


def get_missing_schedule_details(query: str, chat_history: Optional[List[Dict[str, Any]]] = None):
    """
    Extract scheduling details and determine what information is missing.
    Optionally inherits date, time, or duration from recent chat_history turns.
    """

    details = extract_datetime_details(query)

    # If date is missing and history exists, check if date can be inferred from recent turns
    if not details["date"] and chat_history:
        for msg in reversed(chat_history):
            content = msg.get("content") or msg.get("query", "")
            hist_details = extract_datetime_details(content)
            if hist_details.get("date"):
                details["date"] = hist_details["date"]
                break

    # If time is missing and history exists, check if time can be inferred
    if not details["time"] and chat_history:
        for msg in reversed(chat_history):
            content = msg.get("content") or msg.get("query", "")
            hist_details = extract_datetime_details(content)
            if hist_details.get("time"):
                details["time"] = hist_details["time"]
                break

    missing = []

    if not details["date"]:
        missing.append("date")

    if not details["time"]:
        missing.append("time")

    # Inherit duration from recent turn if available, else default to 60 minutes
    if not details["duration_minutes"]:
        inherited_duration = None
        if chat_history:
            for msg in reversed(chat_history):
                content = msg.get("content") or msg.get("query", "")
                hist_details = extract_datetime_details(content)
                if hist_details.get("duration_minutes"):
                    inherited_duration = hist_details["duration_minutes"]
                    break
        details["duration_minutes"] = inherited_duration or DEFAULT_DURATION_MINUTES

    return {
        "details": details,
        "missing": missing,
        "complete": len(missing) == 0,
    }
