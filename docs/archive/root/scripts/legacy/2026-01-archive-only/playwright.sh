#!/usr/bin/env bash
set -euo pipefail
export PLAYWRIGHT_BROWSERS_PATH=0
export PATH="/Users/hujia/.nvm/versions/node/v24.2.0/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/hujia/.local/bin:$PATH"
exec /usr/local/bin/npx -y @playwright/mcp@latest

