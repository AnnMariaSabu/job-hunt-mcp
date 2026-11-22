# What I Learned: Job Hunt MCP Server

Notes in simple words, one section per step.

---

## Step 0: Setup + hello MCP server

### What we built
- `venv/`: a private box of Python packages just for this project.
- `requirements.txt`: the list of packages to install (`pip install -r requirements.txt`).
- `config.py`: every path and setting in one place.
- `server.py`: a tiny MCP server named **job-hunt** with one tool, `hello(name)`.
- `.gitignore`: tells git which files must never be uploaded (venv, personal data).

### Key ideas

**1. What is an MCP server?**
A program that gives an AI app (like Claude) **new abilities**.
Claude can't open my `jobs.db` file by itself. Our server can. So Claude *asks*
the server, and the server does the work and sends back the answer.

> Think of MCP like a **USB-C port for AI**: any MCP app (Claude Code, Claude
> Desktop, the Inspector) can plug into any MCP server, using the same rules.

**2. What is a tool?**
A normal Python function that the AI is allowed to call.

```python
@mcp.tool()
def hello(name: str) -> str:
    """Say hello. A tiny tool to check the server works."""
    return f"Hello, {name}!"
```

- `@mcp.tool()` = "Claude may call this function."
- The **name** (`hello`), the **docstring**, and the **type hints** (`name: str`)
  are sent to Claude. That's how Claude knows *what the tool does* and *what to
  pass in*. **Why it matters:** a clear docstring means Claude picks the right tool.

**3. What is stdio?**
"Standard input / standard output": the two text pipes every program has
(keyboard in, screen out).
Claude starts `server.py` as a child program, **writes requests into its
stdin**, and **reads answers from its stdout**. The messages are JSON, like:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "hello", "arguments": {"name": "Ann"}}}
```

- **Why stdio?** It's the simplest choice: no network, no ports, no passwords,
  and everything stays on my laptop.
- **Watch out:** never `print()` in a stdio server. stdout is the answer
  pipe, so a stray print mixes junk into the JSON and breaks the connection.

**4. MCP SDK v2 vs v1**
Old tutorials use `from mcp.server.fastmcp import FastMCP`. In **v2** it is:

```python
from mcp.server import MCPServer
mcp = MCPServer("job-hunt")
```

**5. Why config.py?**
`BASE_DIR = Path(__file__).resolve().parent` = "the folder this file is in".
All other paths are built from it, so the project works from any folder.

### How I checked it
A small client started `server.py` over stdio and called the tool:
```
Server name: job-hunt
Tools: ['hello']
hello('Ann') -> Hello, Ann! The job-hunt MCP server is running.
```

---

## Step 1: Test with the MCP Inspector

### What we did
Used the **MCP Inspector**, the official test app for MCP servers. It plays the role
of Claude, so I can click a tool and see the exact request and answer.

**Why?** When something breaks later, the Inspector tells me if the bug is in
*my server* (Inspector fails too) or in *Claude's setup* (Inspector works).

### How to run it
Browser UI (opens a web page; pick a tool, type arguments, click **Run**):
```powershell
npx -y @modelcontextprotocol/inspector .\venv\Scripts\python.exe server.py
```
CLI mode (prints JSON in the terminal):
```powershell
npx -y @modelcontextprotocol/inspector --cli .\venv\Scripts\python.exe server.py --method tools/list
npx -y @modelcontextprotocol/inspector --cli .\venv\Scripts\python.exe server.py --method tools/call --tool-name hello --tool-arg name=Ann
```
(`mcp dev server.py` also works, but it needs the `uv` tool installed.)

### Key idea: the schema is made for me
I only wrote `def hello(name: str) -> str` plus a docstring. The SDK turned that into:
```json
{"name": "hello",
 "description": "Say hello. A tiny tool to check the server works.",
 "inputSchema": {"properties": {"name": {"type": "string"}}, "required": ["name"]}}
```
That JSON is **exactly what Claude reads** to learn the tool. Type hints are
not just decoration. They become the instructions for the AI.

The answer came back as:
```json
{"content": [{"type": "text", "text": "Hello, Ann! The job-hunt MCP server is running."}],
 "isError": false}
