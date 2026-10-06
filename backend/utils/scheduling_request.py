import re
from typing import Any, Dict, List, Optional

from utils.intent_detector import detect_intent
from utils.candidate_resolver import resolve_candidate
from utils.context_manager import (
    extract_candidate_from_history,
    is_candidate_context_reference,
    is_valid_candidate_name,
)


def extract_candidate_name(query: str, chat_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Extract the candidate name from a scheduling request.
    Supports multi-turn context resolution via chat_history.
    """
    # 1. If query contains context coreferences (e.g. 'above candidate', 'him', 'her'),
    # resolve the candidate from recent conversation history.
    if is_candidate_context_reference(query) and chat_history:
        candidate_from_context = extract_candidate_from_history(chat_history)
        if candidate_from_context and is_valid_candidate_name(candidate_from_context):
            return candidate_from_context

    candidate_query = query.casefold()

    # Remove conversational filler phrases
    candidate_query = re.sub(
        r"\b(one\s+more\s+interview|one\s+more|another\s+interview|another|"
        r"today\s+itself|itself|again|also|as\s+well|instead|either|too)\b",
        " ",
        candidate_query,
    )

    # Remove context reference phrases so they aren't parsed as names
    candidate_query = re.sub(
        r"\b(?:the\s+)?above\s+candidate\b|\bcandidate\s+above\b|"
        r"\b(?:the\s+)?previous\s+candidate\b|\b(?:the\s+)?same\s+candidate\b|"
        r"\b(?:this|that|the)\s+candidate\b|\bcandidate\b|"
        r"\b(?:him|her|them)\b",
        " ",
        candidate_query,
    )

    # Remove common scheduling words.
    candidate_query = re.sub(
        r"\b(schedule|reschedule|book|rebook|set|up|arrange|an|the|a|interview|"
        r"interviews|meeting|call|session|slot|for|with|at|on|between|please|"
        r"kindly|me|can|could|would|you)\b",
        " ",
        candidate_query,
    )

    # Remove relative date expressions (including typos like tommorow, tommrow).
    candidate_query = re.sub(
        r"\b(today|day\s+after\s+tom+o*r+o*w?|tom+o*r+o*w?)\b",
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

    # Remove month-based dates (both Month Day like October 7th and Day Month like 7th October).
    month_regex = (
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
        r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    )
    candidate_query = re.sub(
        r"\b\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+" + month_regex + r"(?:,?\s*\d{4})?\b",
        " ",
        candidate_query,
    )
    candidate_query = re.sub(
        r"\b" + month_regex + r"\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?\b",
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
        r"\b(?:UTC(?:[+-]\d{1,2}(?::\d{2})?)?|IST|EST|PST|CST|MST)\b",
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

    cleaned_name = " ".join(candidate_query.split())

    # If a valid candidate name was extracted, return it
    if is_valid_candidate_name(cleaned_name):
        return cleaned_name

    # If no valid name was extracted, fallback to conversation history if available
    if chat_history:
        candidate_from_context = extract_candidate_from_history(chat_history)
        if candidate_from_context and is_valid_candidate_name(candidate_from_context):
            return candidate_from_context

    return ""


def analyze_scheduling_request(query: str, chat_history: Optional[List[Dict[str, Any]]] = None):
    """
    Detect intent and resolve the candidate for scheduling requests.
    Supports multi-turn context resolution via chat_history.
    """

    intent = detect_intent(query)

    if intent != "schedule_interview":
        return {
            "intent": intent,
            "candidate": None,
        }

    candidate_name = extract_candidate_name(query, chat_history=chat_history)

    if not candidate_name or not is_valid_candidate_name(candidate_name):
        return {
            "intent": intent,
            "candidate": None,
            "error": "Candidate name not provided. Which candidate would you like to schedule an interview for?",
        }

    candidate = resolve_candidate(candidate_name)

    if not candidate:
        # Candidate not indexed in resumes/vector DB, but a valid candidate name was provided/resolved
        return {
            "intent": intent,
            "candidate": {
                "candidate_name": candidate_name.title(),
                "email": "",
            },
            "candidate_query": candidate_name,
        }

    return {
        "intent": intent,
        "candidate": candidate,
    }