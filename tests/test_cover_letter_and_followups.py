from datetime import date
from pathlib import Path

import pytest
from docx import Document

import config
from jobhunt import cover_letter, db, reminders, tracker

JOB = ("AI Engineer at Example AI Labs, Kochi. Build RAG apps with Python and "
       "LangChain. Docker is a plus.")

HONEST = """Dear Hiring Team,

I am applying for the AI Engineer role at Example AI Labs in Kochi. I am a B.Tech
graduate who enjoys building practical AI tools in Python, and your work on RAG
applications is exactly the kind of work I want to grow in.

In my RAG Study Assistant project, I built a RAG chatbot that answers questions from
50+ pages of college notes, using LangChain and an LLM API. I also added a Streamlit
chat interface and tested the answers on 30 questions, reaching 80% correct answers.
This taught me how to check the quality of an AI system, not just build it.

I have not used Docker in a project yet, but I am learning it now so I can ship my
apps more easily. I would be glad to bring my Python, SQL and machine learning skills
to your team and keep learning from experienced engineers.

Thank you for your time and consideration.

Asha Example"""


@pytest.fixture
def job_id():
    return tracker.add_job("https://example.com/ai", company="Example AI Labs",
                           role="AI Engineer", description=JOB)["job_id"]


def test_draft_gives_facts_and_rules(job_id):
    pack = cover_letter.draft_cover_letter(job_id)
    assert pack["job"]["company"] == "Example AI Labs"
    assert pack["skill_gaps"] == ["docker"]
    assert pack["best_bullets"][0]["id"] == "rag-bot"
    assert any("Never invent" in rule for rule in pack["rules"])


def test_honest_letter_is_saved_as_docx(job_id):
    result = cover_letter.save_cover_letter(job_id, HONEST, learning_mentions=["Docker"])
    path = Path(result["file"])
    assert path == config.COVER_LETTERS_DIR / "Example-AI-Labs_AI-Engineer.docx"
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "Dear Hiring Team," in text and "Asha Example" in text


def test_learning_a_skill_must_be_declared(job_id):
    with pytest.raises(ValueError, match="not on my resume: \\['docker'\\]"):
        cover_letter.save_cover_letter(job_id, HONEST)  # Docker not declared


def test_invented_numbers_and_skills_are_blocked(job_id):
    fake = HONEST.replace("80% correct", "95% correct") + "\nI also deployed it on Kubernetes."
    with pytest.raises(ValueError) as error:
        cover_letter.save_cover_letter(job_id, fake, learning_mentions=["Docker"])
    assert "kubernetes" in str(error.value)
    assert "['95']" in str(error.value)


def test_too_short_letter_is_blocked(job_id):
    with pytest.raises(ValueError, match="too short"):
        cover_letter.save_cover_letter(job_id, "Dear Team, hire me. Thanks, Asha")


def test_followups_finds_old_applied_jobs_only():
    old = tracker.add_job("https://example.com/old", company="Old Co")["job_id"]
    new = tracker.add_job("https://example.com/new", company="New Co")["job_id"]
    saved = tracker.add_job("https://example.com/saved", company="Saved Co")["job_id"]
    tracker.update_status(old, "applied")
    tracker.update_status(new, "applied")
    db.update_job(old, {"date_updated": "2026-11-01"}, touch=False)
    db.update_job(saved, {"date_updated": "2026-11-01"}, touch=False)  # not applied

    due = reminders.followups(today=date(2026, 11, 21))
    assert [d["job_id"] for d in due] == [old]
    assert due[0]["days_waiting"] == 20
    assert "follow-up" in due[0]["suggestion"]
    assert new not in [d["job_id"] for d in due]


def test_add_note_resets_the_followup_timer():
    job_id = tracker.add_job("https://example.com/x")["job_id"]
    tracker.update_status(job_id, "applied")
    db.update_job(job_id, {"date_updated": "2026-01-01"}, touch=False)
    assert len(reminders.followups()) == 1
    tracker.add_note(job_id, "Emailed the recruiter")
    assert reminders.followups() == []
