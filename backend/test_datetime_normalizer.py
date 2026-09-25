from datetime import datetime

from utils.datetime_normalizer import normalize_datetime


test_cases = [
    {
        "date": "2026-10-02",
        "time": "3pm",
        "duration_minutes": 60,
        
    },
    {
        "date": "10/05/2026",
        "time": "2pm",
        "duration_minutes": 30,
    },
    {
        "date": "2026-10-02",
        "time": "3pm",
        "duration_minutes": 60,
        "timezone": "IST",
    },
    {
        "date": "October 2",
        "time": "4pm",
        "duration_minutes": 45,
    },
]


reference_datetime = datetime(2026, 9, 25, 10, 0)


for details in test_cases:
    result = normalize_datetime(
        details,
        reference_datetime=reference_datetime,
    )

    print("\nInput:")
    print(details)

    print("\nNormalized:")
    print("Start:", result["start_datetime"])
    print("End:", result["end_datetime"])
    print("Duration:", result["duration_minutes"])
    print("Error:", result["error"])

    print("-" * 60)