```

---

## Step 2: Tracker tools (SQLite)

### What we built
| File | Job (restaurant picture) |
|---|---|
| `server.py` | **Waiter**: takes Claude's order, calls the kitchen. Tiny functions + docstrings. |
| `jobhunt/tracker.py` | **Chef**: checks the rules (valid status? duplicate link?). |
| `jobhunt/db.py` | **Fridge**: stores and fetches rows in SQLite (`data/jobs.db`). |
| `jobhunt/sources.py` | Finds links in text, detects LinkedIn / Naukri / Indeed. |

Tools: `add_job`, `update_status`, `list_jobs`, `get_job`, `add_note`.

**Why 3 layers?** The Streamlit dashboard (Step 10) reuses the chef and fridge
without the waiter. And each layer is easy to test alone.

### Key ideas
- **SQLite** = a whole database in one file. Built into Python (`import sqlite3`).
- **`?` placeholders** in SQL: `conn.execute("... WHERE id = ?", (job_id,))`.
  sqlite3 fills them in safely. Gluing text into SQL yourself allows *SQL injection*.
- **`Literal` types** = a fixed list of choices:
  ```python
  JobStatus = Literal["saved", "applied", "interview", "offer", "rejected"]
  def update_status(job_id: int, status: JobStatus): ...
  ```
  MCP shows Claude `"enum": ["saved", ...]`, so Claude *can't* invent a status like "hired".
- **Errors Claude can read.** In SDK v2 only a `ToolError`'s message reaches Claude
  (other errors are hidden for safety). Our code raises `ValueError("No job with id 42...")`
  and the `friendly_errors` decorator turns it into a `ToolError`. Then Claude can fix
  its own mistake (e.g. call `list_jobs` to find the right id).
- **Duplicates**: same link → no second row. Simple rule, saves a messy tracker.
- **No delete tool**: deleting is human-only (dashboard), so the AI can't lose my data.
- **Tests with a fake database**: `tests/conftest.py` points `config.DB_PATH` at a temp
  folder for every test (`monkeypatch`). Tests can never touch my real `jobs.db`.

### Output
```
12 passed in 2.30s
```

---

## Step 3: Master resume + bullets + match_resume

### What we built
- `data/master_resume.example.yaml`: profile, education, skills (a **fake** person).
- `data/master_bullets.example.yaml`: every achievement, written once, **tagged by skill**.
- `jobhunt/data_files.py`: loads the YAML files. Uses my real file if it exists,
  else the example. Also has the **bullet safety check**.
- `jobhunt/skills.py`: finds skills in job text and compares them with mine.
- `jobhunt/matching.py` + tool `match_resume(job_id)`.
- `demo.py`: runs the tools on fake data in a temp folder (`python demo.py`).

### Key ideas
- **Private vs example data.** My real `master_resume.yaml` is git-ignored.
  The `.example.yaml` files are fake and safe to commit, and the code falls back to them,
  so anyone can run the project.
- **YAML** = data written like a tidy list. `yaml.safe_load` reads *only data*
  (plain `yaml.load` could run code hidden in a file).
- **Skill matching without AI.** A catalog of skills + aliases:
  `"scikit-learn": ["scikit-learn", "sklearn"]`. A regex looks for each alias as a
  *whole word*: `(?<!\w)java(?!\w)` doesn't match inside "javascript".
  **Why no AI here?** Code is instant, free, gives the same answer every time,
  and I can see exactly *why* it said 57%.
- **Match %** = matched skills ÷ skills the job asks for.
  Example: job wants {python, sql, docker}, I have {python, sql} → 2/3 = 66.7%, gap = docker.
- **Skill gaps** = what to learn next. If "docker" keeps showing up, that's a signal.
- **Safety check** (`check_bullets`): every skill tagged on a bullet must also be on my
  resume. Otherwise a tailored resume could claim a skill I never said I have.
- **A bug the tests caught early:** the skill "r" matched "Rs. 5 LPA". Fix: search only
  aliases like "r programming", never a single letter.

### Output (demo)
```
>>> match_resume({"job_id": 1})
"match_percent": 57.1,
"matched_skills": ["langchain", "llm", "python", "rag"],
"skill_gaps": ["docker", "fastapi", "vector databases"],
"supporting_bullets": [{"id": "rag-bot", ...}]
```
`20 passed`

---

## Step 4: Rubric + rank_jobs

### What we built
- `data/rubric.example.yaml`: my priorities with **weights**.
- `jobhunt/ranking.py` + tool `rank_jobs(status="saved")`.

### Key ideas
- **Two different questions:**
  `match_resume` = "do *I* fit the job?" and `rank_jobs` = "does the job fit *me*?"
  In the demo the Data Analyst job is a 100% skill match but ranks lower,
  because it pays 4 LPA and mentions no learning.
- **Weighted average.** Each factor scores 0.0–1.0, the weight says how much it counts:
  ```
  role_fit 0.79 x 35 + location 1.0 x 20 + salary 1.0 x 15 + learning 1.0 x 20 + company 0.5 x 10
  = 87.5 out of 100
  ```
  Change the weights in `rubric.yaml` and the ranking follows *my* priorities.
- **Explainable scores.** Every factor returns a reason ("in Kochi", "6 LPA (target 6)").
  A ranking you can't explain is a ranking you can't trust.
- **Unknown ≠ bad.** No salary given → 0.5 (neutral), so a job isn't punished for a
  missing number.
- **Parsing text with regex:** `"5-7 LPA"` → 6.0 (middle of the range).
- **Scores don't reset follow-ups.** Saving `rank_score` uses `touch=False`, so
  `date_updated` only changes on real news (status, notes). A test checks this.
- **Checking config files.** A typo like `vibes: 10` in the rubric gives a clear error
  instead of a silent wrong ranking.

`30 passed`

---

## Step 5: tailor_resume (.docx)

### What we built
- `jobhunt/resume.py` + tool `tailor_resume(job_id, bullet_ids=None)`
  → `output/resumes/<Company>_<Role>.docx` (python-docx).
- `jobhunt/safety.py`: checks every skill and bullet against my data files.

### Key ideas
- **Tailoring = choosing + ordering, not rewriting.**
  For an AI job: RAG bullets first, "Python, LLM, RAG, LangChain" first in Skills.
  The words are always *my* words from `master_bullets.yaml`.
- **Gaps stay off the resume.** The job wants Docker, but I don't have it, so it's
  reported as `skill_gaps_not_added` and never written.
- **Claude can choose, code checks.** Claude may pass `bullet_ids=["rag-bot", ...]`.
  A made-up id → clear error. **Why?** The AI is good at judging *which* bullets fit,
  but only code can *guarantee* nothing is invented.
- **Safety check before saving** (`check_resume_content`): every skill must be spelled
  exactly as in my resume, every bullet must match word for word. If not → no file.
  This guards against future changes too ("belt and braces").
- **Safe file names:** `"Acme AI / Labs"` → `Acme-AI-Labs` (no `/` or `?`, which Windows forbids).
- **python-docx basics:** `Document()`, `add_heading`, `add_paragraph(text, style="List Bullet")`,
  `run.bold = True`, `doc.save(path)`.

`35 passed`

---

## Step 6: Cover letter + follow-ups

### What we built
- `jobhunt/cover_letter.py` + tools `draft_cover_letter(job_id)` and
  `save_cover_letter(job_id, letter_text, learning_mentions)`.
- `jobhunt/reminders.py` + tool `followups(days=7)`.

### Key ideas
- **Claude writes, code checks.** Our server has no AI inside. So:
  1. `draft_cover_letter` gives Claude a **facts pack** (job, my real bullets, gaps, rules).
     Giving an AI real facts to write from is called **grounding**.
  2. Claude writes the letter.
  3. `save_cover_letter` **checks it in code** before saving. A check like this is a **guardrail**.
- **The guardrails:**
  - a skill not on my resume → blocked ("Kubernetes")
  - a number not in my data or the job post → blocked ("95%" when my bullet says 80%)
  - too short / too long → blocked
- **"I know X" vs "I'm learning X".** Simple code can't tell these apart. So Claude
  must *declare* learning skills: `learning_mentions=["Docker"]`. Honest and visible.
- **Error messages are instructions.** The blocked message says *what* to fix, so
  Claude can fix the letter by itself and try again.
- **Follow-ups:** status `applied`/`interview` + no update for 7+ days → remind me.
  After I follow up (a *human* sends it), `add_note` resets the timer.
- **Testing dates:** `followups(today=date(2026, 11, 21))`. Passing "today" in makes
  time-based code easy to test.
- **Naming:** the module is `reminders.py`, not `followups.py`, so it doesn't clash with
  the tool function `followups()` in server.py.

`42 passed`
