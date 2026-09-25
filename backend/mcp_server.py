import re

from google_calendar import get_upcoming_events
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

    events = get_upcoming_events()

    results = []

    candidate_normalized = _normalize_text(candidate_name)

    for event in events:

        summary = event.get("summary", "")
        event_search_text = _event_search_text(event)

        print(
            f"MCP CHECK: candidate='{candidate_normalized}' "
            f"against event='{event_search_text}'"
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
            f"'{candidate_name}'"
        )

        return {
            "candidate": candidate_name,
            "found": False,
            "message": "No upcoming interview found."
        }

    print(
        f"MCP: Found {len(results)} interview(s) "
        f"for '{candidate_name}'"
    )

    return {
        "found": True,
        "results": results
    }


if __name__ == "__main__":
    mcp.run()