# pyrefly: ignore [missing-import]
import pytest
from pydantic import ValidationError
# pyrefly: ignore [missing-import]
from utils.jd_fit_analyzer import (
    CandidateFitReport,
    calculate_fit_score,
    build_jd_fit_prompt,
    analyze_candidate_jd_fit,
)


def test_models_validation():
    # Valid report
    report = CandidateFitReport(
        candidate_name="Priya Patel",
        target_role="Senior Backend Engineer",
        match_score_percent=85,
        matched_required_skills=["Python", "FastAPI", "PostgreSQL"],
        missing_required_skills=["Docker"],
        matched_preferred_skills=["Redis"],
        missing_preferred_skills=["Kubernetes"],
        core_strengths=["Strong API development experience", "Postgres optimization"],
        suggested_probe_questions=["How have you managed containerization without Docker?"],
        executive_summary="Strong match for backend core requirements.",
    )
    assert report.match_score_percent == 85
    assert len(report.matched_required_skills) == 3

    # Out of range match score
    with pytest.raises(ValidationError):
        CandidateFitReport(
            candidate_name="Priya Patel",
            target_role="Engineer",
            match_score_percent=150,  # Invalid: > 100
            core_strengths=[],
            suggested_probe_questions=[],
            executive_summary="",
        )


def test_calculate_fit_score_deterministic():
    # 1. 100% match on both required and preferred
    score = calculate_fit_score(
        matched_required=4, total_required=4,
        matched_preferred=2, total_preferred=2
    )
    assert score == 100

    # 2. 100% required (4/4), 0% preferred (0/2) -> 75%
    score = calculate_fit_score(
        matched_required=4, total_required=4,
        matched_preferred=0, total_preferred=2
    )
    assert score == 75

    # 3. Only required skills specified (no preferred) -> 100% required weight
    score = calculate_fit_score(
        matched_required=3, total_required=4,
        matched_preferred=0, total_preferred=0
    )
    assert score == 75

    # 4. Hard penalty invariant: < 50% required matched -> max score 50%
    # e.g., 1 of 4 required matched (25%), but 2 of 2 preferred matched (100%)
    # Normal weighted: 0.75 * 0.25 + 0.25 * 1.0 = 0.1875 + 0.25 = 43.75% -> capped at 50%
    score = calculate_fit_score(
        matched_required=1, total_required=4,
        matched_preferred=2, total_preferred=2
    )
    assert score <= 50

    # 5. Zero required matched -> 0 or <= 25
    score = calculate_fit_score(
        matched_required=0, total_required=4,
        matched_preferred=0, total_preferred=2
    )
    assert score == 0


def test_build_jd_fit_prompt():
    prompt = build_jd_fit_prompt(
        candidate_name="Arjun Kumar",
        candidate_context="Arjun has 5 years DevOps experience with Terraform, Ansible, AWS.",
        jd_text="Looking for a DevOps Engineer with Terraform, Kubernetes, and CI/CD."
    )
    assert "Arjun Kumar" in prompt
    assert "Terraform" in prompt
    assert "Kubernetes" in prompt
    assert "EVIDENCE GROUNDING" in prompt


def test_analyze_candidate_jd_fit_mock():
    class DummyLLM:
        def invoke(self, messages):
            class Response:
                content = """{
                    "candidate_name": "Priya Patel",
                    "target_role": "Backend Engineer",
                    "match_score_percent": 88,
                    "matched_required_skills": ["Python", "FastAPI"],
                    "missing_required_skills": ["Kafka"],
                    "matched_preferred_skills": ["Docker"],
                    "missing_preferred_skills": [],
                    "core_strengths": ["High-throughput API development"],
                    "suggested_probe_questions": ["Explain how you would introduce Kafka for event streaming."],
                    "executive_summary": "Priya matches key backend skills but lacks Kafka experience."
                }"""
            return Response()

    report = analyze_candidate_jd_fit(
        candidate_name="Priya Patel",
        candidate_context="Priya is proficient in Python, FastAPI, and Docker.",
        jd_text="Backend Engineer: Requires Python, FastAPI, Kafka. Preferred: Docker.",
        llm=DummyLLM()
    )

    assert isinstance(report, CandidateFitReport)
    assert report.candidate_name == "Priya Patel"
    assert "Python" in report.matched_required_skills
    assert "Kafka" in report.missing_required_skills
    assert report.match_score_percent == 88


def test_analyze_empty_inputs():
    with pytest.raises(ValueError, match="Candidate context cannot be empty"):
        analyze_candidate_jd_fit("Priya", "", "JD Text")

    with pytest.raises(ValueError, match="Job Description cannot be empty"):
        analyze_candidate_jd_fit("Priya", "Resume context", "")


