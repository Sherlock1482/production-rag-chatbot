import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)


def evaluate_answer(answer: str, expected_keywords: list):

    answer_lower = answer.lower()

    matched_keywords = []

    for keyword in expected_keywords:

        if keyword.lower() in answer_lower:
            matched_keywords.append(keyword)

    accuracy = (
        len(matched_keywords)
        / len(expected_keywords)
    )

    print("\n===== ANSWER EVALUATION =====")

    print(f"Answer: {answer}")

    print(
        f"Expected keywords: "
        f"{expected_keywords}"
    )

    print(
        f"Matched keywords: "
        f"{matched_keywords}"
    )

    print(
        f"Keyword Accuracy: "
        f"{accuracy:.2%}"
    )

    return accuracy


if __name__ == "__main__":

    test_cases = [

        {
            "question": "What skills does Sam Taylor have?",
            "answer": """
            Sam Taylor is a Backend Engineer with skills in
            Python, Java, Spring Boot, PostgreSQL, Docker,
            Redis and REST APIs.
            """,
            "expected_keywords": [
                "Python",
                "Java",
                "Spring Boot",
                "PostgreSQL",
                "Docker",
                "Redis",
                "REST APIs"
            ]
        },

        {
            "question": "What database does Sam Taylor use?",
            "answer": """
            Sam Taylor uses PostgreSQL and Redis in his projects.
            """,
            "expected_keywords": [
                "PostgreSQL",
                "Redis"
            ]
        },

        {
            "question": "What is Sam Taylor's role?",
            "answer": """
            Sam Taylor is a Backend Engineer.
            """,
            "expected_keywords": [
                "Backend Engineer"
            ]
        },

        {
            "question": "What skills does Arjun Kumar have?",
            "answer": """
            Arjun Kumar has skills in Java, Spring Boot,
            Microservices, Docker, Kubernetes, PostgreSQL,
            Kafka and AWS.
            """,
            "expected_keywords": [
                "Java",
                "Spring Boot",
                "Docker",
                "Kubernetes",
                "PostgreSQL",
                "Kafka",
                "AWS"
            ]
        }

    ]

    total_accuracy = 0

    for test in test_cases:

        print("\n----------------------------")
        print(f"Question: {test['question']}")

        accuracy = evaluate_answer(
            test["answer"],
            test["expected_keywords"]
        )

        total_accuracy += accuracy

    average_accuracy = (
        total_accuracy
        / len(test_cases)
    )

    print("\n===== FINAL RESULTS =====")

    print(
        f"Average Answer Accuracy: "
        f"{average_accuracy:.2%}"
    )