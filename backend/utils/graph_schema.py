"""
Graph Database Schema & Skill Taxonomy Initializer.
Sets up uniqueness constraints, indexes, and foundational domain ontologies (e.g., Observability).
"""
import sys
from pathlib import Path

# Add backend directory to sys.path so utils can be imported from root or backend
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from utils.graph_db import run_cypher, verify_graph_connection
except ImportError:
    from backend.utils.graph_db import run_cypher, verify_graph_connection

def init_graph_schema():
    """Creates uniqueness constraints and indexes for nodes."""
    print("Setting up Neo4j schema constraints and indexes...")

    # Constraints ensure unique entity identity and create automatic B-tree indexes
    constraints = [
        # Candidate uniqueness by ID or Email
        """
        CREATE CONSTRAINT candidate_id_unique IF NOT EXISTS
        FOR (c:Candidate) REQUIRE c.id IS UNIQUE
        """,
        # Skill uniqueness by normalized lowercase name
        """
        CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
        FOR (s:Skill) REQUIRE s.normalized_name IS UNIQUE
        """,
        # Company uniqueness
        """
        CREATE CONSTRAINT company_name_unique IF NOT EXISTS
        FOR (cmp:Company) REQUIRE cmp.normalized_name IS UNIQUE
        """,
        # Role uniqueness
        """
        CREATE CONSTRAINT role_name_unique IF NOT EXISTS
        FOR (r:Role) REQUIRE r.normalized_name IS UNIQUE
        """,
    ]

    for cypher in constraints:
        try:
            run_cypher(cypher)
        except Exception as e:
            print(f"Notice on constraint creation: {e}")

    print("Schema constraints and indexes established successfully.")


def seed_skill_taxonomy():
    """
    Seeds core technology taxonomies into the graph.
    Connects specific tools to parent domains (e.g. Prometheus -> Observability).
    """
    print("Seeding technology and skills taxonomy...")

    # Define Parent Domain -> Sub-skills / Tools mapping
    taxonomy = {
        "observability": {
            "display_name": "Observability",
            "category": "DevOps & SRE",
            "children": [
                "prometheus", "grafana", "datadog", "opentelemetry", 
                "jaeger", "elk stack", "elasticsearch", "logstash", 
                "kibana", "cloudwatch", "dynatrace", "new relic", 
                "splunk", "distributed tracing", "metrics", "apm"
            ]
        },
        "cloud computing": {
            "display_name": "Cloud Computing",
            "category": "Infrastructure",
            "children": [
                "aws", "azure", "gcp", "google cloud", "amazon web services",
                "terraform", "cloudformation"
            ]
        },
        "containerization": {
            "display_name": "Containerization & Orchestration",
            "category": "DevOps & Infrastructure",
            "children": [
                "docker", "kubernetes", "k8s", "helm", "openshift", "containerd"
            ]
        },
        "database": {
            "display_name": "Databases",
            "category": "Data & Storage",
            "children": [
                "postgresql", "mysql", "mongodb", "redis", "qdrant", 
                "neo4j", "elasticsearch", "cassandra", "sqlite"
            ]
        },
        "backend": {
            "display_name": "Backend Engineering",
            "category": "Software Development",
            "children": [
                "fastapi", "flask", "django", "spring boot", "nodejs", 
                "express", "microservices", "rest api", "graphql", "grpc"
            ]
        },
        "ai & machine learning": {
            "display_name": "AI & Machine Learning",
            "category": "Artificial Intelligence",
            "children": [
                "rag", "langchain", "llamaindex", "pytorch", "tensorflow", 
                "llm", "embeddings", "nlp", "transformers", "vector search"
            ]
        }
    }

    # Cypher query to merge parent and child skill nodes, and link them via SUB_CATEGORY_OF
    seed_query = """
    UNWIND $data AS domain
    MERGE (parent:Skill {normalized_name: domain.parent_name})
    ON CREATE SET parent.name = domain.display_name, parent.category = domain.category, parent.is_category = true
    ON MATCH SET parent.name = domain.display_name, parent.category = domain.category, parent.is_category = true

    WITH parent, domain
    UNWIND domain.children AS child_name
    MERGE (child:Skill {normalized_name: child_name})
    ON CREATE SET child.name = toUpper(substring(child_name, 0, 1)) + substring(child_name, 1, size(child_name)),
                  child.is_category = false
    MERGE (child)-[:SUB_CATEGORY_OF]->(parent)
    """

    payload = []
    for parent_key, details in taxonomy.items():
        payload.append({
            "parent_name": parent_key,
            "display_name": details["display_name"],
            "category": details["category"],
            "children": details["children"]
        })

    run_cypher(seed_query, {"data": payload})
    print(f"Successfully seeded {len(taxonomy)} domain categories and child skills into Neo4j!")


def get_expanded_skills(skill_query: str) -> list[str]:
    """
    Given a skill name (e.g. 'observability'), returns all synonymous and 
    child tool skills (e.g. ['prometheus', 'grafana', 'datadog', ...]).
    """
    clean_skill = skill_query.strip().lower()
    
    query = """
    MATCH (target:Skill)
    WHERE target.normalized_name = $skill_name 
       OR toLower(target.name) = $skill_name
    
    // Find child skills if target is a category
    OPTIONAL MATCH (child:Skill)-[:SUB_CATEGORY_OF*1..2]->(target)
    
    // Find parent category and siblings if target is a tool
    OPTIONAL MATCH (target)-[:SUB_CATEGORY_OF]->(parent:Skill)<-[:SUB_CATEGORY_OF]-(sibling:Skill)
    
    RETURN target.normalized_name AS primary,
           collect(DISTINCT child.normalized_name) AS children,
           collect(DISTINCT sibling.normalized_name) AS siblings
    """
    
    results = run_cypher(query, {"skill_name": clean_skill})
    if not results:
        return [clean_skill]

    row = results[0]
    expanded = set()
    if row.get("primary"):
        expanded.add(row["primary"])
    if row.get("children"):
        expanded.update(row["children"])
    
    # Filter out None values
    return [s for s in expanded if s]


if __name__ == "__main__":
    if verify_graph_connection():
        init_graph_schema()
        seed_skill_taxonomy()
        
        # Test query for 'observability'
        test_expanded = get_expanded_skills("observability")
        print("\nTest Taxonomy Lookup for 'observability':")
        print(test_expanded)