def test_format_fit_report_markdown():
    # pyrefly: ignore [missing-import]
    from utils.jd_fit_analyzer import format_fit_report_markdown
    report = CandidateFitReport(
        candidate_name="Priya Patel",
        target_role="Senior Backend Engineer",
        match_score_percent=85,
        matched_required_skills=["Python", "FastAPI"],
        missing_required_skills=["Kubernetes"],
        matched_preferred_skills=["Docker"],
        missing_preferred_skills=[],
        core_strengths=["API architecture"],
        suggested_probe_questions=["How do you deploy without K8s?"],
        executive_summary="Solid candidate for python backend.",
    )
    md = format_fit_report_markdown(report)
    assert "CANDIDATE FIT & GAP ANALYSIS: PRIYA PATEL" in md
    assert "Match Score: 85%" in md
    assert "Python" in md
    assert "Kubernetes" in md
    assert "How do you deploy without K8s?" in md


def test_extract_text_from_pdf_invalid():
    import io
    # pyrefly: ignore [missing-import]
    from utils.jd_fit_analyzer import extract_text_from_pdf
    with pytest.raises(ValueError, match="Could not parse PDF"):
        extract_text_from_pdf(io.BytesIO(b"invalid pdf content"))


def test_clean_candidate_name():
    # pyrefly: ignore [missing-import]
    from utils.jd_fit_analyzer import clean_candidate_name

    assert clean_candidate_name("Aarav Sharma", "Aarav Sharma.pdf") == "Aarav Sharma"
    assert clean_candidate_name("SHIVAM Software Development Engineer", "Shivam.pdf") == "Shivam"
    assert clean_candidate_name("TECHNICAL SKILLS", "alex.pdf") == "Alex"
    assert clean_candidate_name("", "Avery_Chen_Resume.docx") == "Avery Chen"
    assert clean_candidate_name(None, "Rajdeep.pdf") == "Rajdeep"
    assert clean_candidate_name("Vikram Malhotra Etc Excel", "Vikram Malhotra etc excel.xlsx") == "Vikram Malhotra"
    assert clean_candidate_name(None, "Vikram Malhotra etc excel.xlsx") == "Vikram Malhotra"


def test_analyze_top_candidates_for_jd_mock(monkeypatch):
    # pyrefly: ignore [missing-import]
    from utils.jd_fit_analyzer import analyze_top_candidates_for_jd

    # Mock find_top_candidates_from_qdrant
    mock_candidates = [
        {
            "candidate_name": "Aarav Sharma",
            "source": "Aarav Sharma.pdf",
            "context": "Aarav has 7 years experience in Distributed Systems and Python.",
            "score": 0.88,
        },
        {
            "candidate_name": "Shivam",
            "source": "Shivam.pdf",
            "context": "Shivam has 4 years experience in FastAPI and PostgreSQL.",
            "score": 0.82,
        },
        {
            "candidate_name": "Alex",
            "source": "alex.pdf",
            "context": "Alex is experienced in React and frontend architecture.",
            "score": 0.74,
        },
    ]

    monkeypatch.setattr(
        "utils.jd_fit_analyzer.find_top_candidates_from_qdrant",
        lambda jd_text, top_n=3, collection_name="ta_documents": mock_candidates[:top_n],
    )

    class MockLLM:
        def invoke(self, prompt):
            class Response:
                content = """{
                    "candidate_name": "Evaluated Candidate",
                    "target_role": "Backend Engineer",
                    "match_score_percent": 85,
                    "matched_required_skills": ["Python"],
                    "missing_required_skills": [],
                    "core_strengths": ["FastAPI architecture"],
                    "suggested_probe_questions": ["Explain your system design approach."],
                    "executive_summary": "Strong fit for the position."
                }"""
            return Response()

    result = analyze_top_candidates_for_jd(
        jd_text="Looking for a Python Backend Engineer with distributed systems expertise.",
        top_n=3,
        llm=MockLLM(),
    )

    assert "top_candidates" in result
    assert len(result["top_candidates"]) == 3
    assert "markdown_report" in result
    assert "CANDIDATE MATCH & COMPARISON SUMMARY" in result["markdown_report"].upper()
    assert "Aarav Sharma.pdf" in result["sources"]
    # Verify no unreadable unicode bullets or em-dashes
    assert "•" not in result["markdown_report"]
    assert "—" not in result["markdown_report"]
    # Verify concise report without redundant breakdown
    assert "DETAILED CANDIDATE EVALUATION BREAKDOWN" not in result["markdown_report"]



