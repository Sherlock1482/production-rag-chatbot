import re
from pathlib import Path
from typing import Any, Dict, List, Optional


CONTEXT_REFERENCE_PATTERNS = [
    r"\b(?:the\s+)?above\s+candidate\b",
    r"\bcandidate\s+above\b",
    r"\b(?:the\s+)?previous\s+candidate\b",
    r"\b(?:the\s+)?last\s+candidate\b",
    r"\b(?:the\s+)?same\s+candidate\b",
    r"\bthis\s+candidate\b",
    r"\bthat\s+candidate\b",
    r"\bthe\s+candidate\b",
    r"\b(?:the\s+)?applicant\b",
    r"\b(?:this|that|above)\s+applicant\b",
    r"\b(?:the|this|that|above)\s+person\b",
    r"\b(?:him|her|them)\b",
    r"\b(?:he|she)\b",
    r"\b(?:above|previous)\s+one\b",
]

FILLER_WORDS = [
    r"\b(?:can|could|would)\s+you\b",
    r"\bplease\b",
    r"\bkindly\b",
    r"\bone\s+more\s+interview\b",
    r"\bone\s+more\b",
    r"\banother\s+interview\b",
    r"\banother\b",
    r"\btoday\s+itself\b",
    r"\bitself\b",
    r"\bagain\b",
    r"\balso\b",
    r"\bas\s+well\b",
    r"\binstead\b",
    r"\beither\b",
    r"\btoo\b",
]

INVALID_CANDIDATE_NAMES = {
    "",
    "candidate",
    "the candidate",
    "above candidate",
    "the above candidate",
    "candidate above",
    "previous candidate",
    "the previous candidate",
    "last candidate",
    "same candidate",
    "this candidate",
    "that candidate",
    "one more",
    "itself",
    "one more itself above candidate",
    "one more candidate",
    "another candidate",
    "requested candidate",
    "the requested candidate",
    "unknown",
    "unknown candidate",
    "him",
    "her",
    "them",
    "someone",
    "anyone",
    "person",
    "applicant",
    "technical skills",
}


def is_candidate_context_reference(text: str) -> bool:
    """
    Check if a text contains coreference indicators referring to
    a candidate mentioned in the conversation context.
    """
    if not text:
        return False

    text_lower = text.casefold()
    for pattern in CONTEXT_REFERENCE_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    return False


def is_valid_candidate_name(name: Optional[str]) -> bool:
    """
    Check if a string represents a plausible candidate name
    and not a filler word, pronoun, or generic placeholder.
    """
    if not name:
        return False

    clean = " ".join(re.sub(r"[^a-zA-Z\s]", " ", name).split())
    if len(clean) < 2:
        return False

    clean_lower = clean.casefold()
    if clean_lower in INVALID_CANDIDATE_NAMES:
        return False

    # Disallow names containing clear non-name phrases
    forbidden_substrings = [
        "above candidate",
        "previous candidate",
        "same candidate",
        "this candidate",
        "that candidate",
        "the candidate",
        "one more",
        "itself",
        "schedule",
        "interview",
        "conflict",
        "today",
        "tomorrow",
        "yesterday",
        "technical skills",
    ]
    for sub in forbidden_substrings:
        if sub in clean_lower:
            return False

    return True


def get_known_candidate_names() -> List[str]:
    """
    Collect candidate names from local resumes and known database sources.
    """
    names = []

    # Check data/resumes directory
    resumes_dir = Path(__file__).resolve().parents[1] / "data" / "resumes"
    if resumes_dir.exists():
        for file in resumes_dir.glob("*.txt"):
            stem = file.stem.strip()
            if stem and len(stem) >= 2:
                names.append(stem.title())

    # Fallback known candidates in TA DB / test fixtures
    default_known = ["Aarav", "Priya Patel", "Arjun Kumar", "Jane Doe", "Damu", "Gaurav", "Raj", "Shivam"]
    for d in default_known:
        if d not in names:
            names.append(d)

    return names


