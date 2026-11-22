"""followups: which jobs are waiting too long for news?

Rule: status is 'applied' or 'interview', and nothing changed for N days
(config.FOLLOWUP_AFTER_DAYS). After I follow up, add_note() resets the timer.
"""

from datetime import date

import config
from jobhunt import db

SUGGESTIONS = {
    "applied": "Send a short, polite follow-up to HR/the recruiter, or check the job portal.",
    "interview": "Send a thank-you note and ask kindly about the next steps.",
}


def followups(days: int | None = None, today: date | None = None) -> list[dict]:
    days = config.FOLLOWUP_AFTER_DAYS if days is None else days
    if days < 0:
        raise ValueError("days must be 0 or more")
    today = today or date.today()

    due = []
    for job in db.list_jobs(list(SUGGESTIONS)):
        waiting = (today - date.fromisoformat(job["date_updated"])).days
        if waiting >= days:
            due.append({"job_id": job["id"], "company": job["company"],
                        "role": job["role"], "status": job["status"],
                        "days_waiting": waiting, "last_update": job["date_updated"],
                        "suggestion": SUGGESTIONS[job["status"]]})
    due.sort(key=lambda d: d["days_waiting"], reverse=True)  # most overdue first
    return due
