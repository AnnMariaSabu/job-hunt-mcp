"""The dashboard, tested without a browser (Streamlit's AppTest)."""

from streamlit.testing.v1 import AppTest

import config
from jobhunt import db, tracker

DASHBOARD = str(config.BASE_DIR / "dashboard.py")


def open_dashboard() -> AppTest:
    app = AppTest.from_file(DASHBOARD, default_timeout=30).run()
    assert not app.exception, app.exception
    return app


def test_empty_dashboard_loads():
    app = open_dashboard()
    assert app.title[0].value == "🎯 Job Hunt"
    assert [m.value for m in app.metric] == ["0", "0", "0", "0", "0"]


def test_counts_and_table_show_my_jobs():
    a = tracker.add_job("https://example.com/a", company="Acme", role="Data Analyst",
                        description="SQL and Excel")["job_id"]
    tracker.add_job("https://example.com/b", company="Beta", role="AI Engineer")
    tracker.update_status(a, "applied")
    app = open_dashboard()
    assert [m.value for m in app.metric] == ["1", "1", "0", "0", "0"]
    assert set(app.dataframe[0].value["company"]) == {"Acme", "Beta"}


def test_delete_needs_the_confirm_tick():
    job_id = tracker.add_job("https://example.com/x", company="Acme")["job_id"]
    app = open_dashboard()
    delete = app.button(key=f"delete_{job_id}")
    assert delete.disabled  # can't click before ticking "Yes, delete"
    app.checkbox(key=f"sure_{job_id}").check().run()
    app.button(key=f"delete_{job_id}").click().run()
    assert not app.exception
    assert db.get_job(job_id) is None


def test_add_job_form_saves_a_job():
    app = open_dashboard()
    app.text_area(key="new_text").input("https://www.naukri.com/job-listings-data-engineer-1")
    app.text_input(key="new_company").input("Beta")
    app.text_input(key="new_role").input("Data Engineer")
    app.button(key="save_job").click().run()
    assert not app.exception
    assert [j["company"] for j in tracker.list_jobs()] == ["Beta"]
    assert app.success[0].value == "Saved as job 1."
