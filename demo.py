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

        await call(client, "list_jobs")


if __name__ == "__main__":
    asyncio.run(main())
