from utils.intent_detector import detect_intent


test_queries = [
    "Schedule Rajuu Sharma's interview",
    "Book an interview for Rajuu Sharma",
    "Set up an interview with Rajuu Sharma",
    "When is Rajuu Sharma's interview?",
    "Where is Rajuu Sharma's interview?",
    "What is Rajuu Sharma's interview status?",
    "What skills does Rajuu Sharma have?",
    "Does Rajuu Sharma know Python?",
]


for query in test_queries:
    intent = detect_intent(query)

    print(f"Query:  {query}")
    print(f"Intent: {intent}")
    print("-" * 60)