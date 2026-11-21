# Project 4: Job Hunt MCP Server (Python)

## Goal
A calm, structured, fast way to manage my job search. It tracks jobs, shows status
and skill gaps, ranks jobs, makes a tailored resume + cover letter per job, and
reminds me to follow up. Inspired by github.com/dfrysinger/ai-job-hunt-toolkit,
built from scratch in Python for learning. It NEVER applies by itself.

## My job search
- Roles: AI Engineer, AI/ML Engineer, Data Analyst, Data Engineer
- Level: Fresher / 0-2 years (B.Tech graduate)
- Locations: Kochi, Bangalore, Chennai
- Sources: LinkedIn, Naukri, Indeed (job-alert emails + paste link), Indeed connector

## Tech
- Windows + PowerShell, Python 3.12, venv
- Official MCP Python SDK v2 (docs: https://py.sdk.modelcontextprotocol.io/)
- SQLite, PyYAML, python-docx, Streamlit, pytest. Settings in config.py
- No local LLM: Claude (the MCP client) does the writing.
  The server does fast code only: database, skill gaps, ranking, safety checks.

## Data (data/)
- master_resume.yaml: profile, education, skills
- master_bullets.yaml: every achievement, tagged by skill (written once)
- rubric.yaml: my priorities with weights (role fit, location, salary, learning, company)
- jobs.db: company, role, link, source, location, description, status, dates,
  match %, rank score, notes
- PRIVATE: real data files are git-ignored; commit *.example.yaml files instead

## Tools
- add_job(link_or_text, source) · update_status(job_id, status) · list_jobs(status?)
- match_resume(job_id) -> match %, matched skills, gaps
- rank_jobs() -> jobs sorted by my rubric score
- tailor_resume(job_id) -> output/resumes/<Company>_<Role>.docx
- draft_cover_letter(job_id) · followups() · import_job_alerts(email_text)
Resources: master resume, bullets, job list. Prompts: "weekly job review".

## Safety rules
- Never invent skills or experience: code checks every bullet/skill comes from data files
- No auto-apply, no scraping LinkedIn/Naukri
- Deleting jobs = human only (not an AI tool)

## Steps (ONE at a time)
0 setup + hello MCP server | 1 test with MCP Inspector | 2 tracker tools
3 master resume + bullets + match_resume | 4 rubric + rank_jobs
5 tailor_resume | 6 cover letter + followups | 7 resources + prompts
8 connect to Claude Code | 9 job sources (paste link, alert emails)
10 Streamlit dashboard + tests + evaluation | 11 README + notes