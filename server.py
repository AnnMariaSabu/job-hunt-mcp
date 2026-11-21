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
from jobhunt import tracker

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


if __name__ == "__main__":
    mcp.run()  # default transport is "stdio"
