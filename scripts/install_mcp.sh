#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${GREEN}[*] Setting up Serena MCP...${RESET}"

# 1. Setup Serena MCP in .serena-mcp
if [ -d ".serena-mcp" ]; then
    echo -e "${YELLOW}Found .serena-mcp directory. Installing dependencies with uv...${RESET}"
    cd .serena-mcp
    # Ensure uv is available
    if ! command -v uv &> /dev/null; then
        echo "Error: uv is not installed. Please install uv first."
        exit 1
    fi
    # Sync dependencies (creates .venv)
    uv sync
    cd ..
    echo -e "${GREEN}[✓] Serena MCP dependencies installed.${RESET}"
else
    echo "Error: .serena-mcp directory not found!"
    exit 1
fi

# 2. Setup Spec Kit (Optional, but recommended in guide)
echo -e "${YELLOW}Ensuring Spec Kit is available...${RESET}"
# We don't necessarily need to 'install' it if we use uvx, but let's check
echo -e "${GREEN}[✓] Spec Kit ready (will use uvx).${RESET}"

# 3. Generate Config Snippet
PWD=$(pwd)
SERENA_PATH="$PWD/.serena-mcp"
UV_PATH=$(which uv)

echo -e "\n${GREEN}==============================================${RESET}"
echo -e "${GREEN}SUCCESS! MCP Tools are ready.${RESET}"
echo -e "${GREEN}==============================================${RESET}"
echo -e "Please configure your Claude Desktop or MCP Client with the following config:"
echo -e ""
echo -e "JSON Configuration (add to 'mcpServers'):"
echo -e "--------------------------------------------------"
cat <<EOF
{
  "serena": {
    "command": "$PWD/scripts/mcp/serena.sh"
  },
  "exa": {
    "command": "npx",
    "args": ["-y", "exa-mcp-server"],
    "env": {
      "EXA_API_KEY": "<YOUR_EXA_API_KEY>"
    }
  },
  "chrome-devtools": {
    "command": "npx",
    "args": ["-y", "chrome-devtools-mcp@latest"]
  },
  "spec-kit": {
    "command": "uvx",
    "args": ["--from", "git+https://github.com/github/spec-kit.git", "specify"]
  }
}
EOF
echo -e "--------------------------------------------------"
echo -e "\nNote: Replace <YOUR_EXA_API_KEY> with your actual API key from .env.local"
