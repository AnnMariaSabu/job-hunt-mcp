"""Resources and prompts, tested through the real MCP protocol."""

import asyncio
import json

from mcp import Client

from jobhunt import matching, tracker


def with_client(work):
    from server import mcp

    async def run():
        async with Client(mcp) as client:
            return await work(client)

    return asyncio.run(run())


def test_resume_resources_can_be_read():
    async def work(client):
        resume = await client.read_resource("resume://master")
        bullets = await client.read_resource("resume://bullets")
        return resume.contents[0].text, bullets.contents[0].text

    resume_text, bullets_text = with_client(work)
    assert "Asha Example" in resume_text
    assert "rag-bot" in bullets_text


def test_job_resources_list_and_template():
    job_id = tracker.add_job("https://example.com/j", company="Acme")["job_id"]

    async def work(client):
        templates = await client.list_resource_templates()
        listing = await client.read_resource("jobs://list")
        one = await client.read_resource(f"jobs://{job_id}")
        return templates, listing, one

    templates, listing, one = with_client(work)
    assert "jobs://{job_id}" in [t.uri_template for t in templates.resource_templates]
    assert json.loads(listing.contents[0].text)[0]["company"] == "Acme"
    assert json.loads(one.contents[0].text)["id"] == job_id


def test_prompts_are_listed_and_filled_in():
    async def work(client):
        names = [p.name for p in (await client.list_prompts()).prompts]
        weekly = await client.get_prompt("weekly_job_review")
        prep = await client.get_prompt("prepare_application", {"job_id": "7"})
        return names, weekly, prep

    names, weekly, prep = with_client(work)
    assert {"weekly_job_review", "prepare_application"} <= set(names)
    assert "followups()" in weekly.messages[0].content.text
    assert "tailor_resume(7)" in prep.messages[0].content.text


def test_skill_gap_report_counts_gaps_across_jobs():
    for n in range(3):
        tracker.add_job(f"https://example.com/{n}", role="AI Engineer",
                        description="Python and Docker" + (" and AWS" if n == 0 else ""))
    report = matching.skill_gap_report()
    assert report["jobs_checked"] == 3
    assert report["top_gaps"][0] == {"skill": "docker", "jobs": 3}
    assert {"skill": "aws", "jobs": 1} in report["top_gaps"]
