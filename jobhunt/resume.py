"""tailor_resume: build a one-page .docx resume for ONE job.

Tailoring = CHOOSING and ORDERING, never rewriting:
  1. pick the bullets that prove the job's skills (or the ones Claude chose)
  2. put matched skills first
  3. skill gaps are NOT added (I don't have them!)
  4. safety check, then save output/resumes/<Company>_<Role>.docx
"""

import re
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt

import config
from jobhunt import data_files, matching, safety, skills, tracker


def safe_name(text: str) -> str:
    """Make text safe for a file name: 'Acme AI / Labs' -> 'Acme-AI-Labs'."""
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "-".join(words)[:40] or "Unknown"


def output_path(folder: Path, job: dict) -> Path:
    return folder / f"{safe_name(job['company'])}_{safe_name(job['role'])}.docx"


def choose_bullets(all_bullets: list[dict], wanted_skills: list[str],
                   bullet_ids: list[str] | None) -> list[dict]:
    """The bullets to use: Claude's choice (checked), else the best matches."""
    by_id = {b["id"]: b for b in all_bullets}
    if bullet_ids:
        unknown = [i for i in bullet_ids if i not in by_id]
        if unknown:
            raise ValueError(f"Unknown bullet id(s) {unknown}. "
                             f"Valid ids: {sorted(by_id)}")
        chosen_ids = list(dict.fromkeys(bullet_ids))  # remove repeats, keep order
        if len(chosen_ids) > config.MAX_BULLETS:
            raise ValueError(f"Too many bullets ({len(chosen_ids)}). "
                             f"Max is {config.MAX_BULLETS} (config.MAX_BULLETS).")
        return [by_id[i] for i in chosen_ids]

    # Experience is ALWAYS kept: real work matters to recruiters even when it
    # doesn't match this job's skills (dropping it would hide my internships).
    must = [b["id"] for b in all_bullets if b.get("section") == "experience"]
    # Projects fill the rest: best matches first, then the others (file order).
    best = [b["id"] for b in matching.rank_bullets(all_bullets, wanted_skills)
            if b["id"] not in must]
    rest = [b["id"] for b in all_bullets if b["id"] not in must and b["id"] not in best]
    room = max(config.MAX_BULLETS - len(must), 0)
    return [by_id[i] for i in must + (best + rest)[:room]]


def order_skills(resume_skills: list[str], matched: list[str]) -> list[str]:
    """My skills, matched ones first. Spelled exactly as in my resume."""
    first = [s for s in resume_skills if skills.canonical(s) in matched]
    rest = [s for s in resume_skills if s not in first]
    return first + rest


def tailor_resume(job_id: int, bullet_ids: list[str] | None = None) -> dict:
    job = tracker.require_job(job_id)
    resume = data_files.load_resume()
    all_bullets = data_files.load_bullets()  # already safety-checked on load
    match = matching.match_resume(job_id)
    matched = match.get("matched_skills", [])

    chosen_skills = order_skills(resume.get("skills", []), matched)
    chosen_bullets = choose_bullets(all_bullets, matched, bullet_ids)

    problems = safety.check_resume_content(chosen_skills, chosen_bullets, resume, all_bullets)
    if problems:
        raise ValueError("Safety check failed, resume NOT written: " + "; ".join(problems))

    path = output_path(config.RESUMES_DIR, job)
    write_docx(path, resume, chosen_skills, chosen_bullets)

    answer = {
        "file": str(path),
        "bullets_used": [b["id"] for b in chosen_bullets],
        "skills_order": chosen_skills,
        "matched_skills": matched,
        "skill_gaps_not_added": match.get("skill_gaps", []),
        "reminder": "Review the file before sending. YOU apply; this tool never does.",
    }
    warning = data_files.example_warning()
    if warning:
        answer["warning"] = warning
    return answer


# ---------- the Word file ----------

def write_docx(path: Path, resume: dict, chosen_skills: list[str],
               chosen_bullets: list[dict]) -> None:
    profile = resume.get("profile", {})
    doc = Document()
    for section in doc.sections:  # small margins = fits on one page
        section.top_margin = section.bottom_margin = Inches(0.6)
        section.left_margin = section.right_margin = Inches(0.7)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    doc.add_heading(profile.get("name", ""), level=0)
    contact = [profile.get(k) for k in ("email", "phone", "location", "linkedin", "github")]
    if profile.get("headline"):
        doc.add_paragraph(profile["headline"])
    doc.add_paragraph(" | ".join(str(c) for c in contact if c))

    if profile.get("summary"):
        doc.add_heading("Summary", level=1)
        doc.add_paragraph(profile["summary"])

    doc.add_heading("Skills", level=1)
    doc.add_paragraph(", ".join(chosen_skills))

    # Section order comes from my resume file, e.g. [projects, experience].
    for section_name in resume.get("section_order", ["experience", "projects"]):
        bullets = [b for b in chosen_bullets if b.get("section") == section_name]
        if not bullets:
            continue
        doc.add_heading(section_name.title(), level=1)
        for heading in dict.fromkeys(b.get("heading", "") for b in bullets):
            group = [b for b in bullets if b.get("heading", "") == heading]
            doc.add_paragraph().add_run(heading).bold = True
            link = next((b["link"] for b in group if b.get("link")), None)
            if link:
                doc.add_paragraph(link)
            for bullet in group:
                doc.add_paragraph(bullet["text"], style="List Bullet")

    if resume.get("education"):
        doc.add_heading("Education", level=1)
        for edu in resume["education"]:
            line = " | ".join(str(edu[k]) for k in ("degree", "school", "years", "score")
                              if edu.get(k))
            doc.add_paragraph(line)

    if resume.get("certifications"):
        doc.add_heading("Certifications", level=1)
        for cert in resume["certifications"]:
            doc.add_paragraph(str(cert), style="List Bullet")

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
