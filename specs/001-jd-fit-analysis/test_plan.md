# Test Plan 001: Candidate vs. JD Gap & Fit Analysis

## 1. Scope
This test plan validates the data contracts, calculation logic, edge cases, and LLM structured output parsing defined in [`spec.md`](./spec.md).

---

## 2. Test Suite Breakdown (`tests/test_jd_fit_analyzer.py`)

### Test Case 1: Contract Validation (Pydantic Schema)
- **Objective**: Ensure `CandidateFitReport` and `SkillAssessment` enforce all required fields, ranges ($0 \le score \le 100$), and list constraints.
- **Assertion**:
  - Scores $> 100$ or $< 0$ raise `ValidationError`.
  - Confidence $< 0.0$ or $> 1.0$ raise `ValidationError`.
  - Valid dictionary correctly instantiates models without data loss.

### Test Case 2: Deterministic Score Calculation
- **Objective**: Verify mathematical scoring formula:
  $$\text{Score} = (0.75 \times \text{required\_ratio}) + (0.25 \times \text{preferred\_ratio})$$
- **Test Scenarios**:
  1. All required skills matched, all preferred matched $\rightarrow$ 100%.
  2. All required skills matched, 0 preferred matched $\rightarrow$ 75%.
  3. 50% required matched, 100% preferred matched $\rightarrow$ capped at 50% max due to Hard Penalty Invariant.
  4. 0 required skills matched $\rightarrow$ 0% (or capped $\le 25\%$ if preferred match exists).

### Test Case 3: Mock LLM Structured Parsing
- **Objective**: Test that `analyze_candidate_jd_fit(candidate_name, candidate_context, jd_text, llm)` parses LLM JSON outputs cleanly into `CandidateFitReport`.
- **Test Fixture**:
  - Sample Resume: Backend engineer with Python, FastAPI, Docker, Postgres.
  - Sample JD: Senior Backend Engineer needing Python, FastAPI, Postgres (Required), Kubernetes (Preferred).
- **Assertions**:
  - Returns valid `CandidateFitReport` instance.
  - `matched_required_skills` includes "Python", "FastAPI".
  - `missing_preferred_skills` includes "Kubernetes".
  - Probe questions are non-empty list of strings.

### Test Case 4: Edge Case — Empty or Malformed Input
- **Scenario A**: Empty candidate context string $\rightarrow$ raises ValueError or returns graceful missing candidate report.
- **Scenario B**: Empty JD string $\rightarrow$ raises ValueError or prompts for JD input.

### Test Case 5: Prompt Extraction & Formatting
- **Objective**: Ensure the generated prompt sent to Groq includes the strict rubric, grounding instructions, and explicit candidate/JD text blocks.
- **Assertion**: Prompt text contains both candidate context and JD text without truncation.

---

## 3. Execution Command
```powershell
pytest tests/test_jd_fit_analyzer.py -v
```
