from utils.scheduling_request import analyze_scheduling_request
from utils.context_manager import contextualize_query


test_cases = [
    {
        "description": "Standard explicit candidate query",
        "history": [],
        "query": "Schedule an interview with Priya tomorrow at 8:30 PM",
    },
    {
        "description": "Multi-turn context: user references above candidate after conflict",
        "history": [
            {
                "role": "user",
                "content": "can you schedule an interview for Aarav tomorrow at 7 PM for 2 hours?",
            },
            {
                "role": "assistant",
                "content": "The requested time is unavailable. Conflicting event(s): Interview - Aarav (2026-10-06T19:00:00Z).",
            },
        ],
        "query": "Can you schedule one more interview today itself with the above candidate today at 7pm for 2hrs?",
    },
]


for case in test_cases:
    desc = case["description"]
    query = case["query"]
    history = case["history"]

    contextualized = contextualize_query(query, history)
    result = analyze_scheduling_request(contextualized, chat_history=history)

    print(f"\nScenario: {desc}")
    print(f"Original Query: {query}")
    print(f"Contextualized: {contextualized}")
    print(f"Result: {result}")
    print("-" * 60)