import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from pathlib import Path

# Ensure root and backend are in sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_live_chat_observability():
    print("\n" + "=" * 60)
    print("TEST 1: 'who has done observability skills'")
    print("=" * 60)
    
    response = client.post(
        "/chat",
        json={
            "query": "who has done observability skills",
            "session_id": "test_e2e_obs"
        }
    )
    
    assert response.status_code == 200
    answer = response.text
    print("\n--- CHATBOT RESPONSE ---")
    print(answer)
    print("------------------------\n")
    
    # Assertions
    assert "couldn't find enough relevant information" not in answer.lower(), "Guardrail incorrectly blocked the response!"
    assert "Alex Mercer" in answer or "alex" in answer.lower(), "Expected Alex Mercer to be identified!"
    assert "Rajdeep.pdf" in answer or "knowledge graph" in answer.lower(), "Expected source citation!"
    print(">>> TEST 1 PASSED: Alex Mercer successfully identified with Observability skills!")


def test_live_chat_python():
    print("\n" + "=" * 60)
    print("TEST 2: 'who knows python'")
    print("=" * 60)
    
    response = client.post(
        "/chat",
        json={
            "query": "who knows python",
            "session_id": "test_e2e_python"
        }
    )
    
    assert response.status_code == 200
    answer = response.text
    print("\n--- CHATBOT RESPONSE ---")
    print(answer)
    print("------------------------\n")
    
    assert "couldn't find enough relevant information" not in answer.lower()
    # At least one known Python developer should be present
    found_py_dev = any(name in answer for name in ["Rajuu Sharma", "Gaurav Pednekar", "Alex Mercer", "Morgan Riley", "Damu"])
    assert found_py_dev, "Expected Python developers to be listed!"
    print(">>> TEST 2 PASSED: Python developers successfully identified!")


def test_live_chat_experience():
    print("\n" + "=" * 60)
    print("TEST 3: 'who has more than 5 years of experience'")
    print("=" * 60)
    
    response = client.post(
        "/chat",
        json={
            "query": "who has more than 5 years of experience",
            "session_id": "test_e2e_exp"
        }
    )
    
    assert response.status_code == 200
    answer = response.text
    print("\n--- CHATBOT RESPONSE ---")
    print(answer)
    print("------------------------\n")
    
    assert "couldn't find enough relevant information" not in answer.lower()
    found_senior = any(name in answer for name in ["Arjun Kumar", "Damu B", "Rajuu Sharma"])
    assert found_senior, "Expected candidates with >= 5 years experience to be listed!"
    print(">>> TEST 3 PASSED: Candidates with > 5 years experience successfully identified!")


if __name__ == "__main__":
    test_live_chat_observability()
    test_live_chat_python()
    test_live_chat_experience()
    print("\n" + "=" * 60)
    print("ALL END-TO-END GRAPHRAG TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
