# job-hunt-mcp

A calm, structured way to run a job search, built as an **MCP server** in Python
(official MCP Python SDK **v2**).

You talk to Claude ("save this job", "rank my jobs", "make a resume for job 3"), and
Claude uses this server's tools. **Claude does the writing; the server does the fast,
safe code:** a SQLite job tracker, skill matching, ranking, Word documents, and safety
checks. **It never applies to jobs by itself.**

Built for a fresher searching for AI Engineer / AI/ML Engineer / Data Analyst / Data
Engineer roles in Kochi, Bangalore and Chennai. All of that is easy to change in
`config.py` and `rubric.yaml`.

## How it fits together

```
 You ──chat──> Claude Code ──MCP over stdio──> server.py  (the "waiter": tools, resources, prompts)
                                                   │
 You ──browser──> dashboard.py (Streamlit) ────────┤
                                                   ▼
                                           jobhunt/  (the "kitchen": all logic)
                                           tracker · matching · ranking · resume · cover_letter
                                           reminders · sources · safety · skills · data_files
                                                   │
                                                   ▼
                                     data/jobs.db (SQLite) + data/*.yaml + output/*.docx
```

## Features

| Tool | What it does |
|---|---|
| `add_job(link_or_text, ...)` | Save a job from a link or pasted job text. Skips duplicates. |
| `import_job_alerts(email_text, dry_run)` | Save all jobs from a pasted LinkedIn / Naukri / Indeed alert email. |
| `update_job_details(job_id, ...)` | Fill in a description or fix details later. |
| `list_jobs(status?)` · `get_job(job_id)` | See your jobs. |
| `update_status(job_id, status, note)` | saved → applied → interview → offer / rejected. |
| `add_note(job_id, note)` | Dated note; also resets the follow-up timer. |
| `match_resume(job_id)` | Match %, matched skills, skill gaps, and your proof bullets. |
| `rank_jobs(status)` | Score 0–100 from *your* rubric, with a reason for every factor. |
| `tailor_resume(job_id, bullet_ids?)` | One-page `.docx` from your real bullets only. |
| `draft_cover_letter(job_id)` · `save_cover_letter(...)` | Facts for Claude to write from; checks the letter before saving `.docx`. |
| `followups(days?)` | Applied/interview jobs with no news for 7+ days. |
| `skill_gap_report()` | The skills most of your jobs want that you don't have yet. |
| `hello(name)` | Health check. |

**Resources:** `resume://master`, `resume://bullets`, `jobs://list`, `jobs://{job_id}`<br>
**Prompts:** `find_jobs(roles?, cities?)`, `weekly_job_review`, `prepare_application(job_id)`

## How jobs get in

| Site | How | Example |
|---|---|---|
| **Indeed** | Claude searches with the **Indeed connector** (connect it in claude.ai → Settings → Connectors) | `/mcp__job-hunt__find_jobs`, or *"Find AI Engineer jobs in Kochi on Indeed and save the good ones"* |
| **LinkedIn / Naukri** | **Paste** the link **and** the job text (the text is what makes matching work) | Claude: *"Save this job: https://... (paste the description)"*. Dashboard: **Add jobs** → paste both into the big box. |
| **Any alert email** | Copy the whole email and paste it | Dashboard: **Add jobs → Import a job-alert email** |

The server never opens LinkedIn or Naukri pages itself (no scraping). It reads only what
you paste or what the Indeed connector returns.

## Safety rules (enforced in code)

- **Never invents skills or experience.** Resumes use only bullets from
  `master_bullets.yaml`, word for word. Bullets can only be tagged with skills from your
  resume. Cover letters are blocked if they claim a skill or a number that isn't in your data.
- **Never applies, never contacts anyone, no scraping.** It reads only text you paste.
- **Deleting a job is human-only** (dashboard, with a confirm tick). There is no AI delete tool.
- **Your data stays private.** Real data files, `jobs.db` and `output/` are git-ignored;
  only fake `*.example.yaml` files are committed.

## Setup (Windows / PowerShell)

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Use your own data
The project runs right away on a **fake example person**. To use your real details:
```powershell
Copy-Item data\master_resume.example.yaml  data\master_resume.yaml
Copy-Item data\master_bullets.example.yaml data\master_bullets.yaml
Copy-Item data\rubric.example.yaml         data\rubric.yaml
```
Then edit the three new files (they are git-ignored). Tag each bullet only with skills
that are listed in your `master_resume.yaml`; the safety check enforces this.

## Run it

| What | Command |
|---|---|
| Connect to **Claude Code** | Open this folder in Claude Code and approve the `job-hunt` server from `.mcp.json` (or run `/mcp`). Check with `claude mcp list`. |
| Connect to the **Claude Desktop app** | Settings → Developer → Edit Config, add the block below (full paths), then fully quit and reopen the app. |
| **Dashboard** | `.\venv\Scripts\streamlit run dashboard.py` |
| **Demo** (fake data, temp folder) | `.\venv\Scripts\python.exe demo.py` |
| **MCP Inspector** | `npx -y @modelcontextprotocol/inspector .\venv\Scripts\python.exe server.py` |
| **Tests** | `.\venv\Scripts\python.exe -m pytest` |
| **Evaluation** | `.\venv\Scripts\python.exe evaluate.py` |

Claude Desktop config (`claude_desktop_config.json`; the Microsoft Store version keeps it in
`%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\`):
```json
{
  "mcpServers": {
    "job-hunt": {
      "command": "C:\\path\\to\\job-hunt-mcp\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\job-hunt-mcp\\server.py"]
    }
  }
}
```
The claude.ai **website** can't use this server: it only reaches servers on the internet,
and this one runs on your laptop over stdio.

Things to say to Claude:
- *"Find jobs on Indeed"* (or run `/mcp__job-hunt__find_jobs`)
- *"Save this job: <paste the job post>"*
- *"Import this job alert email: <paste>"*
- *"Rank my saved jobs and tell me the top 3"*
- *"Prepare my application for job 2"* (or use the `prepare_application` prompt)
- *"Run my weekly job review"* (or `/mcp__job-hunt__weekly_job_review`)

## Quality

- **69 tests**: they use a temporary database and the fake example data, so they never touch your files.
- **Evaluation** (`evaluate.py`): the skill finder, checked against 8 hand-labelled job posts,
  scores **precision 1.00, recall 0.89, F1 0.94**, and the ranking gets **5/5** obvious pairs right.

## Project layout

```
server.py          MCP server: tools, resources, prompts (thin wrappers)
config.py          all paths and settings
dashboard.py       Streamlit dashboard (human control panel)
demo.py            every tool in action on fake data
evaluate.py        quality evaluation  (evaluation/cases.yaml = labelled job posts)
.mcp.json          connects the server to Claude Code
jobhunt/           all the logic (shared by server + dashboard)
data/              *.example.yaml (committed) + your private files (git-ignored)
tests/             pytest tests
LEARNING.md        what I learned, step by step, in simple words
PLAN.md            the project plan
```

Inspired by [dfrysinger/ai-job-hunt-toolkit](https://github.com/dfrysinger/ai-job-hunt-toolkit);
written from scratch in Python for learning.
