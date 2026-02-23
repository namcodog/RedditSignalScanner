#!/usr/bin/env bash
set -euo pipefail

# Activate the Serena MCP virtual environment and run the MCP server
cd /Users/hujia/Desktop/RedditSignalScanner/.serena-mcp

# Check if .venv exists, if not try to use it from the installed package
if [ -d ".venv" ]; then
    source .venv/bin/activate
    exec python -m serena.cli start_mcp_server
else
    # Try using uv or pip to run
    exec python3 -m serena.cli start_mcp_server
fi
