"""match_resume: how well does my resume fit one saved job?"""

from jobhunt import data_files, db, skills, tracker


def job_text(job: dict) -> str:
    """The text we search for skills: the role title plus the description."""
    return f"{job['role']}\n{job['description']}"


def rank_bullets(bullets: list[dict], wanted_skills: list[str]) -> list[dict]:
    """My bullets that prove skills the job wants, best first.

    Score = how many wanted skills the bullet proves. Ties keep file order.
    """
    wanted = set(wanted_skills)
    scored = []
    for position, bullet in enumerate(bullets):
        proves = sorted({skills.canonical(s) for s in bullet.get("skills", [])} & wanted)
        if proves:
            scored.append((-len(proves), position, {**bullet, "proves": proves}))
    return [item for _, _, item in sorted(scored, key=lambda t: (t[0], t[1]))]


def match_resume(job_id: int) -> dict:
    job = tracker.require_job(job_id)
    resume = data_files.load_resume()
    result = skills.match_skills(job_text(job), resume.get("skills", []))

    if result["match_percent"] is None:
        return {"job_id": job_id, "match_percent": None,
                "message": "No skills found in this job. Save the job description "
                           "first (add_job with description=...)."}

    db.update_job(job_id, {"match_percent": result["match_percent"]}, touch=False)
    best = rank_bullets(data_files.load_bullets(), result["matched_skills"])
    answer = {
        "job_id": job_id, "company": job["company"], "role": job["role"], **result,
        "supporting_bullets": [{"id": b["id"], "text": b["text"], "proves": b["proves"]}
                               for b in best[:5]],
    }
    warning = data_files.example_warning()
    if warning:
        answer["warning"] = warning
    return answer
