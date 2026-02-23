#!/usr/bin/env bash
set -euo pipefail

show_usage() {
  cat <<USAGE
Usage: score_batched.sh --input <candidates.json> --limit <N> --topn <K>
Env overrides:
  THEMES   (default: what_to_sell,how_to_sell,where_to_sell,how_to_source)
  BATCHES  (default: 300 600 900 1200 1500 <limit>)
  REDDIT_MAX_CONCURRENCY (default: 3)
  REDDIT_RATE_LIMIT      (default: 45)
  REDDIT_REQUEST_TIMEOUT_SECONDS (default: 30)
USAGE
}

INPUT=""
LIMIT=""
TOPN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2;;
    --limit) LIMIT="$2"; shift 2;;
    --topn)  TOPN="$2";  shift 2;;
    -h|--help) show_usage; exit 0;;
    *) echo "Unknown arg: $1"; show_usage; exit 1;;
  esac
done

if [[ -z "$INPUT" || -z "$LIMIT" || -z "$TOPN" ]]; then
  echo "Missing required args" >&2
  show_usage
  exit 1
fi

THEMES_DEFAULT="what_to_sell,how_to_sell,where_to_sell,how_to_source"
THEMES="${THEMES:-$THEMES_DEFAULT}"

# Reddit API safer defaults
export REDDIT_MAX_CONCURRENCY="${REDDIT_MAX_CONCURRENCY:-3}"
export REDDIT_RATE_LIMIT="${REDDIT_RATE_LIMIT:-45}"
export REDDIT_REQUEST_TIMEOUT_SECONDS="${REDDIT_REQUEST_TIMEOUT_SECONDS:-30}"

# batches
if [[ -z "${BATCHES:-}" ]]; then
  BATCHES=(300 600 900 1200 1500 "$LIMIT")
else
  # shellcheck disable=SC2206
  BATCHES=( ${BATCHES} )
fi

PY=${PYTHON:-/opt/homebrew/bin/python3.11}

echo "==> Batched scoring. input=$INPUT limit=$LIMIT topn=$TOPN themes=$THEMES batches=${BATCHES[*]}"

for cur in "${BATCHES[@]}"; do
  echo "[Batch] limit=$cur (resume) ..."
  PYTHONPATH=. "$PY" scripts/score_crossborder.py \
    --limit "$cur" --input "${INPUT}" --themes "$THEMES" --topn "$TOPN" --resume || true
  # progress snapshot
  if [[ -f data/top5000_subreddits_scored.csv ]]; then
    echo "[Progress] scored.csv: $(($(wc -l < data/top5000_subreddits_scored.csv)-1)) rows (data)"
  fi
  for f in ../reports/local-acceptance/crossborder-*-top${TOPN}.csv; do
    if [[ -f "$f" ]]; then
      echo "[Progress] $(basename "$f"): $(($(wc -l < "$f")-1)) rows"
    fi
  done
done

echo "==> Batched scoring done."

