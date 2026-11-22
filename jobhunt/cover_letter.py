"""Cover letters: Claude WRITES, this code gives the facts and CHECKS.

  1. draft_cover_letter(job_id) -> a "facts pack" + rules for Claude
  2. Claude writes the letter
  3. save_cover_letter(job_id, text) -> safety checks -> .docx

Giving the AI real facts to write from is called GROUNDING.
Checking its writing afterwards in code is a GUARDRAIL.
"""

import re
from datetime import date

from docx import Document
from docx.shared import Pt

import config
from jobhunt import data_files, matching, resume, safety, tracker

RULES = [
    "Use ONLY facts from 'me' and 'best_bullets'. Never invent skills, numbers, "
    "projects or experience.",
    "Do not claim any skill in 'skill_gaps'. You may say I am learning one, but then "
    "list it in learning_mentions when saving.",
    "200-300 words, 3-4 short paragraphs, warm, simple and specific to this company.",
    "Start with 'Dear Hiring Team,' (or the hiring manager's name if the post gives it) "
    "and end with my name.",
    "Then call save_cover_letter(job_id, letter_text, learning_mentions).",
]

MIN_WORDS, MAX_WORDS = 120, 400


def draft_cover_letter(job_id: int) -> dict:
    """Everything Claude needs to write an honest letter for this job."""
    job = tracker.require_job(job_id)
    res = data_files.load_resume()
    match = matching.match_resume(job_id)
    best = matching.rank_bullets(data_files.load_bullets(), match.get("matched_skills", []))
    pack = {
        "job_id": job_id,
        "job": {"company": job["company"], "role": job["role"],
                "location": job["location"], "description": job["description"][:3000]},
        "me": {"profile": res.get("profile", {}), "education": res.get("education", []),
               "skills": res.get("skills", [])},
        "matched_skills": match.get("matched_skills", []),
        "skill_gaps": match.get("skill_gaps", []),
        "best_bullets": [{"id": b["id"], "text": b["text"]} for b in best[:4]],
        "rules": RULES,
    }
    warning = data_files.example_warning()
    if warning:
        pack["warning"] = warning
    return pack


# ---------- checks ----------

NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)*")


def numbers_in(text: str) -> set[str]:
    """'200k+ rows, 0.86 F1, 1,200 users' -> {'200', '0.86', '1200'}"""
    return {n.replace(",", "") for n in NUMBER_PATTERN.findall(text)}


def check_letter(text: str, job: dict, learning_mentions: list[str]) -> list[str]:
    """Problems that block saving. Empty list = OK."""
    problems = []
    words = len(text.split())
    if words < MIN_WORDS:
        problems.append(f"too short ({words} words, need at least {MIN_WORDS})")
    if words > MAX_WORDS:
        problems.append(f"too long ({words} words, max {MAX_WORDS})")

    res = data_files.load_resume()
    allowed_skills = list(res.get("skills", [])) + list(learning_mentions)
    claimed = safety.unsupported_skills(text, allowed_skills)
    if claimed:
        problems.append(f"mentions skills not on my resume: {claimed}. Remove them, or if "
                        "the letter only says I am LEARNING them, list them in "
                        "learning_mentions")

    # Every number must come from my data or from the job post.
    sources = [str(res), str(data_files.load_bullets()), job["description"], str(date.today())]
    allowed_numbers = set().union(*(numbers_in(s) for s in sources))
    invented = sorted(numbers_in(text) - allowed_numbers)
    if invented:
        problems.append(f"numbers not found in my resume, bullets or the job post: "
                        f"{invented}. Don't invent numbers")
    return problems


# ---------- saving ----------

def save_cover_letter(job_id: int, letter_text: str,
                      learning_mentions: list[str] | None = None) -> dict:
    job = tracker.require_job(job_id)
    text = (letter_text or "").strip()
    learning_mentions = learning_mentions or []
    problems = check_letter(text, job, learning_mentions)
    if problems:
        raise ValueError("Cover letter NOT saved: " + "; ".join(problems))

    path = resume.output_path(config.COVER_LETTERS_DIR, job)
    write_docx(path, data_files.load_resume().get("profile", {}), text)
    answer = {"file": str(path), "words": len(text.split()),
              "learning_mentions": learning_mentions,
              "reminder": "Read it once before sending. YOU apply; this tool never does."}
    warning = data_files.example_warning()
    if warning:
        answer["warning"] = warning
    return answer


def write_docx(path, profile: dict, text: str) -> None:
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading(profile.get("name", ""), level=1)
    contact = [profile.get(k) for k in ("email", "phone", "location")]
    doc.add_paragraph(" | ".join(str(c) for c in contact if c))
    doc.add_paragraph(date.today().strftime("%d %B %Y"))
    for paragraph in re.split(r"\n\s*\n", text):  # blank line = new paragraph
        doc.add_paragraph(" ".join(paragraph.split()))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
