"""Job sources: cleaning links and reading job-alert emails (all FAKE emails)."""

import pytest

from jobhunt import db, sources, tracker

LINKEDIN_ALERT = """Your job alert for data analyst in Kochi
3 new jobs match your preferences.

Data Analyst
Acme Analytics
Kochi, Kerala, India
View job: https://www.linkedin.com/comm/jobs/view/4011111111/?trackingId=abc%3D&refId=xyz

AI Engineer
Example AI Labs
Bengaluru, Karnataka, India
Actively recruiting
View job: https://www.linkedin.com/comm/jobs/view/4022222222/?trackingId=def

See all jobs: https://www.linkedin.com/comm/jobs/search?keywords=data
Unsubscribe: https://www.linkedin.com/comm/psettings/email-unsubscribe?x=1
"""

NAUKRI_ALERT = """Jobs for you
Data Engineer
Beta Solutions
2-5 Yrs | Chennai
https://www.naukri.com/job-listings-data-engineer-beta-solutions-chennai-123456?src=jobalert
"""

INDEED_ALERT = """AI/ML Engineer
Gamma Tech - Kochi, Kerala
₹6,00,000 - ₹8,00,000 a year
https://in.indeed.com/rc/clk?jk=abc123def&from=ja
"""


@pytest.mark.parametrize("raw, clean", [
    ("https://www.linkedin.com/comm/jobs/view/4011111111/?trackingId=abc&refId=x",
     "https://www.linkedin.com/jobs/view/4011111111/"),
    ("https://www.linkedin.com/jobs/collections/recommended/?currentJobId=555",
     "https://www.linkedin.com/jobs/view/555/"),
    ("https://in.indeed.com/rc/clk?jk=abc123&from=ja", "https://in.indeed.com/viewjob?jk=abc123"),
    ("https://www.naukri.com/job-listings-x-123?src=jobalert&sid=9",
     "https://www.naukri.com/job-listings-x-123"),
    ("https://careers.example.com/jobs/42?utm_source=mail&lang=en#apply",
     "https://careers.example.com/jobs/42?lang=en"),
])
def test_normalize_link(raw, clean):
    assert sources.normalize_link(raw) == clean


def test_linkedin_alert_is_parsed_and_noise_skipped():
    jobs = sources.parse_job_alerts(LINKEDIN_ALERT)
    assert jobs == [
        {"role": "Data Analyst", "company": "Acme Analytics", "location": "Kochi, Kerala, India",
         "link": "https://www.linkedin.com/jobs/view/4011111111/", "source": "linkedin"},
        {"role": "AI Engineer", "company": "Example AI Labs",
         "location": "Bengaluru, Karnataka, India",
         "link": "https://www.linkedin.com/jobs/view/4022222222/", "source": "linkedin"},
    ]  # the "See all" and "Unsubscribe" links are not jobs


def test_naukri_and_indeed_alerts_drop_salary_and_experience_bits():
    naukri = sources.parse_job_alerts(NAUKRI_ALERT)[0]
    assert (naukri["role"], naukri["company"], naukri["location"]) == (
        "Data Engineer", "Beta Solutions", "Chennai")
    indeed = sources.parse_job_alerts(INDEED_ALERT)[0]
    assert (indeed["role"], indeed["company"], indeed["location"]) == (
        "AI/ML Engineer", "Gamma Tech", "Kochi, Kerala")


def test_import_saves_jobs_and_skips_duplicates():
    first = tracker.import_job_alerts(LINKEDIN_ALERT)
    assert len(first["added"]) == 2 and first["duplicates"] == []
    # Same jobs again, but with different tracking junk in the links:
    again = tracker.import_job_alerts(LINKEDIN_ALERT.replace("trackingId=abc", "trackingId=zzz"))
    assert again["added"] == [] and len(again["duplicates"]) == 2
    assert len(tracker.list_jobs()) == 2


def test_dry_run_saves_nothing():
    result = tracker.import_job_alerts(NAUKRI_ALERT, dry_run=True)
    assert result["found"] == 1
    assert tracker.list_jobs() == []


def test_email_without_job_links_gives_clear_error():
    with pytest.raises(ValueError, match="No job links found"):
        tracker.import_job_alerts("Hello! No jobs today.")


def test_pasting_the_same_job_with_tracking_junk_is_a_duplicate():
    tracker.add_job("https://www.linkedin.com/jobs/view/777/")
    again = tracker.add_job("https://www.linkedin.com/comm/jobs/view/777/?trackingId=q")
    assert again["result"] == "duplicate"


def test_update_job_details_fills_in_description():
    job_id = tracker.import_job_alerts(NAUKRI_ALERT)["added"][0]["job_id"]
    result = tracker.update_job_details(job_id, description="Spark, Airflow, SQL")
    assert result["changed"] == ["description"]
    assert db.get_job(job_id)["description"] == "Spark, Airflow, SQL"
    assert db.get_job(job_id)["company"] == "Beta Solutions"  # untouched
    with pytest.raises(ValueError, match="Nothing to change"):
        tracker.update_job_details(job_id)
