"""Prompt texts: ready-made 'recipes' that I pick from a menu in Claude.

A prompt doesn't DO anything itself. It is a message that tells Claude which
tools to use, in which order, and what kind of answer I want.
"""

WEEKLY_JOB_REVIEW = """Run my calm weekly job review. Use the job-hunt tools:

1. followups(): list jobs where I should follow up. For each, give a 1-line suggestion.
2. rank_jobs(): pick the top 3 saved jobs to apply to this week, and say WHY
   (use the score breakdown, in simple words).
3. skill_gap_report(): name the ONE skill that would help the most, plus one small,
   concrete way to start learning it this week.
4. list_jobs(): give counts per status (saved / applied / interview / offer / rejected).

Keep it short, friendly and calm: a few bullet points per section.
Do NOT apply to any job and do NOT contact anyone. I do that myself."""


def prepare_application(job_id: str) -> str:
    return f"""Help me prepare my application for job {job_id}. Use the job-hunt tools:

1. get_job({job_id}) and match_resume({job_id}): tell me my match %, my strengths for
   this job, and my skill gaps, in simple words.
2. tailor_resume({job_id}): make the tailored resume. Tell me which bullets you used.
3. draft_cover_letter({job_id}): write a cover letter using ONLY those facts, then
   save it with save_cover_letter. If it is blocked, fix what the error says and retry.
4. Give me the file paths and a short checklist for applying.

Do NOT apply for me. I will review the files and apply myself, then mark it with
update_status({job_id}, "applied")."""
