"""Shared test setup. pytest loads this file automatically."""

import asyncio

import pytest
from mcp import Client

import config


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """EVERY test gets its own empty temp folder for the database and output files.

    Why? Tests must never touch my real jobs.db or my real resume files.
    `monkeypatch` changes a setting only during one test, then puts it back.
    """
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "jobs.db")
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(config, "RESUMES_DIR", tmp_path / "output" / "resumes")
    monkeypatch.setattr(config, "COVER_LETTERS_DIR", tmp_path / "output" / "cover_letters")
    # Point the private data files at paths that don't exist, so the code
    # falls back to the committed *.example.yaml files (fake data).
    monkeypatch.setattr(config, "MASTER_RESUME_PATH", tmp_path / "master_resume.yaml")
    monkeypatch.setattr(config, "MASTER_BULLETS_PATH", tmp_path / "master_bullets.yaml")
    monkeypatch.setattr(config, "RUBRIC_PATH", tmp_path / "rubric.yaml")
    return tmp_path


def call_tool(name: str, arguments: dict | None = None):
    """Call one MCP tool through a real MCP client (in memory, no subprocess)."""
    from server import mcp

    async def run():
        async with Client(mcp) as client:
            return await client.call_tool(name, arguments or {})

    return asyncio.run(run())


@pytest.fixture
def tool():
    return call_tool
