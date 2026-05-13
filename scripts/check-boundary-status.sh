#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINI_DIR="$ROOT_DIR/hotpost-mini/hotpost-mini-app"

echo "== root repo =="
git -C "$ROOT_DIR" status --short -- hotpost-mini || true

echo
echo "== mini repo =="
if [ -d "$MINI_DIR/.git" ]; then
  git -C "$MINI_DIR" status --short
  git -C "$MINI_DIR" branch --show-current
  git -C "$MINI_DIR" log -1 --oneline --decorate
else
  echo "missing mini repo: $MINI_DIR"
  exit 1
fi
