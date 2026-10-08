import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

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


def _get_llm():
    """Initializes Groq LLM for Cypher generation and query analysis."""
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        temperature=0.0,
        max_tokens=512,
    )


def find_candidates_by_skill(skill_name: str) -> List[Dict]:
    """
    Finds candidates possessing a skill, automatically expanding parent 
    taxonomies (e.g. 'observability' -> 'prometheus', 'grafana', 'datadog').
    """
    clean_skill = skill_name.strip().lower()

    # Query Neo4j: Find target skill or any child tool connected via SUB_CATEGORY_OF
    cypher = """
    MATCH (target:Skill)
    WHERE target.normalized_name = $skill_name 
       OR toLower(target.name) = $skill_name
    
    // Find any child skills under this category
    OPTIONAL MATCH (child:Skill)-[:SUB_CATEGORY_OF*1..2]->(target)
    
    WITH collect(DISTINCT target) + collect(DISTINCT child) AS relevant_skills
    UNWIND relevant_skills AS s
    MATCH (c:Candidate)-[:HAS_SKILL]->(s)
    
    RETURN c.name AS candidate_name,
           c.role AS role,
           c.experience_years AS experience_years,
           c.email AS email,
           c.source_doc AS source_doc,
           collect(DISTINCT s.name) AS matched_skills
    ORDER BY c.experience_years DESC
    """

    results = run_cypher(cypher, {"skill_name": clean_skill})

    # Fallback if no exact match on Skill node yet: fuzzy match across all Skill nodes
    if not results:
        fuzzy_cypher = """
        MATCH (s:Skill)
        WHERE s.normalized_name CONTAINS $skill_name 
           OR toLower(s.name) CONTAINS $skill_name
        MATCH (c:Candidate)-[:HAS_SKILL]->(s)
        RETURN c.name AS candidate_name,
               c.role AS role,
               c.experience_years AS experience_years,
               c.email AS email,
               c.source_doc AS source_doc,
               collect(DISTINCT s.name) AS matched_skills
        ORDER BY c.experience_years DESC
        """
        results = run_cypher(fuzzy_cypher, {"skill_name": clean_skill})

    return results


def find_candidates_by_experience(min_years: float, role_keyword: Optional[str] = None) -> List[Dict]:
    """Finds candidates with >= min_years of experience, optionally filtered by role."""
    cypher = """
    MATCH (c:Candidate)
    WHERE c.experience_years >= $min_years
    """
    params = {"min_years": float(min_years)}

    if role_keyword:
        cypher += " AND (toLower(c.role) CONTAINS toLower($role) OR EXISTS { MATCH (c)-[:HELD_ROLE]->(r:Role) WHERE toLower(r.name) CONTAINS toLower($role) })"
        params["role"] = role_keyword.strip()

    cypher += """
    OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
    RETURN c.name AS candidate_name,
           c.role AS role,
           c.experience_years AS experience_years,
           c.email AS email,
           c.source_doc AS source_doc,
           collect(DISTINCT s.name) AS all_skills
    ORDER BY c.experience_years DESC
    """
    return run_cypher(cypher, params)


def get_candidate_profile(candidate_name: str) -> Optional[Dict]:
    """Retrieves full candidate entity graph profile."""
    cypher = """
    MATCH (c:Candidate)
    WHERE toLower(c.name) CONTAINS toLower($name)
    OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
    OPTIONAL MATCH (c)-[:WORKED_AT]->(cmp:Company)
    OPTIONAL MATCH (c)-[:HELD_ROLE]->(r:Role)
    RETURN c.name AS candidate_name,
           coalesce(c.role, r.name) AS role,
           c.experience_years AS experience_years,
           c.email AS email,
           c.source_doc AS source_doc,
           collect(DISTINCT s.name) AS skills,
           collect(DISTINCT cmp.name) AS companies
    LIMIT 1
    """
    results = run_cypher(cypher, {"name": candidate_name.strip()})
    return results[0] if results else None


def list_all_candidates_in_graph() -> List[Dict]:
    """Returns an overview of all candidate nodes currently in Neo4j."""
    cypher = """
    MATCH (c:Candidate)
    OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
    RETURN c.name AS candidate_name,
           c.role AS role,
           c.experience_years AS experience_years,
           c.source_doc AS source_doc,
           count(DISTINCT s) AS skill_count
    ORDER BY c.name ASC
    """
    return run_cypher(cypher)


