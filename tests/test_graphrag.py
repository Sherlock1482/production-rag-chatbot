import pytest
try:
    # pyrefly: ignore [missing-import]
    from utils.graph_retriever import query_graph_for_recruiter, find_candidates_by_skill
    # pyrefly: ignore [missing-import]
    from guardrails.evidence_guardrail import check_evidence_guardrail
    # pyrefly: ignore [missing-import]
    from guardrails.output_guardrail import check_output_guardrail
except ImportError:
    from backend.utils.graph_retriever import query_graph_for_recruiter, find_candidates_by_skill
    from backend.guardrails.evidence_guardrail import check_evidence_guardrail
    from backend.guardrails.output_guardrail import check_output_guardrail


def test_graphrag_retrieval_observability():
    """Verify that 'observability' query automatically matches candidates with Prometheus or Grafana."""
    result = query_graph_for_recruiter("who has done observability skills")
    assert result["found"] is True
    assert result["query_type"] == "skill_match"
    
    candidates = [c["candidate_name"] for c in result["results"]]
    assert "Alex Mercer" in candidates

    alex = next(c for c in result["results"] if c["candidate_name"] == "Alex Mercer")
    matched_lower = [s.lower() for s in alex["matched_skills"]]
    assert any(tool in matched_lower for tool in ["prometheus", "grafana"])


def test_graphrag_retrieval_python():
    """Verify skill lookup for Python returns Python developers."""
    result = query_graph_for_recruiter("who knows python")
    assert result["found"] is True
    candidates = [c["candidate_name"] for c in result["results"]]
    assert any(name in candidates for name in ["Rajuu Sharma", "Gaurav Pednekar", "Alex Mercer"])


def test_graphrag_retrieval_experience():
    """Verify experience filtering returns candidates with >= 5 years."""
    result = query_graph_for_recruiter("who has more than 5 years of experience")
    assert result["found"] is True
    assert result["query_type"] == "experience_filter"
    for cand in result["results"]:
        assert cand["experience_years"] >= 5.0


def test_evidence_guardrail_with_graph():
    """Verify that evidence guardrail passes when Knowledge Graph provides authoritative data."""
    passed = check_evidence_guardrail(relevant_docs=[], has_graph_evidence=True)
    assert passed is True


def test_output_guardrail_with_graph():
    """Verify that output guardrail recognizes Knowledge Graph context as supporting evidence."""
    passed = check_output_guardrail(
        answer="Alex Mercer has observability skills including Prometheus and Grafana.",
        relevant_docs=[],
        graph_context="Candidate: Alex Mercer. Matched Skills: Prometheus, Grafana via Observability."
    )
    assert passed is True
