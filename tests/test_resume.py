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
    # Experience first (always kept), then the best-matching project bullet.
    assert result["bullets_used"][:3] == ["intern-dashboard", "intern-sql", "rag-bot"]


def test_experience_is_always_kept_even_when_space_is_short(monkeypatch):
    monkeypatch.setattr(config, "MAX_BULLETS", 3)
    result = resume.tailor_resume(make_job())
    assert result["bullets_used"] == ["intern-dashboard", "intern-sql", "rag-bot"]


def test_section_order_and_project_links(isolated):
    (isolated / "master_resume.yaml").write_text(
        Path(config.DATA_DIR / "master_resume.example.yaml").read_text(encoding="utf-8")
        + "\nsection_order: [projects, experience]\n", encoding="utf-8")
    bullets = data_files.load_yaml(config.MASTER_BULLETS_PATH)
    bullets["bullets"][2]["link"] = "github.com/asha-example/rag-bot"
    import yaml
    (isolated / "master_bullets.yaml").write_text(yaml.safe_dump(bullets), encoding="utf-8")

    text = docx_text(resume.tailor_resume(make_job())["file"])
    assert text.index("Projects") < text.index("Experience")
    assert "github.com/asha-example/rag-bot" in text


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
