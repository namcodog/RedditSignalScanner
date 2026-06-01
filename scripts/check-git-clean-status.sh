#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINI_DIR="$ROOT_DIR/hotpost-mini/hotpost-mini-app"

status=0

check_repo() {
  local label="$1"
  local dir="$2"

  echo "== $label =="

  if [ ! -d "$dir/.git" ]; then
    echo "missing git repo: $dir"
    status=1
    echo
    return
  fi

  local branch
  branch="$(git -C "$dir" branch --show-current)"
  if [ "$branch" != "main" ]; then
    echo "branch mismatch: expected main, got ${branch:-detached}"
    status=1
  fi

  local porcelain
  porcelain="$(git -C "$dir" status --porcelain=v1 --untracked-files=all)"
  if [ -n "$porcelain" ]; then
    echo "dirty working tree:"
    echo "$porcelain"
    status=1
  fi

  if ! git -C "$dir" diff --quiet; then
    echo "unstaged diff exists"
    status=1
  fi

  if ! git -C "$dir" diff --cached --quiet; then
    echo "staged diff exists"
    status=1
  fi

  local stash
  stash="$(git -C "$dir" stash list)"
  if [ -n "$stash" ]; then
    echo "stash is not empty:"
    echo "$stash"
    status=1
  fi

  local upstream
  if ! upstream="$(git -C "$dir" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)"; then
    echo "missing upstream for branch ${branch:-detached}"
    status=1
    echo
    return
  fi

  local head upstream_head
  head="$(git -C "$dir" rev-parse HEAD)"
  upstream_head="$(git -C "$dir" rev-parse "$upstream")"
  if [ "$head" != "$upstream_head" ]; then
    echo "local HEAD does not match $upstream"
    echo "HEAD:     $head"
    echo "$upstream: $upstream_head"
    status=1
  fi

  local remote remote_branch remote_head
  remote="${upstream%%/*}"
  remote_branch="${upstream#*/}"
  remote_head="$(git -C "$dir" ls-remote "$remote" "refs/heads/$remote_branch" | awk '{print $1}')"
  if [ -z "$remote_head" ]; then
    echo "remote branch not found: $upstream"
    status=1
  elif [ "$head" != "$remote_head" ]; then
    echo "local HEAD does not match remote $upstream"
    echo "HEAD:   $head"
    echo "remote: $remote_head"
    status=1
  fi

  echo "branch: $branch"
  echo "HEAD: $head"
  echo
}

check_repo "root repo" "$ROOT_DIR"
check_repo "mini repo" "$MINI_DIR"

exit "$status"
