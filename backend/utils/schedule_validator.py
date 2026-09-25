from datetime import datetime, timedelta


MIN_DURATION_MINUTES = 15
MAX_DURATION_MINUTES = 240


def validate_schedule(
    start_datetime: datetime | None,
    end_datetime: datetime | None,
    duration_minutes: int | None,
    reference_datetime: datetime | None = None,
):
    """
    Validate normalized interview scheduling details.
    """

    if reference_datetime is None:
        reference_datetime = datetime.now()

    errors = []

    # -------------------------
    # Required values
    # -------------------------

    if start_datetime is None:
        errors.append("Start date and time are required.")

    if end_datetime is None:
        errors.append("End date and time are required.")

    if duration_minutes is None:
        errors.append("Interview duration is required.")

    if errors:
        return {
            "valid": False,
            "errors": errors,
        }

    # -------------------------
    # Duration validation
    # -------------------------

    if duration_minutes < MIN_DURATION_MINUTES:
        errors.append(
            f"Interview duration must be at least "
            f"{MIN_DURATION_MINUTES} minutes."
        )

    if duration_minutes > MAX_DURATION_MINUTES:
        errors.append(
            f"Interview duration cannot exceed "
            f"{MAX_DURATION_MINUTES} minutes."
        )

    # -------------------------
    # Date/time validation
    # -------------------------

    if start_datetime <= reference_datetime:
        errors.append("Interview date and time must be in the future.")

    # Make sure end is after start.
    if end_datetime <= start_datetime:
        errors.append("Interview end time must be after start time.")

    # Verify duration matches start/end.
    actual_duration = (
        end_datetime - start_datetime
    ).total_seconds() / 60

    if actual_duration != duration_minutes:
        errors.append(
            "Interview duration does not match the start and end time."
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }