import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from utils.graph_db import run_cypher, verify_graph_connection
    from utils.graph_schema import get_expanded_skills
except ImportError:
    from backend.utils.graph_db import run_cypher, verify_graph_connection
    from backend.utils.graph_schema import get_expanded_skills


class ExtractedCandidateProfile(BaseModel):
    candidate_name: str = Field(description="Full name of candidate")
    email: Optional[str] = Field(default="", description="Email address if found")
    current_role: Optional[str] = Field(default="", description="Job title or primary role, e.g. Senior Java Developer")
    years_of_experience: Optional[float] = Field(default=0.0, description="Total years of professional experience as a number")
    skills: List[str] = Field(default_factory=list, description="List of technical skills, languages, tools, frameworks, databases")
    companies: List[str] = Field(default_factory=list, description="List of companies or organizations candidate worked for")


def _get_llm():
    """Initializes Groq LLM client for extraction."""
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        temperature=0.0,
        max_tokens=1024,
    )


def extract_candidate_profile_from_text(text: str, source_name: str = "") -> ExtractedCandidateProfile:
    """
    Extracts structured candidate profile, technical skills, and work history
    from resume/profile text using Groq LLM with a regex fallback.
    """
    if not text or not text.strip():
        return ExtractedCandidateProfile(candidate_name="Unknown")

    prompt = f"""You are an expert recruitment parser. Extract candidate details from the text below into valid JSON.

Document Name: {source_name}
Text:
{text[:4000]}

Respond ONLY with a valid JSON object matching this schema:
{{
  "candidate_name": "Full Name",
  "email": "email@example.com or empty string",
  "current_role": "Primary Job Title or Role",
  "years_of_experience": 5.0,
  "skills": ["Skill1", "Skill2", "Tool1", "Framework1"],
  "companies": ["Company1", "Company2"]
}}

Rules:
1. "skills" must include all technical skills, frameworks, tools, monitoring solutions (e.g. Prometheus, Grafana, Datadog), databases, and platforms explicitly mentioned.
2. If years of experience is described (e.g. '5 years of experience'), return it as a number (5.0).
3. Do not include explanatory text, markdown notes, or code fences outside the JSON.
"""

    try:
        llm = _get_llm()
        response = llm.invoke(prompt)
        raw_content = getattr(response, "content", str(response)).strip()
        
        # Clean potential markdown fences
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_content, re.DOTALL)
        if fence_match:
            clean_json = fence_match.group(1)
        else:
            start = raw_content.find("{")
            end = raw_content.rfind("}")
            clean_json = raw_content[start:end + 1] if start != -1 and end != -1 else raw_content

        data = json.loads(clean_json)
        return ExtractedCandidateProfile(
            candidate_name=str(data.get("candidate_name") or "Unknown").strip(),
            email=str(data.get("email") or "").strip(),
            current_role=str(data.get("current_role") or "").strip(),
            years_of_experience=float(data.get("years_of_experience") or 0.0),
            skills=[str(s).strip() for s in data.get("skills", []) if str(s).strip()],
            companies=[str(c).strip() for c in data.get("companies", []) if str(c).strip()],
        )

    except Exception as e:
        print(f"LLM extraction warning for {source_name}: {e}. Falling back to heuristic extraction.")
        return _fallback_heuristic_extraction(text, source_name)


def _fallback_heuristic_extraction(text: str, source_name: str) -> ExtractedCandidateProfile:
    """Fast regex-based fallback if LLM is unavailable or times out."""
    name = "Unknown Candidate"
    email = ""
    role = ""
    exp = 0.0
    skills = []

    # Name
    m_name = re.search(r"(?im)^(?:candidate\s+name|name)\s*[:\-]\s*(.+)$", text)
    if m_name:
        name = m_name.group(1).strip()
    elif source_name:
        name = Path(source_name).stem.replace("_", " ").title()

    # Email
    m_email = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    if m_email:
        email = m_email.group(0).strip()

    # Role
    m_role = re.search(r"(?im)^role\s*[:\-]\s*(.+)$", text)
    if m_role:
        role = m_role.group(1).strip()

    # Experience
    m_exp = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+of\s+experience", text, re.IGNORECASE)
    if m_exp:
        try:
            exp = float(m_exp.group(1))
        except ValueError:
            pass

    # Skills lines
    in_skills = False
    for line in text.splitlines():
        line_clean = line.strip()
        if re.match(r"(?i)^(technical\s+)?skills\s*[:\-]?", line_clean):
            in_skills = True
            continue
        if in_skills:
            if not line_clean or line_clean.endswith(":") or line_clean.startswith("Professional Summary"):
                in_skills = False
                continue
            item = re.sub(r"^[-*•\d.]\s*", "", line_clean).strip()
            if item:
                skills.extend([s.strip() for s in re.split(r"[,/|]", item) if s.strip()])

    return ExtractedCandidateProfile(
        candidate_name=name,
        email=email,
        current_role=role,
        years_of_experience=exp,
        skills=list(dict.fromkeys(skills)),
        companies=[],
    )


