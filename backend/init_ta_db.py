import sqlite3


def init_ta_db():
    conn = sqlite3.connect("ta_interviews.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            candidate_name TEXT,
            role TEXT,
            interview_stage TEXT,
            scheduled_date TEXT,
            interviewer TEXT
        )
    """)

    sample_data = [
        (
            "Priya Patel",
            "Backend Engineer",
            "Final Round",
            "2026-04-10",
            "Alex Smith"
        ),
        (
            "Arjun Kumar",
            "DevOps Engineer",
            "Technical Screening",
            "2027-04-12",
            "Sarah Jenkins"
        ),
        (
            "Jane Doe",
            "Full Stack Developer",
            "HR Round",
            "2026-04-15",
            "Mark Taylor"
        )
    ]

    cursor.executemany(
        "INSERT INTO interviews VALUES (?, ?, ?, ?, ?)",
        sample_data
    )

    conn.commit()
    conn.close()

    print("TA database initialized successfully.")


if __name__ == "__main__":
    init_ta_db()