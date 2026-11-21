"""The job-hunt MCP server.

Run it:  python server.py
It talks over stdio: it reads requests from stdin and writes answers to stdout.
So never use print() in this server, because it would mix junk into the answers.
"""

from mcp.server import MCPServer

import config

mcp = MCPServer(config.SERVER_NAME)


@mcp.tool()
def hello(name: str) -> str:
    """Say hello. A tiny tool to check the server works."""
    return f"Hello, {name}! The job-hunt MCP server is running."


if __name__ == "__main__":
    mcp.run()  # default transport is "stdio"
