import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

_driver: Driver | None = None


def get_graph_driver() -> Driver:
    """Returns a singleton Neo4j driver instance."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    return _driver


def close_graph_driver():
    """Closes the Neo4j driver connection."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def verify_graph_connection() -> bool:
    """Verifies that the Neo4j database is reachable and authenticated."""
    try:
        driver = get_graph_driver()
        driver.verify_connectivity()
        print("Connected to Neo4j successfully!")
        return True
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return False


def run_cypher(query: str, parameters: dict = None) -> list:
    """Executes a Cypher query and returns the results as a list of dictionaries."""
    driver = get_graph_driver()
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


if __name__ == "__main__":
    print("Testing Neo4j connection...")
    if verify_graph_connection():
        # Quick query test
        res = run_cypher("RETURN 'Neo4j is online!' AS message")
        print("Test Query Result:", res)
