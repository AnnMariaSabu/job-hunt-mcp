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
