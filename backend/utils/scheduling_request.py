import re

from utils.intent_detector import detect_intent
from utils.candidate_resolver import resolve_candidate


def extract_candidate_name(query: str) -> str:
    """
    Extract the candidate name from a scheduling request.
    """

    candidate_query = query.casefold()

    # Remove common scheduling words.
    candidate_query = re.sub(
        r"\b(schedule|book|set|up|arrange|an|the|interview|"
        r"for|with|at|please|me|can|you)\b",        " ",
        candidate_query,
    )

    # Remove relative date expressions.
    candidate_query = re.sub(
        r"\b(today|tomorrow|day\s+after\s+tomorrow)\b",
        " ",
        candidate_query,
    )

    # Remove explicit dates such as:
    # 2026-10-02
    # 10/02/2026
    candidate_query = re.sub(
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        " ",
        candidate_query,
    )

    candidate_query = re.sub(
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        " ",
        candidate_query,
    )

    # Remove month-based dates.
    candidate_query = re.sub(
        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
        r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+\d{1,2}(?:st|nd|rd|th)?"
        r"(?:,\s*\d{4})?\b",
        " ",
        candidate_query,
    )

    # Remove time such as:
    # 8:30 PM
    # 8 PM
    candidate_query = re.sub(
        r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b",
        " ",
        candidate_query,
    )

    candidate_query = re.sub(
        r"\b\d{1,2}\s*(?:am|pm)\b",
        " ",
        candidate_query,
    )

    # Remove duration such as:
    # 30 minutes
    # 1 hour
    candidate_query = re.sub(
        r"\b\d+\s*(?:minutes?|mins?|hours?|hrs?)\b",
        " ",
        candidate_query,
    )

    # Remove timezone.
    candidate_query = re.sub(
        r"\b(?:UTC[+-]\d{1,2}(?::\d{2})?|IST|EST|PST|CST|MST)\b",
        " ",
        candidate_query,
        flags=re.IGNORECASE,
    )

    # Remove possessive "'s".
    candidate_query = re.sub(
        r"'s\b",
        "",
        candidate_query,
    )

    # Keep only letters/numbers/spaces.
    candidate_query = re.sub(
        r"[^a-z0-9\s]",
        " ",
        candidate_query,
    )

    return " ".join(candidate_query.split())

def analyze_scheduling_request(query: str):
    """
    Detect intent and resolve the candidate for scheduling requests.
    """

    intent = detect_intent(query)

    if intent != "schedule_interview":
        return {
            "intent": intent,
            "candidate": None,
        }

    candidate_name = extract_candidate_name(query)

    if not candidate_name:
        return {
            "intent": intent,
            "candidate": None,
            "error": "Candidate name not provided.",
        }

    candidate = resolve_candidate(candidate_name)

    if not candidate:
        return {
            "intent": intent,
            "candidate": None,
            "candidate_query": candidate_name,
            "error": "Candidate not found.",
        }

    return {
        "intent": intent,
        "candidate": candidate,
    }