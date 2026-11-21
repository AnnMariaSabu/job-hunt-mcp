"""Storage: a small SQLite database with one table, `jobs`.

SQLite = a whole database inside ONE file (data/jobs.db). Nothing to install,
and Python has it built in (`import sqlite3`).
"""

import sqlite3
from contextlib import contextmanager
from datetime import date

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company       TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL DEFAULT '',
    link          TEXT NOT NULL DEFAULT '',
    source        TEXT NOT NULL DEFAULT 'other',
    location      TEXT NOT NULL DEFAULT '',
    salary_lpa    REAL,
    description   TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'saved',
    date_added    TEXT NOT NULL,
    date_updated  TEXT NOT NULL,
    date_applied  TEXT,
    match_percent REAL,
    rank_score    REAL,
    notes         TEXT NOT NULL DEFAULT ''
)
"""

# Columns that update_job() may change. `id` and `date_added` never change.
EDITABLE_COLUMNS = {
    "company", "role", "link", "source", "location", "salary_lpa", "description",
    "status", "date_updated", "date_applied", "match_percent", "rank_score", "notes",
}


@contextmanager
def connect():
    """Open the database, hand it to the caller, then save and close it."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row  # rows act like dicts: row["company"]
    try:
        conn.execute(SCHEMA)  # creates the table the first time only
        yield conn
        conn.commit()
    finally:
        conn.close()


def today() -> str:
    """Today's date as text, e.g. '2026-11-21'."""
    return date.today().isoformat()


def insert_job(company: str, role: str, link: str = "", source: str = "other",
               location: str = "", description: str = "",
               salary_lpa: float | None = None) -> int:
    """Add a new job with status 'saved'. Returns the new job id."""
    now = today()
    with connect() as conn:
        # The ? marks are filled in safely by sqlite3. Never paste values into
        # SQL text yourself: that allows "SQL injection".
        cursor = conn.execute(
            """INSERT INTO jobs (company, role, link, source, location, description,
                                 salary_lpa, status, date_added, date_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)""",
            (company, role, link, source, location, description, salary_lpa, now, now),
        )
        return cursor.lastrowid


def get_job(job_id: int) -> dict | None:
    """One job as a dict, or None if the id doesn't exist."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def find_by_link(link: str) -> dict | None:
    """The job with this exact link, or None. Used to stop duplicates."""
    if not link:
        return None
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE link = ?", (link,)).fetchone()
    return dict(row) if row else None


def list_jobs(statuses: list[str] | None = None) -> list[dict]:
    """All jobs (newest first), or only jobs whose status is in `statuses`."""
    with connect() as conn:
        if statuses:
            marks = ", ".join("?" for _ in statuses)
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE status IN ({marks}) ORDER BY id DESC", statuses
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def update_job(job_id: int, fields: dict, touch: bool = True) -> None:
    """Change some columns of one job.

    touch=True also sets date_updated to today. Scores use touch=False, because
    re-ranking is not real news about the job (it must not reset follow-ups).
    """
    fields = dict(fields)
    if touch:
        fields["date_updated"] = today()
    bad = set(fields) - EDITABLE_COLUMNS
    if bad:
        raise ValueError(f"Cannot edit column(s): {sorted(bad)}")
    if not fields:
        return
    # Column names come from EDITABLE_COLUMNS (our own list), so this is safe.
    sets = ", ".join(f"{col} = ?" for col in fields)
    with connect() as conn:
        conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", [*fields.values(), job_id])


def delete_job(job_id: int) -> bool:
    """Delete a job. HUMAN ONLY: used by the dashboard, never exposed as an AI tool."""
    with connect() as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cursor.rowcount > 0
