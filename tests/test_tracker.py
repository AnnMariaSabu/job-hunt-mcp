import pytest

from jobhunt import db, sources, tracker


def test_add_job_from_link_detects_source():
    result = tracker.add_job("https://www.linkedin.com/jobs/view/123/",
                             company="Acme", role="AI Engineer")
    assert result["result"] == "added"
    assert result["job"]["source"] == "linkedin"
    assert result["job"]["status"] == "saved"


def test_add_job_from_pasted_text_keeps_description_and_link():
    text = "Data Analyst at Beta. Skills: SQL, Excel. Apply: https://www.naukri.com/job-1"
    job_id = tracker.add_job(text)["job_id"]
    job = db.get_job(job_id)
    assert job["description"] == text
    assert job["link"] == "https://www.naukri.com/job-1"
    assert job["source"] == "naukri"


def test_duplicate_link_is_not_added_twice():
    first = tracker.add_job("https://in.indeed.com/viewjob?jk=abc")
    second = tracker.add_job("https://in.indeed.com/viewjob?jk=abc")
    assert second["result"] == "duplicate"
    assert second["job_id"] == first["job_id"]
    assert len(tracker.list_jobs()) == 1


def test_same_company_and_role_with_a_new_link_is_a_duplicate():
    # Indeed gives the SAME job a NEW short link on every search.
    first = tracker.add_job("https://to.indeed.com/aa9bng2wdvlq",
                            company="Rotox Technologies Pvt. Ltd.",
                            role="AI Engineer – Computer Vision")
    second = tracker.add_job("https://to.indeed.com/aaxfncp68hfh",
                             company="ROTOX TECHNOLOGIES PVT LTD",
                             role="ai engineer  computer vision")
    assert second["result"] == "duplicate"
    assert second["job_id"] == first["job_id"]
    assert len(tracker.list_jobs()) == 1


def test_same_company_with_a_different_role_is_added():
    tracker.add_job("https://to.indeed.com/a1", company="Acme", role="AI Engineer")
    second = tracker.add_job("https://to.indeed.com/a2", company="Acme", role="Data Analyst")
    assert second["result"] == "added"


def test_jobs_with_unknown_company_and_role_are_not_merged():
    # Alert emails often have no company or role. Different links = different jobs.
    tracker.add_job("https://example.com/job-1")
    second = tracker.add_job("https://example.com/job-2")
    assert second["result"] == "added"


def test_empty_input_is_rejected():
    with pytest.raises(ValueError, match="job link"):
        tracker.add_job("   ")


def test_update_status_sets_date_applied_and_note():
    job_id = tracker.add_job("https://example.com/job")["job_id"]
    result = tracker.update_status(job_id, "applied", note="Applied on site")
    assert result["old_status"] == "saved" and result["new_status"] == "applied"
    job = db.get_job(job_id)
    assert job["date_applied"] == db.today()
    assert "Applied on site" in job["notes"]


def test_bad_status_and_bad_id_give_clear_errors():
    job_id = tracker.add_job("https://example.com/job")["job_id"]
    with pytest.raises(ValueError, match="Unknown status"):
        tracker.update_status(job_id, "hired")
    with pytest.raises(ValueError, match="No job with id 999"):
        tracker.update_status(999, "applied")


def test_list_jobs_filters_by_status():
    a = tracker.add_job("https://example.com/a")["job_id"]
    tracker.add_job("https://example.com/b")
    tracker.update_status(a, "applied")
    assert [j["id"] for j in tracker.list_jobs("applied")] == [a]
    assert len(tracker.list_jobs()) == 2


def test_detect_source():
    assert sources.detect_source("https://www.naukri.com/x") == "naukri"
    assert sources.detect_source("https://indeed.co.in/x") == "indeed"
    assert sources.detect_source("https://notlinkedin.com/x") == "other"
    assert sources.detect_source("") == "other"
