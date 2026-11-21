# job-hunt-mcp

A calm, structured way to manage a job search, built as an **MCP server** in Python.
Claude (the MCP client) does the writing; this server does the fast, safe code:
tracking jobs, matching skills, ranking, and building resumes. It never applies by itself.

## Setup (Windows / PowerShell)

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe server.py   # starts the server over stdio (waits for a client)
```

See [PLAN.md](PLAN.md) for the plan and [LEARNING.md](LEARNING.md) for notes.
