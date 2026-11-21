"""Tests through the real MCP protocol, the same way Claude calls the tools."""

import asyncio

from mcp import Client


def test_tools_are_listed_with_status_choices():
    from server import mcp

    async def run():
        async with Client(mcp) as client:
            return await client.list_tools()

    tools = {t.name: t for t in asyncio.run(run()).tools}
    assert {"hello", "add_job", "update_status", "list_jobs", "get_job", "add_note"} <= set(tools)
    # The Literal type became a list of allowed values that Claude can see:
    status_schema = tools["update_status"].input_schema["properties"]["status"]
    assert status_schema["enum"] == ["saved", "applied", "interview", "offer", "rejected"]


def test_hello(tool):
    result = tool("hello", {"name": "Ann"})
    assert result.content[0].text == "Hello, Ann! The job-hunt MCP server is running."


def test_add_and_list_job(tool):
    added = tool("add_job", {"link_or_text": "https://www.linkedin.com/jobs/view/1/",
                             "company": "Acme", "role": "Data Analyst"})
    assert not added.is_error
    listed = tool("list_jobs")
    assert listed.structured_content["result"][0]["company"] == "Acme"


def test_our_error_message_reaches_claude(tool):
    result = tool("update_status", {"job_id": 42, "status": "applied"})
    assert result.is_error
    assert "No job with id 42" in result.content[0].text
