import pytest
import yaml

import config
from jobhunt import db, ranking, tracker

GOOD = ("AI Engineer in Kochi. Python, RAG, LangChain, LLM. "
        "Mentorship and training for freshers. 5-7 LPA.")
BAD = "Sales Executive in Delhi. Cold calling, targets. 2.5 LPA."


def add(role, description, company="Acme", location=""):
    return tracker.add_job(f"https://example.com/{role}/{company}", company=company,
                           role=role, location=location, description=description)["job_id"]


def test_good_job_ranks_above_bad_job_and_scores_are_saved():
    good = add("AI Engineer", GOOD, location="Kochi")
    bad = add("Sales Executive", BAD, location="Delhi")
    ranked = ranking.rank_jobs()
    assert [r["job_id"] for r in ranked] == [good, bad]
    assert ranked[0]["rank"] == 1
    assert 0 <= ranked[1]["score"] < ranked[0]["score"] <= 100
    assert db.get_job(good)["rank_score"] == ranked[0]["score"]
    # rank_jobs also saves the skill match %, so tables can show it
    assert ranked[0]["match_percent"] == db.get_job(good)["match_percent"] == 100.0


def test_breakdown_explains_each_factor():
    add("AI Engineer", GOOD, location="Bengaluru")
    breakdown = ranking.rank_jobs()[0]["breakdown"]
    assert set(breakdown) == set(ranking.FACTORS)
    assert breakdown["location"]["why"] == "in Bangalore"  # alias Bengaluru -> Bangalore
    assert breakdown["salary"]["score"] == 1.0  # 6 LPA = target
    assert breakdown["learning"]["why"].startswith("mentions")


def test_ranking_does_not_reset_followup_timer():
    job_id = add("AI Engineer", GOOD)
    db.update_job(job_id, {"date_updated": "2026-01-01"}, touch=False)
    ranking.rank_jobs()
    assert db.get_job(job_id)["date_updated"] == "2026-01-01"


def test_only_saved_jobs_by_default():
    job_id = add("AI Engineer", GOOD)
    tracker.update_status(job_id, "applied")
    assert ranking.rank_jobs() == []
    assert len(ranking.rank_jobs("applied")) == 1


@pytest.mark.parametrize("text, expected", [
    ("Salary 5-7 LPA", 6.0),
    ("CTC: 4 LPA", 4.0),
    ("3 to 4.5 lakhs per annum", 3.75),
    ("Competitive salary", None),
])
def test_parse_salary(text, expected):
    assert ranking.parse_salary_lpa(text) == expected


def test_my_own_rubric_file_is_used(isolated):
    rubric = {"weights": {"company": 100}, "dream_companies": ["Acme"]}
    (isolated / "rubric.yaml").write_text(yaml.safe_dump(rubric), encoding="utf-8")
    add("Anything", "text", company="Acme Corp")
    assert ranking.rank_jobs()[0]["score"] == 100.0


def test_bad_rubric_gives_clear_error():
    with pytest.raises(ValueError, match="unknown factor"):
        ranking.check_weights({"weights": {"vibes": 10}})
    with pytest.raises(ValueError, match="all weights are 0"):
        ranking.check_weights({"weights": {"salary": 0}})
