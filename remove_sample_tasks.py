import sqlite3

from database import DB_FILE

SAMPLES = [
    ("Complete UI/UX Assignment", "2026-08-30"),
    ("Submit Research Proposal", "2026-09-02"),
    ("Prepare Presentation Slides", "2026-09-05"),
]


def main():
    conn = sqlite3.connect(DB_FILE)
    rows = []
    for title, due in SAMPLES:
        rows += conn.execute(
            "SELECT t.task_id, u.email, t.title FROM tasks t "
            "JOIN users u ON u.user_id = t.user_id "
            "WHERE t.title = ? AND t.due_date = ? AND t.description = ''",
            (title, due)).fetchall()

    if not rows:
        print("No sample tasks found - nothing to remove.")
        return
    print(f"Found {len(rows)} sample task(s):")
    for _, email, title in rows:
        print(f"  {email:<30} {title}")
    if input("Delete them? (y/N): ").strip().lower() != "y":
        print("Nothing deleted.")
        return
    with conn:
        conn.executemany("DELETE FROM tasks WHERE task_id = ?",
                         [(r[0],) for r in rows])
    print("Done.")
    conn.close()


if __name__ == "__main__":
    main()
