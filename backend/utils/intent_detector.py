import re


def detect_intent(query: str) -> str:
    """
    Detect the user's intent.

    Returns:
        schedule_interview
        interview_lookup
        candidate_search
    """

    query_normalized = query.casefold()

    # Scheduling intent
    schedule_patterns = [
        r"\bschedule\b",
        r"\bbook\b",
        r"\bset up\b",
        r"\bset\s+up\b",
        r"\barrange\b",
    ]

    for pattern in schedule_patterns:
        if re.search(pattern, query_normalized):
            return "schedule_interview"

    # Existing interview lookup intent
    interview_patterns = [
        r"\bwhen\b.*\binterview\b",
        r"\bwhere\b.*\binterview\b",
        r"\bwho\b.*\binterview\b",
        r"\binterview\b.*\bstatus\b",
        r"\binterview\b.*\bstage\b",
        r"\binterview\b.*\bscheduled\b",
        r"\binterview\b.*\bdate\b",
        r"\binterview\b.*\btime\b",
    ]

    for pattern in interview_patterns:
        if re.search(pattern, query_normalized):
            return "interview_lookup"

    # General candidate/RAG search
    return "candidate_search"