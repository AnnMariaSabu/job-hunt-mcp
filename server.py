"""The job-hunt MCP server.

Run it:  python server.py
It talks over stdio: it reads requests from stdin and writes answers to stdout.
So never use print() in this server, because it would mix junk into the answers.

This file is the 'waiter': each tool is a thin wrapper that calls the real
logic in the jobhunt/ package. The docstrings are what Claude reads.
"""

from functools import wraps

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import config
from jobhunt import matching, ranking, resume, tracker

mcp = MCPServer(
    config.SERVER_NAME,
    instructions=(
        "Job search helper for a fresher looking for AI Engineer, AI/ML Engineer, "
        "Data Analyst and Data Engineer roles in Kochi, Bangalore and Chennai. "
        "It tracks jobs and prepares documents. It NEVER applies to jobs: the human "
        "always applies. Use list_jobs to find job ids."
    ),
)


def friendly_errors(func):
    """Show our ValueError messages to Claude (as ToolError).

    In SDK v2, any other error is hidden from Claude for safety, so without this
    Claude would only see 'Error executing tool' and could not fix its mistake.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as error:
            raise ToolError(str(error)) from error
    return wrapper


@mcp.tool()
def hello(name: str) -> str:
    """Say hello. A tiny tool to check the server works."""
    return f"Hello, {name}! The job-hunt MCP server is running."


# ---------- Step 2: tracker tools ----------

@mcp.tool()
@friendly_errors
def add_job(link_or_text: str, source: config.JobSource | None = None,
            company: str = "", role: str = "", location: str = "",
            description: str = "", salary_lpa: float | None = None) -> dict:
    """Save a job to the tracker (status 'saved').

    link_or_text: the job link, OR the full pasted job post text.
    source: linkedin / naukri / indeed / other. Leave empty to detect it from the link.
    company, role, location: fill these in if you know them.
    description: the job description text (needed for good matching).
    salary_lpa: yearly salary in lakhs (e.g. 6.5), if the post says it.
    Duplicate links are not added twice.
    """
    return tracker.add_job(link_or_text, source or "", company, role, location,
                           description, salary_lpa)


@mcp.tool()
@friendly_errors
def update_status(job_id: int, status: config.JobStatus, note: str = "") -> dict:
    """Move a job to a new status. Use after the HUMAN applied, got an interview, etc.

    status: saved, applied, interview, offer, or rejected.
    note: optional short note, e.g. 'Applied on company site'.
    """
    return tracker.update_status(job_id, status, note)


@mcp.tool()
@friendly_errors
def list_jobs(status: config.JobStatus | None = None) -> list[dict]:
    """List saved jobs (short view, newest first). Optionally only one status."""
    return tracker.list_jobs(status)


@mcp.tool()
@friendly_errors
def get_job(job_id: int) -> dict:
    """Get ALL details of one job, including the full description and notes."""
    return tracker.require_job(job_id)


@mcp.tool()
@friendly_errors
def add_note(job_id: int, note: str) -> dict:
    """Add a dated note to a job, e.g. 'Emailed the recruiter'. Resets the follow-up timer."""
    return tracker.add_note(job_id, note)


# ---------- Step 3: resume matching ----------

@mcp.tool()
@friendly_errors
def match_resume(job_id: int) -> dict:
    """Compare a saved job's skills with MY resume skills.

    Returns match_percent (0-100), matched_skills, skill_gaps (skills the job asks
    for that I don't have yet), and my existing bullets that prove the matched skills.
    Saves match_percent on the job.
    """
    return matching.match_resume(job_id)


# ---------- Step 4: ranking ----------

@mcp.tool()
@friendly_errors
def rank_jobs(status: config.JobStatus = "saved") -> list[dict]:
    """Rank jobs by MY priorities (rubric.yaml): role fit, location, salary,
    learning, company. Best first, score 0-100, with the reason for each factor.
    Saves rank_score on each job. Default: only jobs I haven't applied to yet.
    """
    return ranking.rank_jobs(status)


# ---------- Step 5: tailored resume ----------

@mcp.tool()
@friendly_errors
def tailor_resume(job_id: int, bullet_ids: list[str] | None = None) -> dict:
    """Make a one-page Word resume for one job: output/resumes/<Company>_<Role>.docx.

    It only CHOOSES and ORDERS my real bullets and skills. It never writes new
    ones, and skill gaps are never added. A safety check runs before saving.
    bullet_ids: optional, pick bullets yourself (ids from match_resume's
    supporting_bullets or the resume://bullets resource). Leave empty to auto-pick.
    """
    return resume.tailor_resume(job_id, bullet_ids)


if __name__ == "__main__":
    mcp.run()  # default transport is "stdio"
