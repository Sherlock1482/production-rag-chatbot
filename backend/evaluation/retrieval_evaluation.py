import sys
from pathlib import Path

# Add backend folder to Python path
sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

from utils.retriever import search_and_rerank


def evaluate_retrieval(query: str, expected_source: str):

    results = search_and_rerank(
        query=query,
        top_k=5,
        top_n=3
    )

    correct_rank = None

    for idx, result in enumerate(results):

        source = result.get(
            "source",
            "Unknown"
        )

        if (
            correct_rank is None
            and source == expected_source
        ):
            correct_rank = idx + 1

    # Recall@3
    recall_at_3 = (
        1.0
        if correct_rank is not None and correct_rank <= 3
        else 0.0
    )

    # MRR
    mrr = (
        1 / correct_rank
        if correct_rank is not None
        else 0.0
    )

    print(f"\nQuery: {query}")
    print(f"Expected: {expected_source}")
    print(f"Found at rank: {correct_rank}")
    print(f"Recall@3: {recall_at_3:.2f}")
    print(f"MRR: {mrr:.2f}")

    return recall_at_3, mrr


if __name__ == "__main__":

    evaluation_queries = [

        {
            "query": "What skills does Sam Taylor have?",
            "expected_source": "2.png"
        },

        {
            "query": "What database does Sam Taylor use?",
            "expected_source": "2.png"
        },

        {
            "query": "What is Sam Taylor's role?",
            "expected_source": "2.png"
        },

        {
            "query": "What skills does Arjun Kumar have?",
            "expected_source": "arjun.txt"
        },

        {
            "query": "What cloud platform does Arjun Kumar use?",
            "expected_source": "arjun.txt"
        }
    ]

    total_recall = 0
    total_mrr = 0

    print("\n===== MULTI-QUERY RAG EVALUATION =====")

    for item in evaluation_queries:

        recall, mrr = evaluate_retrieval(
            item["query"],
            item["expected_source"]
        )

        total_recall += recall
        total_mrr += mrr

    query_count = len(evaluation_queries)

    average_recall = (
        total_recall / query_count
    )

    average_mrr = (
        total_mrr / query_count
    )

    print("\n===== FINAL RESULTS =====")

    print(
        f"Average Recall@3: "
        f"{average_recall:.2f}"
    )

    print(
        f"Average MRR: "
        f"{average_mrr:.2f}"
    )