def ingest_candidate_to_graph(profile: ExtractedCandidateProfile, source_doc: str = "") -> dict:
    """
    Upserts candidate node and connects relationships to Skills, Role, and Companies in Neo4j.
    """
    if not profile.candidate_name or profile.candidate_name.lower() in ["unknown", ""]:
        print(f"Skipping candidate ingestion: missing name in {source_doc}")
        return {"status": "skipped", "reason": "missing_name"}

    # Deterministic Candidate ID based primarily on candidate name
    clean_identifier = profile.candidate_name.lower().strip()
    cand_id = f"cand_{hashlib.md5(clean_identifier.encode('utf-8')).hexdigest()[:12]}"

    # 1. Upsert Candidate Node
    cand_query = """
    MERGE (c:Candidate {id: $id})
    SET c.name = $name,
        c.email = $email,
        c.experience_years = $exp,
        c.role = $role,
        c.source_doc = $source_doc
    RETURN c.id AS candidate_id
    """
    run_cypher(cand_query, {
        "id": cand_id,
        "name": profile.candidate_name,
        "email": profile.email,
        "exp": profile.years_of_experience,
        "role": profile.current_role,
        "source_doc": source_doc,
    })

    # 2. Link Role if present
    if profile.current_role:
        role_norm = profile.current_role.lower().strip()
        role_query = """
        MATCH (c:Candidate {id: $id})
        MERGE (r:Role {normalized_name: $role_norm})
        ON CREATE SET r.name = $role_name
        MERGE (c)-[:HELD_ROLE]->(r)
        """
        run_cypher(role_query, {
            "id": cand_id,
            "role_norm": role_norm,
            "role_name": profile.current_role,
        })

    # 3. Link Companies
    if profile.companies:
        comp_query = """
        MATCH (c:Candidate {id: $id})
        UNWIND $companies AS comp_name
        WITH c, comp_name, toLower(trim(comp_name)) AS comp_norm
        WHERE comp_norm <> ''
        MERGE (cmp:Company {normalized_name: comp_norm})
        ON CREATE SET cmp.name = trim(comp_name)
        MERGE (c)-[:WORKED_AT]->(cmp)
        """
        run_cypher(comp_query, {
            "id": cand_id,
            "companies": profile.companies,
        })

    # 4. Link Skills
    # Normalize skills and connect HAS_SKILL relationships
    cleaned_skills = []
    for s in profile.skills:
        clean = s.strip()
        if clean and len(clean) > 1:
            cleaned_skills.append({
                "raw_name": clean,
                "norm_name": clean.lower()
            })

    if cleaned_skills:
        skill_query = """
        MATCH (c:Candidate {id: $id})
        UNWIND $skills AS item
        MERGE (s:Skill {normalized_name: item.norm_name})
        ON CREATE SET s.name = item.raw_name, s.is_category = false
        MERGE (c)-[:HAS_SKILL]->(s)
        """
        run_cypher(skill_query, {
            "id": cand_id,
            "skills": cleaned_skills,
        })

    print(
        f"Ingested '{profile.candidate_name}' into Neo4j: "
        f"{len(cleaned_skills)} skills, role='{profile.current_role}', exp={profile.years_of_experience} yrs"
    )

    return {
        "status": "success",
        "candidate_id": cand_id,
        "candidate_name": profile.candidate_name,
        "skills_linked": len(cleaned_skills),
    }


def ingest_document_to_graph(full_text: str, source_doc: str) -> dict:
    """
    End-to-end wrapper: Extracts candidate profile from text and writes to Neo4j.
    """
    profile = extract_candidate_profile_from_text(full_text, source_doc)
    return ingest_candidate_to_graph(profile, source_doc)


if __name__ == "__main__":
    print("Testing Graph Extractor and Backfilling existing resumes...")
    if verify_graph_connection():
        data_resumes = BACKEND_DIR / "data" / "resumes"
        if data_resumes.exists():
            for f in sorted(data_resumes.glob("*.txt")):
                print(f"\nProcessing {f.name}...")
                with open(f, "r", encoding="utf-8", errors="ignore") as file_in:
                    content = file_in.read()
                res = ingest_document_to_graph(content, f.name)
                print(f"Result: {res}")
