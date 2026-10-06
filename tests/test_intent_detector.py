# pyrefly: ignore [missing-import]
from utils.intent_detector import detect_intent


def test_detect_intent_schedule():
    assert detect_intent("Schedule Rajuu Sharma's interview") == "schedule_interview"
    assert detect_intent("Book an interview for Priya Patel") == "schedule_interview"
    assert detect_intent("Set up an interview with Arjun Kumar") == "schedule_interview"
    assert detect_intent("Arrange an interview for tomorrow") == "schedule_interview"


def test_detect_intent_lookup():
    assert detect_intent("When is Rajuu Sharma's interview?") == "interview_lookup"
    assert detect_intent("Where is Priya's interview?") == "interview_lookup"
    assert detect_intent("What is the interview status for Arjun?") == "interview_lookup"
    assert detect_intent("What is the interview stage for Jane?") == "interview_lookup"


def test_detect_intent_candidate_search():
    assert detect_intent("What skills does Rajuu Sharma have?") == "candidate_search"
    assert detect_intent("Find candidates with Python and FastAPI experience") == "candidate_search"
    assert detect_intent("Compare Priya and Arjun for backend engineer") == "candidate_search"


def test_detect_intent_jd_fit():
    assert detect_intent("Run a fit analysis for Priya Patel against the Senior Backend Engineer JD") == "analyze_jd_fit"
    assert detect_intent("Perform gap analysis for Arjun against the DevOps requirements") == "analyze_jd_fit"
    assert detect_intent("What is the match score for Jane Doe for this job description?") == "analyze_jd_fit"
    assert detect_intent("Evaluate candidate Priya Patel against JD: Python FastAPI developer") == "analyze_jd_fit"
