from pathlib import Path

import pytest
from docx import Document

import config
from jobhunt import data_files, resume, safety, tracker

AI_JOB = "AI Engineer. Python, RAG, LangChain and LLM apps. Docker and Kubernetes a plus."


def make_job():
    return tracker.add_job("https://example.com/ai", company="Example AI Labs",
                           role="AI Engineer", description=AI_JOB)["job_id"]


def docx_text(path) -> str:
    return "\n".join(p.text for p in Document(path).paragraphs)


def test_tailor_resume_writes_docx_with_matched_skills_first():
    result = resume.tailor_resume(make_job())
    path = Path(result["file"])
    assert path == config.RESUMES_DIR / "Example-AI-Labs_AI-Engineer.docx"
    assert path.exists()

    text = docx_text(path)
    assert "Asha Example" in text
    assert result["skills_order"][:4] == ["Python", "LLM", "RAG", "LangChain"]
    assert result["bullets_used"][0] == "rag-bot"
    assert len(result["bullets_used"]) == config.MAX_BULLETS


def test_skill_gaps_are_never_added():
    result = resume.tailor_resume(make_job())
    assert result["skill_gaps_not_added"] == ["docker", "kubernetes"]
    text = docx_text(result["file"]).lower()
    assert "docker" not in text and "kubernetes" not in text


def test_claude_can_choose_bullets_but_only_real_ones():
    job_id = make_job()
    result = resume.tailor_resume(job_id, bullet_ids=["etl-pipeline", "rag-bot"])
    assert result["bullets_used"] == ["etl-pipeline", "rag-bot"]
    with pytest.raises(ValueError, match="Unknown bullet id"):
        resume.tailor_resume(job_id, bullet_ids=["made-up-bullet"])


def test_safety_check_catches_changed_bullet_and_invented_skill():
    res = data_files.load_resume()
    bullets = data_files.load_bullets()
    changed = {**bullets[0], "text": bullets[0]["text"] + " Led a team of 50."}
    problems = safety.check_resume_content(["Python", "Kubernetes"], [changed], res, bullets)
    assert "skill 'Kubernetes' is not in master_resume.yaml" in problems
    assert any("was changed" in p for p in problems)


def test_safe_file_names():
    assert resume.safe_name("Acme AI / Labs (India)") == "Acme-AI-Labs-India"
    assert resume.safe_name("???") == "Unknown"
