from utils.datetime_extractor import extract_datetime_details


test_queries = [
    "Schedule Rajuu Sharma's interview on October 2 at 3 PM",
    "Schedule Rajuu Sharma tomorrow at 10:30 AM",
    "Book Rajuu's interview on 2026-10-05 at 2 PM for 60 minutes",
    "Schedule an interview on 10/06/2026 at 4 PM IST",
    "Schedule Rajuu's interview today at 11 AM",
    "Schedule Rajuu's interview",
]


for query in test_queries:
    result = extract_datetime_details(query)

    print(f"\nQuery: {query}")
    print(f"Result: {result}")
    print("-" * 60)