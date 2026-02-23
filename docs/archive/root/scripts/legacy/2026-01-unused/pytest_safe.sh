#!/usr/bin/env bash
set -euo pipefail
# Safer pytest runner to avoid silent exits:
# - disable 3rd-party plugin autoload
# - enable console logging and full trace
# - allow extra args to be passed through
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
: "${APP_ENV:=test}"
: "${ENABLE_CELERY_DISPATCH:=0}"
python3 -m pytest \
  -p pytest_asyncio.plugin \
  -o log_cli=true -o log_cli_level=INFO \
  --full-trace \
  "$@"

