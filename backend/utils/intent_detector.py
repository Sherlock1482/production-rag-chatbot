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
        r"\b(?:re-?)?schedule\b",
        r"\b(?:re-?)?book\b",
        r"\bset up\b",
        r"\bset\s+up\b",
        r"\barrange\b",
        r"\bone\s+more\s+interview\b",
        r"\banother\s+interview\b",
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

    # JD fit / gap analysis intent
    jd_fit_patterns = [
        r"\b(?:fit|gap)\s+analysis\b",
        r"\bmatch\s+score\b",
        r"\bscore\s+candidate\b",
        r"\b(?:analyze|evaluate|score)\b.*\b(?:against\s+(?:the\s+)?(?:jd|job\s+description|requirements)|for\s+(?:the\s+)?role)\b",
        r"\b(?:against|with)\s+(?:the\s+)?(?:jd|job\s+description)\b",
        r"\bjd\s+fit\b",
    ]

    for pattern in jd_fit_patterns:
        if re.search(pattern, query_normalized):
            return "analyze_jd_fit"

    # General candidate/RAG search
    return "candidate_search"