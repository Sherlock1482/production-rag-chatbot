# Spec 001: Candidate vs. Job Description (JD) Gap & Fit Analysis

## 1. Overview & Objective
Recruiters frequently need to evaluate how well a candidate's resume matches a specific Job Description (JD). 
Today, doing this manually requires cross-referencing multiple pages of requirements with resume experience, often taking 15–30 minutes per candidate.

This feature enables the recruiter to provide a Job Description (either pasted in the prompt, referenced from an ingested document, or specified as a target role) and a candidate name, and receive a **deterministic, structured Candidate Fit & Gap Analysis Report**.

---

## 2. Architectural Flow

```
                      User Prompt:
       "Analyze Priya Patel against Senior Backend Engineer JD: ..."
                                │
                                ▼
               ┌───────────────────────────────────┐
               │ backend/utils/intent_detector.py │
               │   Intent: `analyze_jd_fit`        │
               └────────────────┬──────────────────┘
                                │
                                ▼
               ┌───────────────────────────────────┐
               │ 1. Extract Candidate & JD Content │
               │    - Candidate name resolution    │
               │    - JD text / role extraction    │
               └────────────────┬──────────────────┘
                                │
                                ▼
               ┌───────────────────────────────────┐
               │ 2. Qdrant Context Retrieval       │
               │    - Retrieve candidate's chunks  │
               │    - Retrieve JD chunks (if ref)  │
               └────────────────┬──────────────────┘
                                │
                                ▼
               ┌───────────────────────────────────┐
               │ 3. Structured LLM Fit Engine      │
               │    (backend/utils/jd_fit_analyzer)│
               │    - Groq LLM + Pydantic schema   │
               │    - Evidence quote extraction    │
               │    - Score computation            │
               └────────────────┬──────────────────┘
                                │
                                ▼
               ┌───────────────────────────────────┐
               │ 4. Response & Observability       │
               │    - Langfuse span: "jd-fit-eval" │
               │    - Structured Markdown / JSON   │
               └───────────────────────────────────┘
```

---

## 3. Data Contracts (Pydantic Models)

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class SkillAssessment(BaseModel):
    skill_name: str = Field(
        description="Name of the skill, technology, or domain concept."
    )
    is_required: bool = Field(
        description="True if stated as mandatory/required in the JD; False if nice-to-have/preferred."
    )
    found_in_resume: bool = Field(
        description="True if explicit or strong semantic evidence of this skill exists in the candidate's resume."
    )
    evidence_snippet: Optional[str] = Field(
        default=None,
        description="Verbatim or close excerpt from the resume demonstrating the skill. Null if missing."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0) of the match."
    )

class CandidateFitReport(BaseModel):
    candidate_name: str = Field(
        description="Full name of the candidate evaluated."
    )
    target_role: str = Field(
        description="Target job title or role evaluated against."
    )
    match_score_percent: int = Field(
        ge=0,
        le=100,
        description="Overall match percentage from 0 to 100 based on required and preferred criteria."
    )
    matched_required_skills: List[str] = Field(
        default_factory=list,
        description="List of mandatory skills present in candidate resume."
    )
    missing_required_skills: List[str] = Field(
        default_factory=list,
        description="List of mandatory skills missing from candidate resume."
    )
    matched_preferred_skills: List[str] = Field(
        default_factory=list,
        description="List of nice-to-have skills found."
    )
    missing_preferred_skills: List[str] = Field(
        default_factory=list,
        description="List of nice-to-have skills not found."
    )
    core_strengths: List[str] = Field(
        description="Top 2-4 verified candidate strengths relevant to the position."
    )
    suggested_probe_questions: List[str] = Field(
        description="Targeted technical/behavioral interview questions designed to test identified gaps or verify experience depth."
    )
    executive_summary: str = Field(
        description="2-3 sentence objective overview of candidate suitability."
    )
```

---

## 4. Scoring Algorithm & Invariants

To avoid arbitrary numbers, the match score calculation must follow these rules:

1. **Weight Distribution**:
   - Required skills count for **75%** of the score.
   - Nice-to-have / preferred skills count for **25%** of the score.
   
   $$\text{Score} = \left(0.75 \times \frac{\text{matched\_required}}{\text{total\_required}}\right) + \left(0.25 \times \frac{\text{matched\_preferred}}{\text{total\_preferred}}\right)$$
   *(If no preferred skills are specified in the JD, required skills account for 100%).*

2. **Hard Penalty Invariant**:
   - If **more than 50%** of the required skills are missing, the overall score cannot exceed **50%**, regardless of preferred skills.

3. **Grounding Invariant**:
   - `evidence_snippet` must come from the actual candidate context. Skills may NOT be assumed based on job titles alone (e.g., cannot assume "Kubernetes" just because the title is "DevOps Engineer" unless Kubernetes is documented).

---

## 5. Intent Detection & Triggering

The intent detector (`backend/utils/intent_detector.py`) will identify queries with the intent `analyze_jd_fit`:
* Keywords: `"fit analysis"`, `"gap analysis"`, `"match score"`, `"score candidate"`, `"compare against jd"`, `"evaluate candidate for"`.
* Entities extracted:
  - `candidate_name`: Extracted from query or resolved from conversational history (`context_manager.py`).
  - `job_description_text`: Text provided in query or extracted from ingested JD document.

---

## 6. Acceptance Criteria (BDD Scenarios)

### Scenario 1: Candidate with Strong Match
* **Given** candidate "Priya Patel" with resume mentioning Python, FastAPI, Docker, and PostgreSQL
* **And** a JD requiring Python, FastAPI, and PostgreSQL (Required), with Kubernetes (Preferred)
* **When** fit analysis is requested
* **Then** `match_score_percent` is $\ge 75\%$
* **And** `matched_required_skills` includes Python, FastAPI, PostgreSQL
* **And** `missing_preferred_skills` includes Kubernetes
* **And** `suggested_probe_questions` includes a question probing container orchestration/Kubernetes experience.

### Scenario 2: Candidate Missing Core Requirements
* **Given** candidate "John Doe" with resume focusing on Frontend (React, CSS, HTML)
* **And** a JD requiring Java, Spring Boot, Microservices, and Kafka
* **When** fit analysis is requested
* **Then** `match_score_percent` is $\le 30\%$
* **And** `missing_required_skills` contains Java, Spring Boot, Microservices, Kafka
* **And** `suggested_probe_questions` focuses on backend readiness and distributed systems experience.

### Scenario 3: Missing Candidate in Knowledge Base
* **Given** a query requesting fit analysis for "Unknown Person"
* **When** Qdrant search returns no candidate documents
* **Then** the system returns a polite, structured error: "No resume or profile found for Unknown Person in the knowledge base."
* **And** no hallucinated report is generated.

### Scenario 4: Missing or Empty Job Description
* **Given** a query "Score Priya Patel" without providing a JD or target role
* **When** no target role can be resolved
* **Then** the system prompts the recruiter: "Please provide the Job Description or specify the target role to analyze Priya Patel against."
