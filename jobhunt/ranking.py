"""rank_jobs: score every job with MY rubric, then sort best first.

Each factor gives a score from 0.0 to 1.0 AND a reason in words.
Final score = weighted average of the factors, times 100.

Example with weights role_fit 35, location 20, salary 15, learning 20, company 10:
  scores 0.8, 1.0, 1.0, 0.67, 0.5  ->  (28 + 20 + 15 + 13.3 + 5) / 100 = 81.3
"""

import re

import config
from jobhunt import data_files, db, matching, skills, tracker

FACTORS = ("role_fit", "location", "salary", "learning", "company")


# ---------- the five factors ----------

def role_fit(job: dict, rubric: dict, my_skills: list[str]) -> tuple[float, str]:
    """Half from the job TITLE, half from my SKILL match."""
    titles = list(config.TARGET_ROLES) + list(rubric.get("extra_role_titles", []))
    if any(skills.mentions(job["role"], t) for t in titles):
        title_score, title_why = 1.0, "title is a target role"
    elif any(skills.mentions(job["role"], w) for w in rubric.get("related_role_words", [])):
        title_score, title_why = 0.5, "title is related"
    else:
        title_score, title_why = 0.0, "title is not a target role"

    percent = skills.match_skills(matching.job_text(job), my_skills)["match_percent"]
    if percent is None:
        skill_score, skill_why = 0.5, "skills unknown (no description)"
    else:
        skill_score, skill_why = percent / 100, f"{percent:g}% skill match"
    return (title_score + skill_score) / 2, f"{title_why}; {skill_why}"


def location_fit(job: dict, rubric: dict) -> tuple[float, str]:
    text = job["location"] or job["description"]
    for city in config.TARGET_LOCATIONS:
        aliases = config.LOCATION_ALIASES.get(city.lower(), [city])
        if any(skills.mentions(text, a) for a in aliases):
            return 1.0, f"in {city}"
    if rubric.get("remote_ok", True) and skills.mentions(text, "remote"):
        return 0.8, "remote"
    if not text.strip():
        return 0.5, "location unknown"
    return 0.0, f"not in my cities ({job['location'] or 'see description'})"


# "5-7 LPA", "4 LPA", "6.5 lakhs per annum", "3 to 4.5 LPA"
SALARY_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:(?:-|to)\s*(\d+(?:\.\d+)?)\s*)?(?:lpa|l\.p\.a|lakhs?)",
    re.IGNORECASE,
)


def parse_salary_lpa(text: str) -> float | None:
    """Salary in lakhs per year from job text. A range gives its middle."""
    found = SALARY_PATTERN.search(text or "")
    if not found:
        return None
    low = float(found.group(1))
    high = float(found.group(2)) if found.group(2) else low
    return (low + high) / 2


def salary_fit(job: dict, rubric: dict) -> tuple[float, str]:
    lpa = job["salary_lpa"]
    if lpa is None:
        lpa = parse_salary_lpa(job["description"])
    if lpa is None:
        return 0.5, "salary unknown"
    settings = rubric.get("salary", {})
    low = float(settings.get("minimum_lpa", 3))
    target = float(settings.get("target_lpa", 6))
    score = (lpa - low) / (target - low) if target > low else 1.0
    score = max(0.0, min(1.0, score))  # keep it between 0 and 1
    return score, f"{lpa:g} LPA (target {target:g})"


def learning_fit(job: dict, rubric: dict) -> tuple[float, str]:
    words = [w for w in rubric.get("learning_keywords", [])
             if skills.mentions(job["description"], w)]
    if not words:
        return 0.0, "no learning signals found"
    return min(1.0, len(words) / 3), "mentions " + ", ".join(words)


def company_fit(job: dict, rubric: dict) -> tuple[float, str]:
    name = job["company"].lower()
    if any(c.lower() in name for c in rubric.get("dream_companies", []) if c):
        return 1.0, "dream company"
    if any(c.lower() in name for c in rubric.get("avoid_companies", []) if c):
        return 0.0, "on my avoid list"
    return 0.5, "neutral"


# ---------- putting it together ----------

def check_weights(rubric: dict) -> dict:
    """The rubric's weights, after checking they make sense."""
    weights = rubric.get("weights", {})
    unknown = set(weights) - set(FACTORS)
    if unknown:
        raise ValueError(f"rubric.yaml has unknown factor(s) {sorted(unknown)}. "
                         f"Use: {list(FACTORS)}")
    clean = {}
    for factor in FACTORS:
        value = weights.get(factor, 0)
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"rubric.yaml: weight for {factor} must be a number >= 0")
        clean[factor] = float(value)
    if sum(clean.values()) == 0:
        raise ValueError("rubric.yaml: all weights are 0, so nothing can be ranked")
    return clean


def score_job(job: dict, rubric: dict, my_skills: list[str]) -> dict:
    weights = check_weights(rubric)
    results = {
        "role_fit": role_fit(job, rubric, my_skills),
        "location": location_fit(job, rubric),
        "salary": salary_fit(job, rubric),
        "learning": learning_fit(job, rubric),
        "company": company_fit(job, rubric),
    }
    total = sum(weights[f] * results[f][0] for f in FACTORS) / sum(weights.values())
    breakdown = {f: {"score": round(results[f][0], 2), "weight": weights[f],
                     "why": results[f][1]} for f in FACTORS}
    return {"score": round(total * 100, 1), "breakdown": breakdown}


def rank_jobs(status: str = "saved") -> list[dict]:
    """Score all jobs with this status, save the scores, return best first."""
    tracker.list_jobs(status)  # just to check the status is valid
    rubric = data_files.load_rubric()
    my_skills = data_files.load_resume().get("skills", [])

    ranked = []
    for job in db.list_jobs([status]):
        result = score_job(job, rubric, my_skills)
        percent = skills.match_skills(matching.job_text(job), my_skills)["match_percent"]
        db.update_job(job["id"], {"rank_score": result["score"], "match_percent": percent},
                      touch=False)
        ranked.append({"job_id": job["id"], "company": job["company"],
                       "role": job["role"], "location": job["location"],
                       "match_percent": percent, **result})
    ranked.sort(key=lambda r: r["score"], reverse=True)
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position
    return ranked
