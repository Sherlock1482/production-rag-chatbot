from utils.scheduling_request import analyze_scheduling_request


test_queries = [
    "Schedule an interview with Priya tomorrow at 8:30 PM",
]


for query in test_queries:
    result = analyze_scheduling_request(query)

    print(f"\nQuery: {query}")
    print(f"Result: {result}")
    print("-" * 60)