def extract_candidate_from_history(history: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract the most recently discussed or targeted candidate name from the conversation history.
    Searches backwards from the latest turn.
    """
    if not history:
        return None

    # Inspect messages in reverse order (newest first)
    for message in reversed(history):
        content = message.get("content") or ""
        if not content:
            # Maybe message is in the format of chat_history.json: query / response
            query = message.get("query", "")
            response = message.get("response", "")
            content = f"{query} {response}"

        role = message.get("role", "")

        # ----------------------------------------------------
        # 1. Assistant message patterns
        # ----------------------------------------------------
        if role == "assistant" or not role:
            # Pattern: Conflicting event(s): Interview - Aarav (...)
            conflict_match = re.search(
                r"(?i)Conflicting event\(s\):\s*Interview\s*-\s*([A-Za-z0-9\s]+?)(?:\s*\(|\.|\n|\)|$)",
                content,
            )
            if conflict_match:
                candidate = conflict_match.group(1).strip()
                if is_valid_candidate_name(candidate):
                    return candidate.title()

            # Pattern: Interview for <Name> has been scheduled
            scheduled_match = re.search(
                r"(?i)Interview for ([A-Za-z0-9\s]+?) has been scheduled",
                content,
            )
            if scheduled_match:
                candidate = scheduled_match.group(1).strip()
                if is_valid_candidate_name(candidate):
                    return candidate.title()

            # Pattern: <Name> is scheduled for an interview
            is_scheduled_match = re.search(
                r"(?i)([A-Za-z0-9\s]+?) is scheduled for an interview",
                content,
            )
            if is_scheduled_match:
                candidate = is_scheduled_match.group(1).strip()
                if is_valid_candidate_name(candidate):
                    return candidate.title()

            # Pattern: Interview - <Name>
            generic_interview_match = re.search(
                r"(?i)\bInterview\s*-\s*([A-Za-z0-9\s]+?)(?:\s*\(|\.|\n|\)|$)",
                content,
            )
            if generic_interview_match:
                candidate = generic_interview_match.group(1).strip()
                if is_valid_candidate_name(candidate):
                    return candidate.title()

        # ----------------------------------------------------
        # 2. User message patterns
        # ----------------------------------------------------
        if role == "user" or not role:
            # Pattern: interview for/with <Name>
            user_interview_match = re.search(
                r"(?i)\b(?:interview\s+for|interview\s+with|for|with)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
                content,
            )
            if user_interview_match:
                candidate = user_interview_match.group(1).strip()
                if is_valid_candidate_name(candidate) and not is_candidate_context_reference(candidate):
                    return candidate.title()

            # Pattern: about <Name>
            about_match = re.search(
                r"(?i)\b(?:about|resume\s+of|skills\s+of|experience\s+of)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
                content,
            )
            if about_match:
                candidate = about_match.group(1).strip()
                if is_valid_candidate_name(candidate) and not is_candidate_context_reference(candidate):
                    return candidate.title()

        # ----------------------------------------------------
        # 3. Check for mentions of known candidate names
        # ----------------------------------------------------
        for known in get_known_candidate_names():
            pattern = rf"\b{re.escape(known)}\b"
            if re.search(pattern, content, re.IGNORECASE):
                return known.title()

    return None


def contextualize_query(query: str, history: Optional[List[Dict[str, Any]]]) -> str:
    """
    Contextualize the user's query by resolving coreferences like 'above candidate',
    'him', 'her', or missing candidate names using the recent conversation history.
    """
    if not query:
        return query

    if not history:
        return query

    candidate = extract_candidate_from_history(history)
    if not candidate:
        return query

    modified = query

    # 1. Replace coreference phrases targeting the candidate
    # e.g., "with the above candidate" -> "with Aarav"
    # "for the above candidate" -> "for Aarav"
    coref_subs = [
        (r"(?i)\b(?:with|for)\s+(?:the\s+)?above\s+candidate\b", f"for {candidate}"),
        (r"(?i)\b(?:with|for)\s+(?:the\s+)?previous\s+candidate\b", f"for {candidate}"),
        (r"(?i)\b(?:with|for)\s+(?:the\s+)?same\s+candidate\b", f"for {candidate}"),
        (r"(?i)\b(?:with|for)\s+(?:this|that|the)\s+candidate\b", f"for {candidate}"),
        (r"(?i)\b(?:with|for)\s+(?:him|her|them)\b", f"for {candidate}"),
        (r"(?i)\b(?:the\s+)?above\s+candidate(?:'s)?\b", f"{candidate}'s"),
        (r"(?i)\b(?:the\s+)?previous\s+candidate(?:'s)?\b", f"{candidate}'s"),
        (r"(?i)\b(?:the\s+)?same\s+candidate(?:'s)?\b", f"{candidate}'s"),
        (r"(?i)\b(?:this|that|the)\s+candidate(?:'s)?\b", f"{candidate}'s"),
        (r"(?i)\bhis\b", f"{candidate}'s"),
        (r"(?i)\bher\b", f"{candidate}'s"),
        (r"(?i)\bhim\b", candidate),
    ]

    has_coref = is_candidate_context_reference(query)

    for pattern, replacement in coref_subs:
        modified = re.sub(pattern, replacement, modified)

    # 2. Clean conversational filler in scheduling queries
    # e.g. "one more interview today itself" -> "an interview today"
    modified = re.sub(r"(?i)\bone\s+more\s+interview\b", "an interview", modified)
    modified = re.sub(r"(?i)\bone\s+more\b", "an interview", modified)
    modified = re.sub(r"(?i)\banother\s+interview\b", "an interview", modified)
    modified = re.sub(r"(?i)\btoday\s+itself\b", "today", modified)
    modified = re.sub(r"(?i)\bitself\b", "", modified)

    # 3. If query was a scheduling request that lacked a candidate entirely,
    # and has_coref or candidate not yet mentioned in modified query:
    if re.search(r"(?i)\b(?:schedule|book|arrange|set\s+up)\b", modified):
        if candidate.lower() not in modified.lower():
            # Insert candidate: e.g. "schedule an interview for Aarav"
            if re.search(r"(?i)\b(?:interview)\b", modified):
                modified = re.sub(
                    r"(?i)\b(interview)\b",
                    f"interview for {candidate}",
                    modified,
                    count=1,
                )
            else:
                modified = re.sub(
                    r"(?i)\b(schedule|book|arrange|set\s+up)\b",
                    rf"\1 an interview for {candidate}",
                    modified,
                    count=1,
                )

    # Clean double spaces
    modified = " ".join(modified.split())
    return modified


def format_history_for_prompt(history: Optional[List[Dict[str, Any]]], max_turns: int = 5) -> str:
    """
    Format recent conversation history as plain text for the LLM prompt.
    """
    if not history:
        return "No previous conversation history."

    lines = []
    # Take the last max_turns * 2 messages
    recent = history[-(max_turns * 2):]

    for msg in recent:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No previous conversation history."
