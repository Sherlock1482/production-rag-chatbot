import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


def create_calendar_event(
    candidate_name: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
):
    service = get_calendar_service()

    event = {
        "summary": f"Interview - {candidate_name}",
        "description": description,
        "location": location,
        "start": {
            "dateTime": start_time,
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "UTC",
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return {
        "created": True,
        "event_id": created_event.get("id"),
        "candidate": candidate_name,
        "start_time": created_event["start"].get("dateTime"),
        "end_time": created_event["end"].get("dateTime"),
        "meeting_link": created_event.get("hangoutLink", ""),
        "calendar_link": created_event.get("htmlLink", ""),
    }

def check_calendar_availability(start_time, end_time):
    """
    Check whether the primary Google Calendar has an event
    overlapping the requested time range.

    start_time and end_time should be ISO datetime strings
    containing timezone information.
    """

    service = get_calendar_service()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_time,
        timeMax=end_time,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])

    conflicts = []

    for event in events:
        event_start = event["start"].get(
            "dateTime",
            event["start"].get("date"),
        )

        event_end = event["end"].get(
            "dateTime",
            event["end"].get("date"),
        )

        conflicts.append(
            {
                "summary": event.get("summary", ""),
                "start": event_start,
                "end": event_end,
            }
        )

    return {
        "available": len(conflicts) == 0,
        "conflicts": conflicts,
    }

def find_available_slots(
    start_time,
    duration_minutes=60,
    number_of_slots=3,
    search_hours=4,
):
    """
    Find available interview slots after the requested start time.

    start_time should be a timezone-aware ISO datetime string.
    """

    from datetime import datetime, timedelta

    requested_start = datetime.fromisoformat(start_time)

    search_end = requested_start + timedelta(hours=search_hours)

    service = get_calendar_service()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_time,
        timeMax=search_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])

    conflicts = []

    for event in events:
        event_start = event["start"].get(
            "dateTime",
            event["start"].get("date"),
        )

        event_end = event["end"].get(
            "dateTime",
            event["end"].get("date"),
        )

        if not event_start or not event_end:
            continue

        conflicts.append(
            (
                datetime.fromisoformat(event_start),
                datetime.fromisoformat(event_end),
            )
        )

    available_slots = []

    candidate_start = requested_start

    while candidate_start + timedelta(minutes=duration_minutes) <= search_end:

        candidate_end = candidate_start + timedelta(
            minutes=duration_minutes
        )

        conflict_found = False

        for event_start, event_end in conflicts:

            if (
                candidate_start < event_end
                and candidate_end > event_start
            ):
                conflict_found = True
                break

        if not conflict_found:

            available_slots.append(
                {
                    "start": candidate_start.isoformat(),
                    "end": candidate_end.isoformat(),
                }
            )

            if len(available_slots) >= number_of_slots:
                break

        candidate_start += timedelta(minutes=30)

    return {
        "requested_start": start_time,
        "duration_minutes": duration_minutes,
        "available_slots": available_slots,
    }

def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build(
        "calendar",
        "v3",
        credentials=creds
    )


def get_upcoming_events():

    service = get_calendar_service()

    now = datetime.datetime.now(
        tz=datetime.timezone.utc
    ).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=20,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events_result.get("items", [])