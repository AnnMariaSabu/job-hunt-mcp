"""Job tracker rules: check the input, then ask db.py to store it.

Mistakes by the caller raise ValueError with a clear message.
server.py turns that message into something Claude can read and fix.
"""

import config
from jobhunt import db, sources

# The short view of a job (no long description), used in lists.
SUMMARY_FIELDS = ("id", "company", "role", "location", "source", "status",
                  "match_percent", "rank_score", "date_added", "date_updated", "link")


def summary(job: dict) -> dict:
    return {key: job[key] for key in SUMMARY_FIELDS}


def require_job(job_id: int) -> dict:
    """Get a job or raise a helpful error."""
    job = db.get_job(job_id)
    if job is None:
        raise ValueError(f"No job with id {job_id}. Use list_jobs to see the ids.")
    return job


def add_job(link_or_text: str, source: str = "", company: str = "", role: str = "",
            location: str = "", description: str = "",
            salary_lpa: float | None = None) -> dict:
    """Save a job from a link OR from pasted job text. Skips duplicate links."""
    text = (link_or_text or "").strip()
    if not text:
        raise ValueError("Give a job link or paste the job description text.")

    if sources.is_link(text):
        link = text
    else:
        # Pasted text: keep it as the description, and grab a link from it if any.
        found = sources.find_links(text)
        link = found[0] if found else ""
        description = description or text

    source = (source or sources.detect_source(link)).lower()
    if source not in config.JOB_SOURCES:
        raise ValueError(f"Unknown source '{source}'. Use one of: {config.JOB_SOURCES}")

    existing = db.find_by_link(link)
    if existing:
        return {"result": "duplicate", "job_id": existing["id"],
                "message": f"Already saved as job {existing['id']}. Nothing added.",
                "job": summary(existing)}

    job_id = db.insert_job(
        company=company.strip() or "Unknown company",
        role=role.strip() or "Unknown role",
        link=link, source=source, location=location.strip(),
        description=description.strip(), salary_lpa=salary_lpa,
    )
    job = db.get_job(job_id)
    result = {"result": "added", "job_id": job_id, "job": summary(job)}
    if not job["description"]:
        result["tip"] = ("No description saved. Matching and ranking work much "
                         "better with the job description text.")
    return result


def update_status(job_id: int, status: str, note: str = "") -> dict:
    """Move a job to a new status (saved/applied/interview/offer/rejected)."""
    status = status.lower().strip()
    if status not in config.JOB_STATUSES:
        raise ValueError(f"Unknown status '{status}'. Use one of: {config.JOB_STATUSES}")
    job = require_job(job_id)

    fields = {"status": status}
    if status == "applied" and not job["date_applied"]:
        fields["date_applied"] = db.today()
    if note.strip():
        fields["notes"] = _append_note(job["notes"], note)
    db.update_job(job_id, fields)
    return {"job_id": job_id, "company": job["company"], "role": job["role"],
            "old_status": job["status"], "new_status": status}


def add_note(job_id: int, note: str) -> dict:
    """Add a dated note, e.g. 'Emailed the recruiter'. Also resets the follow-up timer."""
    if not note.strip():
        raise ValueError("The note is empty.")
    job = require_job(job_id)
    notes = _append_note(job["notes"], note)
    db.update_job(job_id, {"notes": notes})
    return {"job_id": job_id, "notes": notes}


def list_jobs(status: str | None = None) -> list[dict]:
    """Short view of all jobs, or only jobs with one status."""
    if status:
        status = status.lower().strip()
        if status not in config.JOB_STATUSES:
            raise ValueError(f"Unknown status '{status}'. Use one of: {config.JOB_STATUSES}")
        jobs = db.list_jobs([status])
    else:
        jobs = db.list_jobs()
    return [summary(j) for j in jobs]


def _append_note(old_notes: str, note: str) -> str:
    line = f"{db.today()}: {note.strip()}"
    return f"{old_notes}\n{line}".strip()
