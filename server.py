"""The job-hunt MCP server.

Run it:  python server.py
It talks over stdio: it reads requests from stdin and writes answers to stdout.
So never use print() in this server, because it would mix junk into the answers.

This file is the 'waiter': each tool is a thin wrapper that calls the real
logic in the jobhunt/ package. The docstrings are what Claude reads.
"""

import json
from functools import wraps

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError

import config
from jobhunt import (cover_letter, data_files, db, matching, prompts, ranking, reminders,
                     resume, tracker)

mcp = MCPServer(
    config.SERVER_NAME,
    instructions=(
        f"Job search helper for a fresher looking for {', '.join(config.TARGET_ROLES)} "
        f"roles in {', '.join(config.TARGET_LOCATIONS)}. "
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
    Duplicates are not added twice: same link, or same company + role.
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


# ---------- Step 6: cover letter + follow-ups ----------

@mcp.tool()
@friendly_errors
def draft_cover_letter(job_id: int) -> dict:
    """Get the FACTS and RULES for writing a cover letter for one job.

    Returns the job, my profile, my best real bullets, matched skills and gaps.
    YOU (Claude) then write the letter using only these facts, and save it with
    save_cover_letter.
    """
    return cover_letter.draft_cover_letter(job_id)


@mcp.tool()
@friendly_errors
def save_cover_letter(job_id: int, letter_text: str,
                      learning_mentions: list[str] | None = None) -> dict:
    """Check a cover letter and save it as output/cover_letters/<Company>_<Role>.docx.

    letter_text: the full letter. Put a blank line between paragraphs.
    learning_mentions: skills the letter says I am LEARNING (not claiming), e.g. ["Docker"].
    Saving is refused if the letter claims skills or numbers not in my data.
    """
    return cover_letter.save_cover_letter(job_id, letter_text, learning_mentions)


@mcp.tool()
@friendly_errors
def followups(days: int | None = None) -> list[dict]:
    """Jobs (applied or interview) with no update for a while. Most overdue first.

    days: how long counts as 'a while' (default from config, 7 days).
    The HUMAN sends the follow-up. Then use add_note to log it, which resets the timer.
    """
    return reminders.followups(days)


# ---------- Step 7: skill gaps, resources, prompts ----------

@mcp.tool()
@friendly_errors
def skill_gap_report() -> dict:
    """Which skills do MANY of my active jobs ask for that I don't have yet?
    The top one is the best thing to learn next."""
    return matching.skill_gap_report()


# Resources = things Claude can READ, each with an address (URI).

@mcp.resource("resume://master", title="Master resume", mime_type="application/yaml")
def master_resume() -> str:
    """My master resume: profile, education, skills."""
    return data_files.resolve(config.MASTER_RESUME_PATH).read_text(encoding="utf-8")


@mcp.resource("resume://bullets", title="Master bullets", mime_type="application/yaml")
def master_bullets() -> str:
    """Every achievement bullet with its id and skill tags."""
    return data_files.resolve(config.MASTER_BULLETS_PATH).read_text(encoding="utf-8")


@mcp.resource("jobs://list", title="Job list", mime_type="application/json")
def job_list() -> str:
    """All saved jobs, short view."""
    return json.dumps(tracker.list_jobs(), indent=2)


@mcp.resource("jobs://{job_id}", title="One job", mime_type="application/json")
def job_detail(job_id: int) -> str:
    """Every detail of one job. A URI with {job_id} is a 'template': one address
    pattern for many jobs, e.g. jobs://3."""
    job = db.get_job(job_id)
    if job is None:
        raise ResourceNotFoundError(f"No job with id {job_id}")
    return json.dumps(job, indent=2)


# Prompts = ready-made recipes I pick from a menu (e.g. /mcp__job-hunt__weekly_job_review).

@mcp.prompt(title="Weekly job review")
def weekly_job_review() -> str:
    """Follow-ups, top 3 jobs to apply to, the skill to learn next, and counts."""
    return prompts.WEEKLY_JOB_REVIEW


@mcp.prompt(title="Prepare an application")
def prepare_application(job_id: str) -> str:
    """Match, tailored resume and cover letter for one job. I apply myself."""
    return prompts.prepare_application(job_id)


@mcp.prompt(title="Find jobs on Indeed")
def find_jobs(roles: str = "", cities: str = "") -> str:
    """Search Indeed (with the Indeed connector) for my roles and cities, save the
    good jobs with full descriptions, and rank them. Leave empty to use config.py."""
    return prompts.find_jobs(roles, cities)


# ---------- Step 9: job sources ----------

@mcp.tool()
@friendly_errors
def import_job_alerts(email_text: str, dry_run: bool = False) -> dict:
    """Save all jobs from a pasted LinkedIn / Naukri / Indeed job-alert email.

    email_text: the whole email text, including the job links.
    dry_run: True = only show what was found, save nothing.
    Reads only the pasted text: it never opens the links (no scraping).
    """
    return tracker.import_job_alerts(email_text, dry_run)


@mcp.tool()
@friendly_errors
def update_job_details(job_id: int, company: str | None = None, role: str | None = None,
                       location: str | None = None, description: str | None = None,
                       salary_lpa: float | None = None) -> dict:
    """Fill in or fix a saved job's details, e.g. paste the description of a job that
    came from an alert email. Only the fields you give are changed."""
    return tracker.update_job_details(job_id, company, role, location, description,
                                      salary_lpa)


if __name__ == "__main__":
    mcp.run()  # default transport is "stdio"
