"""Safety checks: documents may only say what my data files say.

Rule from PLAN.md: never invent skills or experience.
These checks run in CODE (not in the AI's head), so they can't be forgotten.
"""

from jobhunt import skills


def check_resume_content(chosen_skills: list[str], chosen_bullets: list[dict],
                         resume: dict, all_bullets: list[dict]) -> list[str]:
    """Problems with a resume we are about to write. Empty list = safe.

    - every skill must be written exactly as in master_resume.yaml
    - every bullet must be word-for-word the same as in master_bullets.yaml
    """
    problems = []
    allowed_skills = set(resume.get("skills", []))
    for skill in chosen_skills:
        if skill not in allowed_skills:
            problems.append(f"skill '{skill}' is not in master_resume.yaml")

    allowed_text = {b["id"]: b["text"] for b in all_bullets}
    for bullet in chosen_bullets:
        if bullet.get("id") not in allowed_text:
            problems.append(f"bullet '{bullet.get('id')}' is not in master_bullets.yaml")
        elif bullet.get("text") != allowed_text[bullet["id"]]:
            problems.append(f"bullet '{bullet['id']}' was changed; it must match "
                            "master_bullets.yaml word for word")
    return problems


def unsupported_skills(text: str, resume_skills: list[str]) -> list[str]:
    """Known skills mentioned in some writing (e.g. a cover letter) that are NOT
    on my resume. Example: the letter says 'Docker' but my resume doesn't."""
    mine = {skills.canonical(s) for s in resume_skills}
    return sorted(set(skills.extract_skills(text)) - mine)
