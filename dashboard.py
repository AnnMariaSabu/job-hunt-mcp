"""A calm dashboard for my job search.

Run:  .\\venv\\Scripts\\streamlit run dashboard.py

This is the HUMAN's control panel. It uses the same jobhunt/ code as the MCP
server, and it is the ONLY place where a job can be deleted.
"""

from pathlib import Path

import streamlit as st

import config
from jobhunt import data_files, db, matching, ranking, reminders, resume, skills, tracker

st.set_page_config(page_title="Job Hunt", page_icon="🎯", layout="wide")


def run(action, success, rerun=True):
    """Do a change. Show a friendly message instead of crashing on a mistake.

    success: a message, or a function that makes one from the result.
    """
    try:
        result = action()
    except ValueError as error:
        st.error(str(error))
        return None
    st.session_state["flash"] = success(result) if callable(success) else success
    if rerun:
        st.rerun()  # draw the page again with the new data
    return result


# ---------- header ----------

st.title("🎯 Job Hunt")
st.caption("Calm and structured. This app never applies for you.")
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
warning = data_files.example_warning()
if warning:
    st.info(warning)

jobs = db.list_jobs()
for column, status in zip(st.columns(len(config.JOB_STATUSES)), config.JOB_STATUSES):
    column.metric(status.title(), sum(job["status"] == status for job in jobs))

tab_jobs, tab_add, tab_insights = st.tabs(["Jobs", "Add jobs", "Follow-ups & skill gaps"])


# ---------- tab 1: jobs ----------

def show_job(job: dict) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown(f"**{job['role']}** at **{job['company']}**  \n"
                    f"📍 {job['location'] or 'location unknown'} · {job['source']} · "
                    f"added {job['date_added']}")
        if job["link"]:
            st.markdown(f"[Open the job post]({job['link']})")
        result = skills.match_skills(matching.job_text(job),
                                     data_files.load_resume().get("skills", []))
        if result["match_percent"] is None:
            st.write("No skills found yet. Add the job description to see your match.")
        else:
            st.write(f"**Match: {result['match_percent']:g}%**")
            st.write("✅ " + (", ".join(result["matched_skills"]) or "none"))
            st.write("📚 To learn: " + (", ".join(result["skill_gaps"]) or "nothing!"))
        with st.expander("Description"):
            st.write(job["description"] or "No description saved yet.")
        if job["notes"]:
            with st.expander("Notes"):
                st.text(job["notes"])

    with right:
        key = job["id"]
        new_status = st.selectbox("Status", config.JOB_STATUSES, key=f"status_{key}",
                                  index=config.JOB_STATUSES.index(job["status"]))
        note = st.text_input("Note (optional)", key=f"note_{key}")
        if st.button("Save status / note", key=f"save_{key}"):
            def change():
                if new_status != job["status"]:
                    return tracker.update_status(key, new_status, note)
                if note.strip():
                    return tracker.add_note(key, note)
                raise ValueError("Nothing changed.")
            run(change, "Saved.")

        if st.button("Make tailored resume", key=f"resume_{key}"):
            made = run(lambda: resume.tailor_resume(key), "Resume ready.", rerun=False)
            if made:
                with open(made["file"], "rb") as file:
                    st.download_button("⬇️ Download resume", file.read(),
                                       file_name=Path(made["file"]).name,
                                       key=f"download_{key}")

        with st.expander("🗑️ Delete this job (human only)"):
            sure = st.checkbox("Yes, delete this job forever", key=f"sure_{key}")
            if st.button("Delete", key=f"delete_{key}", disabled=not sure, type="primary"):
                run(lambda: db.delete_job(key), f"Deleted job {key}.")


with tab_jobs:
    left, right = st.columns([3, 1])
    chosen = left.multiselect("Show", config.JOB_STATUSES, key="filter",
                              default=["saved", "applied", "interview"])
    if right.button("Re-rank saved jobs", key="rerank"):
        run(lambda: ranking.rank_jobs("saved"), lambda r: f"Ranked {len(r)} saved job(s).")

    shown = [tracker.summary(job) for job in jobs if job["status"] in chosen]
    shown.sort(key=lambda j: (j["rank_score"] is None, -(j["rank_score"] or 0)))
    if not shown:
        st.write("No jobs here yet. Add some in **Add jobs**, or ask Claude.")
    else:
        st.dataframe(
            shown, hide_index=True,
            column_order=["id", "company", "role", "location", "status",
                          "match_percent", "rank_score", "date_added", "link"],
            column_config={
                "link": st.column_config.LinkColumn("Link", display_text="open"),
                "match_percent": st.column_config.NumberColumn("Match %", format="%.0f"),
                "rank_score": st.column_config.NumberColumn("Rank score", format="%.1f"),
            },
        )

    if jobs:
        st.subheader("One job")
        labels = {f"#{j['id']} {j['company']} - {j['role']} ({j['status']})": j["id"]
                  for j in jobs}
        picked = st.selectbox("Pick a job", list(labels), key="pick")
        show_job(db.get_job(labels[picked]))


# ---------- tab 2: add jobs ----------

with tab_add:
    with st.form("add_job", clear_on_submit=True):
        st.subheader("Add one job")
        text = st.text_area("Job link, or the full job post text (best for matching)",
                            key="new_text")
        c1, c2, c3 = st.columns(3)
        company = c1.text_input("Company", key="new_company")
        role = c2.text_input("Role", key="new_role")
        location = c3.text_input("Location", key="new_location")
        salary = st.number_input("Salary in LPA (0 = unknown)", min_value=0.0, step=0.5)
        if st.form_submit_button("Save job", key="save_job"):
            run(lambda: tracker.add_job(text, company=company, role=role, location=location,
                                        salary_lpa=salary or None),
                lambda r: r.get("message") or f"Saved as job {r['job_id']}.")

    with st.form("alerts", clear_on_submit=True):
        st.subheader("Import a job-alert email")
        email = st.text_area("Paste the whole LinkedIn / Naukri / Indeed alert email",
                             key="alert_email")
        if st.form_submit_button("Import jobs", key="import_alerts"):
            run(lambda: tracker.import_job_alerts(email),
                lambda r: f"Added {len(r['added'])} job(s), "
                          f"skipped {len(r['duplicates'])} duplicate(s).")


# ---------- tab 3: follow-ups & skill gaps ----------

with tab_insights:
    st.subheader("Follow-ups due")
    due = reminders.followups()
    if not due:
        st.success("Nothing to follow up right now. 🌿")
    for item in due:
        st.warning(f"**{item['company']} – {item['role']}** ({item['status']}, "
                   f"{item['days_waiting']} days): {item['suggestion']}")

    st.subheader("Skill gaps across my active jobs")
    report = matching.skill_gap_report()
    if report["top_gaps"]:
        st.dataframe(report["top_gaps"], hide_index=True)
        st.caption(f"Checked {report['jobs_checked']} job(s) with a description. "
                   f"{report['tip']}")
    else:
        st.write("No gaps found yet (or no job descriptions saved).")