def execute_text_to_cypher(natural_query: str) -> Dict:
    """
    Translates free-form user question to safe read-only Cypher query using Groq LLM.
    """
    schema_prompt = """You are a Neo4j Cypher generator for a Talent Acquisition Knowledge Graph.
Graph Schema:
- (:Candidate {id, name, email, experience_years, role, source_doc})
- (:Skill {name, normalized_name, is_category})
- (:Role {name, normalized_name})
- (:Company {name, normalized_name})
- Relationships:
  (:Candidate)-[:HAS_SKILL]->(:Skill)
  (:Candidate)-[:HELD_ROLE]->(:Role)
  (:Candidate)-[:WORKED_AT]->(:Company)
  (:Skill)-[:SUB_CATEGORY_OF]->(:Skill)

Write a READ-ONLY Cypher query to answer the question.
Rules:
1. ONLY write MATCH and RETURN statements.
2. NEVER write CREATE, DELETE, DETACH, SET, REMOVE, DROP, or ALTER.
3. Use case-insensitive matching (e.g. toLower(s.name) CONTAINS ... or toLower(c.name)).
4. Return clean columns like candidate_name, role, experience_years, source_doc, matched_skills.
5. Return ONLY the raw Cypher query text without markdown quotes or explanation.

Question: """ + natural_query

    try:
        llm = _get_llm()
        resp = llm.invoke(schema_prompt)
        cypher_text = getattr(resp, "content", str(resp)).strip()
        
        # Clean markdown fences
        cypher_text = re.sub(r"^```(?:cypher)?\s*", "", cypher_text)
        cypher_text = re.sub(r"\s*```$", "", cypher_text).strip()

        # Security check: Read-only check
        forbidden = ["create", "delete", "detach", "set", "remove", "drop", "alter"]
        if any(re.search(rf"\b{f}\b", cypher_text, re.IGNORECASE) for f in forbidden):
            return {"success": False, "error": "Unsafe query generated"}

        data = run_cypher(cypher_text)
        return {"success": True, "cypher": cypher_text, "results": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_graph_context(results: List[Dict], query_topic: str) -> str:
    """Formats retrieved graph records into clean markdown for prompt injection."""
    if not results:
        return f"No candidate records found in the Knowledge Graph for '{query_topic}'."

    lines = [f"=== KNOWLEDGE GRAPH VERIFIED DATA (Topic: {query_topic}) ==="]
    for i, cand in enumerate(results, start=1):
        name = cand.get("candidate_name") or cand.get("name") or "Unknown Candidate"
        role = cand.get("role") or "Not Specified"
        exp = cand.get("experience_years")
        exp_str = f"{exp} years" if exp is not None else "Not Specified"
        doc = cand.get("source_doc") or "Knowledge Base"

        skills = cand.get("matched_skills") or cand.get("skills") or cand.get("all_skills") or []
        skills_str = ", ".join(skills) if skills else "None listed"

        lines.append(f"[{i}] Candidate: {name}")
        lines.append(f"    - Role: {role}")
        lines.append(f"    - Experience: {exp_str}")
        lines.append(f"    - Matched Skills/Tools: {skills_str}")
        lines.append(f"    - Source Document: {doc}")
        lines.append("")

    return "\n".join(lines).strip()


def query_graph_for_recruiter(query: str) -> Dict:
    """
    Main entry point for GraphRAG query execution.
    Inspects intent and extracts relevant graph facts.
    """
    q_lower = query.lower().strip()

    # 1. Experience Query (e.g. "who has more than 5 years", "candidates with 4+ years")
    exp_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", q_lower)
    if ("experience" in q_lower or "years" in q_lower) and exp_match:
        years = float(exp_match.group(1))
        role_kw = None
        for r in ["developer", "engineer", "java", "python", "frontend", "backend", "devops", "cloud"]:
            if r in q_lower:
                role_kw = r
                break
        candidates = find_candidates_by_experience(years, role_kw)
        return {
            "found": len(candidates) > 0,
            "results": candidates,
            "query_type": "experience_filter",
            "context": format_graph_context(candidates, f">= {years} years experience")
        }

    # 2. Specific Candidate Profile Lookup
    cand_match = re.search(r"\b(?:about|profile\s+of|skills\s+of|details\s+for)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b", q_lower)
    if cand_match:
        target_name = cand_match.group(1)
        profile = get_candidate_profile(target_name)
        if profile:
            return {
                "found": True,
                "results": [profile],
                "query_type": "candidate_profile",
                "context": format_graph_context([profile], f"Candidate Profile: {target_name}")
            }

    # 3. Skill & Technology Queries (e.g. "who has done observability skills", "who knows python")
    # Extract likely skill keywords
    clean_skill_q = re.sub(
        r"\b(who|which|candidate|candidates|has|have|done|knows|know|with|experience|in|skills?|technologies|tools?|the|a|an|tell|me|show|find|list|is|are)\b",
        " ",
        q_lower
    )
    extracted_skills = [w.strip() for w in clean_skill_q.split() if len(w.strip()) > 1]

    # Test each extracted word against graph taxonomy or skills
    matched_candidates = []
    searched_topic = ""
    for kw in extracted_skills:
        res = find_candidates_by_skill(kw)
        if res:
            matched_candidates = res
            searched_topic = kw
            break

    if matched_candidates:
        return {
            "found": True,
            "results": matched_candidates,
            "query_type": "skill_match",
            "context": format_graph_context(matched_candidates, f"Skill: {searched_topic}")
        }

    # 4. Fallback to Text-to-Cypher for arbitrary query
    cypher_run = execute_text_to_cypher(query)
    if cypher_run.get("success") and cypher_run.get("results"):
        return {
            "found": True,
            "results": cypher_run["results"],
            "query_type": "cypher_custom",
            "context": format_graph_context(cypher_run["results"], f"Query: {query}")
        }

    return {
        "found": False,
        "results": [],
        "query_type": "none",
        "context": ""
    }


if __name__ == "__main__":
    print("Testing Graph Retriever...")
    if verify_graph_connection():
        # Test 1: Observability skill query
        print("\n--- Test 1: 'who has done observability skills' ---")
        out1 = query_graph_for_recruiter("who has done observability skills")
        print("Found:", out1["found"])
        print(out1["context"])

        # Test 2: Python skill query
        print("\n--- Test 2: 'who knows python' ---")
        out2 = query_graph_for_recruiter("who knows python")
        print("Found:", out2["found"])
        print(out2["context"])

        # Test 3: Experience filter query
        print("\n--- Test 3: 'who has more than 5 years of experience' ---")
        out3 = query_graph_for_recruiter("who has more than 5 years of experience")
        print("Found:", out3["found"])
        print(out3["context"])
