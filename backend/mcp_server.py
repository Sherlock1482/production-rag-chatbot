import sqlite3
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("TA Interview Server")


def query_interview_schedule(candidate_name: str = ""):
    """
    Query the TA interview database.
    """


    db_path = Path(__file__).resolve().parent.parent / "ta_interviews.db"

    if not os.path.exists(db_path):
        return "Interview database not found."

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if candidate_name:
        cursor.execute(
            """
            SELECT *
            FROM interviews
            WHERE candidate_name LIKE ?
            """,
            (f"%{candidate_name}%",)
        )
    else:
        cursor.execute("SELECT * FROM interviews")

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"No interview records found for '{candidate_name}'."

    results = []

    for row in rows:
        results.append({
            "candidate": row[0],
            "role": row[1],
            "stage": row[2],
            "date": row[3],
            "interviewer": row[4]
        })

    return results


@mcp.tool()
def get_interview_schedule(candidate_name: str = ""):
    """
    Get interview schedule and current interview stage
    for one candidate or all candidates.
    """

    return query_interview_schedule(candidate_name)


if __name__ == "__main__":
    mcp.run()