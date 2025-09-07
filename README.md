# OPENAI agent to ADX connectivity — quick run instructions

This repository contains an interactive client that connects to an MCP (Model Context Protocol)
server to run Azure Data Explorer (ADX / KQL) queries. We use the `uv` task runner for convenience.

## Setup

- Create a virtual environment and install Python dependencies (example):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# or install deps ad-hoc, e.g.:
pip install python-dotenv mcp-client azure-kusto-data
```

- Ensure any required environment variables are set (you can use a `.env` file):

```
ADX_CLUSTER_URI=...
ADX_DATABASE=...
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
MCP_HOST=127.0.0.1
MCP_PORT=8000
```

## Running with `uv`

The repo uses `uv` as a lightweight task runner. Here are common commands you'll use from the project root.

- Start the MCP server (run from `mcp-server`):

```bash
# starts the adx MCP server (example)
uv run adx_mcp_server.py
```

- Run the interactive client:

```bash
uv run interactive_claude_mcp.py
```

Notes:
- Use `uv add <package>` to add dependencies to the local uv environment (you used this for `azure-kusto-data`).
- If a task exits with code 1 or 130, check the terminal output for a traceback. Common issues are missing env vars or missing binaries (e.g., Claude Code CLI).

## Troubleshooting

- `Claude Code not found` — install the Claude CLI or use the local shim:

```bash
npm install -g @anthropic-ai/claude-code
# or if you prefer local install in the repo
npm install @anthropic-ai/claude-code
export PATH="$PWD/node_modules/.bin:$PATH"
```

- If you see `❌ Error talking to Claude+MCP: 'ClaudeSDKClient' object has no attribute 'chat'` the installed SDK differs from the expected one; open `interactive_claude_mcp.py` and make sure the client exposes a streaming `chat()` or a `messages.create()` method.

## Quick development tips

- To run the MCP server in the background while you iterate on the client, start the server in one terminal and the client in another.
- If you want the client to run without installing the Claude CLI, ask the maintainer to add the small Python shim that will spawn the MCP server process locally.

---

If you want, I can add a uv task file (e.g., `uv.toml`) with named tasks for starting the server and client.

