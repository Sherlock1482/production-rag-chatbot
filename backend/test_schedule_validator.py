from datetime import datetime, timedelta

from utils.schedule_validator import validate_schedule


reference_datetime = datetime(
    2026,
    9,
    25,
    10,
    0,
)


# ---------------------------------
# Valid schedule
# ---------------------------------

start = datetime(
    2026,
    10,
    2,
    15,
    0,
)

end = start + timedelta(minutes=60)

result = validate_schedule(
    start,
    end,
    60,
    reference_datetime,
)

print("\nVALID SCHEDULE")
print(result)


# ---------------------------------
# Past schedule
# ---------------------------------

start = datetime(
    2026,
    9,
    20,
    15,
    0,
)

end = start + timedelta(minutes=60)

result = validate_schedule(
    start,
    end,
    60,
    reference_datetime,
)

print("\nPAST SCHEDULE")
print(result)


# ---------------------------------
# Too short
# ---------------------------------

start = datetime(
    2026,
    10,
    2,
    15,
    0,
)

end = start + timedelta(minutes=5)

result = validate_schedule(
    start,
    end,
    5,
    reference_datetime,
)

print("\nTOO SHORT")
print(result)


# ---------------------------------
# Too long
# ---------------------------------

start = datetime(
    2026,
    10,
    2,
    15,
    0,
)

end = start + timedelta(minutes=300)

result = validate_schedule(
    start,
    end,
    300,
    reference_datetime,
)

print("\nTOO LONG")
print(result)