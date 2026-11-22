"""See the tools in action on FAKE data, without touching my real files.

Run:  .\\venv\\Scripts\\python.exe demo.py

It talks to the server through a real MCP client (in memory), the same way
Claude does, and prints what each tool returns.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from mcp import Client

import config

AI_JOB = """AI Engineer (Fresher) - Kochi, Infopark
Build RAG and LLM features in Python with LangChain and a vector database.
Nice to have: Docker, FastAPI. Mentorship and training provided. 5-7 LPA."""

ANALYST_JOB = """Data Analyst - Bengaluru
Analyse sales data using SQL, Excel and Power BI dashboards. Statistics a plus.
Salary: 4 LPA."""


ALERT_EMAIL = """Your job alert for data engineer
Data Engineer
Beta Solutions
2-5 Yrs | Chennai
https://www.naukri.com/job-listings-data-engineer-beta-solutions-chennai-123456?src=jobalert

AI Engineer
Example AI Labs
Kochi, Kerala, India
View job: https://www.linkedin.com/comm/jobs/view/1111/?trackingId=abc
Unsubscribe: https://www.linkedin.com/comm/psettings/email-unsubscribe"""

LETTER = """Dear Hiring Team,

I am applying for the AI Engineer role at Example AI Labs in Kochi. I am a B.Tech
graduate who enjoys building practical AI tools in Python, and your RAG and LLM work
is exactly what I want to grow in.

In my RAG Study Assistant project, I built a RAG chatbot that answers questions from
50+ pages of college notes, using LangChain and an LLM API. I also tested the answers
on 30 questions, reaching 80% correct answers. This taught me to check the quality
of an AI system, not just build it.

I have not used Docker in a project yet, but I am learning it now. I would be glad to
bring my Python, SQL and machine learning skills to your team, and to keep learning
from your mentorship and training.

Thank you for your time.

Asha Example"""


def use_temp_folder() -> Path:
    """Point the database and output at a new temp folder, and the private
    data files at missing paths so the *.example.yaml files are used."""
    tmp = Path(tempfile.mkdtemp(prefix="jobhunt-demo-"))
    config.DB_PATH = tmp / "jobs.db"
    config.OUTPUT_DIR = tmp / "output"
    config.RESUMES_DIR = tmp / "output" / "resumes"
    config.COVER_LETTERS_DIR = tmp / "output" / "cover_letters"
    config.MASTER_RESUME_PATH = tmp / "master_resume.yaml"
    config.MASTER_BULLETS_PATH = tmp / "master_bullets.yaml"
    config.RUBRIC_PATH = tmp / "rubric.yaml"
    return tmp


async def call(client: Client, name: str, args: dict | None = None):
    result = await client.call_tool(name, args or {})
    print(f"\n>>> {name}({json.dumps(args or {})[:120]})")
    if result.is_error:
        print("ERROR:", result.content[0].text)
        return None
    data = result_data(result)
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1200])
    return data


def result_data(result):
    """The tool's answer as Python data.

    Tools that return a typed value (str, list[dict]) send `structured_content`
    like {"result": ...}. Tools that return a plain dict send it as JSON text.
    """
    if result.structured_content is not None:
        data = result.structured_content
        return data.get("result", data)
    text = result.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def print_docx(path: str) -> None:
    """Show the text inside a Word file."""
    from docx import Document

    print(f"\n----- inside {Path(path).name} -----")
    for paragraph in Document(path).paragraphs:
        if paragraph.text.strip():
            bullet = "  - " if paragraph.style.name == "List Bullet" else ""
            print(bullet + paragraph.text)
    print("-" * 40)


async def main():
    tmp = use_temp_folder()
    print(f"Demo folder (fake data): {tmp}")
    from server import mcp

    async with Client(mcp) as client:
        # Step 2: tracker
        ai = await call(client, "add_job", {
            "link_or_text": "https://www.linkedin.com/jobs/view/1111/",
            "company": "Example AI Labs", "role": "AI Engineer", "location": "Kochi",
            "description": AI_JOB, "salary_lpa": 6})
        da = await call(client, "add_job", {
            "link_or_text": "https://www.naukri.com/job-listings-data-analyst-2222",
            "company": "Sample Retail", "role": "Data Analyst", "location": "Bengaluru",
            "description": ANALYST_JOB, "salary_lpa": 4})
        await call(client, "add_job", {"link_or_text": "https://www.linkedin.com/jobs/view/1111/"})
        await call(client, "update_status", {"job_id": 999, "status": "applied"})

        # Step 3: matching
        await call(client, "match_resume", {"job_id": ai["job_id"]})
        await call(client, "match_resume", {"job_id": da["job_id"]})

        # Step 4: ranking
        await call(client, "rank_jobs")

        # Step 5: tailored resume (.docx)
        made = await call(client, "tailor_resume", {"job_id": ai["job_id"]})
        print_docx(made["file"])

        # Step 6: cover letter. Claude would write the letter; here the demo plays Claude.
        await call(client, "draft_cover_letter", {"job_id": ai["job_id"]})
        letter = {"job_id": ai["job_id"], "letter_text": LETTER}
        await call(client, "save_cover_letter", {**letter, "letter_text": LETTER.replace(
            "80%", "95%")})                       # invented number -> blocked
        await call(client, "save_cover_letter", {**letter, "learning_mentions": ["Docker"]})

        # Step 6: follow-ups (pretend we applied 10 days ago)
        await call(client, "update_status", {"job_id": da["job_id"], "status": "applied"})
        from jobhunt import db
        db.update_job(da["job_id"], {"date_updated": "2026-11-10"}, touch=False)
        await call(client, "followups")

        # Step 9: a pasted job-alert email (fake). Tracking junk is cleaned off the links.
        await call(client, "import_job_alerts", {"email_text": ALERT_EMAIL})

        await call(client, "list_jobs")


if __name__ == "__main__":
    asyncio.run(main())
