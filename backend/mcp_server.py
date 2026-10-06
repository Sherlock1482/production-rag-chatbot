import re
import sys

from google_calendar import (
    get_upcoming_events,
    check_calendar_availability,
    find_available_slots,
    create_calendar_event,
)
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("TA Interview Server")


def _normalize_text(value: str) -> str:
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", value.casefold()).split()
    )


def _event_search_text(event: dict) -> str:
    values = [
        event.get("summary", ""),
        event.get("description", ""),
        event.get("location", ""),
        event.get("organizer", {}).get("displayName", ""),
    ]

    values.extend(
        attendee.get("displayName", "")
        for attendee in event.get("attendees", [])
    )

    return _normalize_text(" ".join(values))


@mcp.tool()
def get_interview_schedule(candidate_name: str = ""):
    """
    Get interview schedule from Google Calendar
    for one candidate or all upcoming interviews.
    """
    try:
        events = get_upcoming_events()
        results = []
        candidate_normalized = _normalize_text(candidate_name)

        for event in events:
            summary = event.get("summary", "")
            event_search_text = _event_search_text(event)

            print(
                f"MCP CHECK: candidate='{candidate_normalized}' "
                f"against event='{event_search_text}'",
                file=sys.stderr,
            )

            # -------------------------------------------------
            # Candidate filtering
            # -------------------------------------------------
            if candidate_normalized:
                if candidate_normalized not in event_search_text:
                    continue

            start = event["start"].get(
                "dateTime",
                event["start"].get("date")
            )

            results.append({
                "candidate": summary,
                "interview": summary,
                "start_time": start,
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "meeting_link": event.get("hangoutLink", "")
            })

        if not results:
            print(
                f"MCP: No interview found for "
                f"'{candidate_name}'",
                file=sys.stderr,
            )
            return {
                "candidate": candidate_name,
                "found": False,
                "message": "No upcoming interview found."
            }

        print(
            f"MCP: Found {len(results)} interview(s) "
            f"for '{candidate_name}'",
            file=sys.stderr,
        )

        return {
            "found": True,
            "results": results
        }
    except Exception as e:
        print(f"MCP error in get_interview_schedule: {e}", file=sys.stderr)
        return {
            "candidate": candidate_name,
            "found": False,
            "error": str(e),
            "message": f"Calendar lookup failed: {str(e)}"
        }


@mcp.tool()
def check_calendar_availability_tool(
    start_time: str,
    end_time: str,
):
    """
    Check whether a requested interview time is available
    on the recruiter's Google Calendar.
    """
    try:
        return check_calendar_availability(
            start_time,
            end_time,
        )
    except Exception as e:
        print(f"MCP error in check_calendar_availability_tool: {e}", file=sys.stderr)
        return {
            "available": False,
            "conflicts": [],
            "error": str(e),
        }


@mcp.tool()
def find_available_interview_slots(
    start_time: str,
    duration_minutes: int = 60,
    number_of_slots: int = 3,
):
    """
    Find available interview slots after the requested start time.
    """
    try:
        return find_available_slots(
            start_time=start_time,
            duration_minutes=duration_minutes,
            number_of_slots=number_of_slots,
        )
    except Exception as e:
        print(f"MCP error in find_available_interview_slots: {e}", file=sys.stderr)
        return {
            "requested_start": start_time,
            "duration_minutes": duration_minutes,
            "available_slots": [],
            "error": str(e),
        }


@mcp.tool()
def create_interview_event(
    candidate_name: str,
    candidate_email: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
):
    """Create an interview event in the recruiter's Google Calendar."""
    try:
        return create_calendar_event(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
        )
    except Exception as e:
        print(f"MCP error in create_interview_event: {e}", file=sys.stderr)
        return {
            "created": False,
            "error": str(e),
        }

if __name__ == "__main__":
    mcp.run()