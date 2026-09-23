from google_calendar import get_upcoming_events
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("TA Interview Server")


@mcp.tool()
def get_interview_schedule(candidate_name: str = ""):
    """
    Get interview schedule from Google Calendar
    for one candidate or all upcoming interviews.
    """

    events = get_upcoming_events()

    results = []

    for event in events:

        summary = event.get("summary", "")

        # If candidate name is provided,
        # only return matching events.
        if candidate_name:
            if candidate_name.lower() not in summary.lower():
                continue

        start = event["start"].get(
            "dateTime",
            event["start"].get("date")
        )

        results.append({
            "candidate": candidate_name if candidate_name else summary,
            "interview": summary,
            "start_time": start,
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "meeting_link": event.get("hangoutLink", "")
        })

    if not results:
        return {
            "candidate": candidate_name,
            "message": "No upcoming interview found."
        }

    return results


if __name__ == "__main__":
    mcp.run()