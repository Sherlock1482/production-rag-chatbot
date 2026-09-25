from utils.schedule_details import get_missing_schedule_details


test_queries = [
    "Schedule Rajuu Sharma's interview",
    "Schedule Rajuu Sharma on October 2",
    "Schedule Rajuu Sharma at 3 PM",
    "Schedule Rajuu Sharma on October 2 at 3 PM",
    "Schedule Rajuu Sharma on October 2 at 3 PM for 30 minutes",
]


for query in test_queries:
    result = get_missing_schedule_details(query)

    print(f"\nQuery: {query}")
    print(f"Details: {result['details']}")
    print(f"Missing: {result['missing']}")
    print(f"Complete: {result['complete']}")
    print("-" * 60)