# pyrefly: ignore [missing-import]
from utils.context_manager import (
    extract_candidate_from_history,
    contextualize_query,
    is_candidate_context_reference,
    is_valid_candidate_name,
)
# pyrefly: ignore [missing-import]
from utils.scheduling_request import (
    analyze_scheduling_request,
)
# pyrefly: ignore [missing-import]
from utils.schedule_details import get_missing_schedule_details


def test_is_candidate_context_reference():
    assert is_candidate_context_reference("with the above candidate") is True
    assert is_candidate_context_reference("for the above candidate") is True
    assert is_candidate_context_reference("schedule for him") is True
    assert is_candidate_context_reference("schedule for her") is True
    assert is_candidate_context_reference("what about this candidate") is True
    assert is_candidate_context_reference("schedule an interview for Aarav") is False


def test_is_valid_candidate_name():
    assert is_valid_candidate_name("Aarav") is True
    assert is_valid_candidate_name("Priya Patel") is True
    assert is_valid_candidate_name("One More Itself Above Candidate") is False
    assert is_valid_candidate_name("above candidate") is False
    assert is_valid_candidate_name("him") is False
    assert is_valid_candidate_name("") is False


def test_extract_candidate_from_conflict_response():
    history = [
        {"role": "user", "content": "can you schedule an interview for Aarav tomorrow at 7 PM for 2 hours?"},
        {
            "role": "assistant",
            "content": "The requested time is unavailable. Conflicting event(s): Interview - Aarav (2026-10-06T19:00:00Z).",
        },
    ]
    candidate = extract_candidate_from_history(history)
    assert candidate == "Aarav"


def test_extract_candidate_from_scheduled_response():
    history = [
        {"role": "user", "content": "schedule an interview for Shivam tomorrow at 4am"},
        {
            "role": "assistant",
            "content": "Interview for Shivam has been scheduled successfully for Tuesday, October 06, 2026 at 04:00 AM UTC.",
        },
    ]
    candidate = extract_candidate_from_history(history)
    assert candidate == "Shivam"


def test_extract_candidate_from_user_query():
    history = [
        {"role": "user", "content": "can you schedule an interview for Arjun Kumar tomorrow at 10 AM?"},
        {"role": "assistant", "content": "Please provide the interview duration."},
    ]
    candidate = extract_candidate_from_history(history)
    assert candidate == "Arjun Kumar"


def test_contextualize_query_with_above_candidate():
    history = [
        {"role": "user", "content": "can you schedule an interview for Aarav tomorrow at 7 PM for 2 hours?"},
        {
            "role": "assistant",
            "content": "The requested time is unavailable. Conflicting event(s): Interview - Aarav (2026-10-06T19:00:00Z).",
        },
    ]
    query = "Can you schedule one more interview today itself with the above candidate today at 7pm for 2hrs?"
    contextualized = contextualize_query(query, history)
    assert "Aarav" in contextualized
    assert "above candidate" not in contextualized.lower()
    assert "itself" not in contextualized.lower()


def test_contextualize_query_pronouns():
    history = [
        {"role": "user", "content": "Tell me about Damu"},
        {"role": "assistant", "content": "Damu is a Senior Backend Developer with 5 years of experience."},
    ]
    query = "What are his skills?"
    contextualized = contextualize_query(query, history)
    assert "Damu" in contextualized


def test_scheduling_request_resolves_above_candidate_with_history():
    history = [
        {"role": "user", "content": "can you schedule an interview for Aarav tomorrow at 7 PM for 2 hours?"},
        {
            "role": "assistant",
            "content": "The requested time is unavailable. Conflicting event(s): Interview - Aarav (2026-10-06T19:00:00Z).",
        },
    ]
    query = "Can you schedule one more interview today itself with the above candidate today at 7pm for 2hrs?"
    result = analyze_scheduling_request(query, chat_history=history)

    assert result["intent"] == "schedule_interview"
    assert result["candidate"] is not None
    assert result["candidate"]["candidate_name"] == "Aarav"


def test_scheduling_request_without_history_does_not_produce_junk_name():
    query = "Can you schedule one more interview today itself with the above candidate today at 7pm for 2hrs?"
    result = analyze_scheduling_request(query, chat_history=[])

    assert result["intent"] == "schedule_interview"
    assert result["candidate"] is None
    assert "error" in result


def test_schedule_details_with_context():
    history = [
        {"role": "user", "content": "schedule interview for Aarav tomorrow for 2 hours"},
    ]
    query = "at 7pm"
    details = get_missing_schedule_details(query, chat_history=history)
    assert details["complete"] is True
    assert details["details"]["time"] == "7pm"
    assert details["details"]["date"] == "tomorrow"
    assert details["details"]["duration_minutes"] == 120
