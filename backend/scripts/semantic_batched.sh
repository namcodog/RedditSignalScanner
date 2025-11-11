#!/usr/bin/env bash
set -euo pipefail

# Defaults
INPUT="../backend/data/crossborder_candidates.json"
LIMIT=1762
TOPN=200
POSTS_PER=10
BATCHES=(600 1000 1400 1762)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2;;
    --limit) LIMIT="$2"; shift 2;;
    --topn) TOPN="$2"; shift 2;;
    --posts-per) POSTS_PER="$2"; shift 2;;
    --batches) IFS=' ' read -r -a BATCHES <<< "$2"; shift 2;;
    *) shift;;
  esac
done

echo "==> Batched semantic scoring. input=$INPUT limit=$LIMIT topn=$TOPN posts_per=$POSTS_PER batches=${BATCHES[*]}"

for B in "${BATCHES[@]}"; do
  if (( B > LIMIT )); then continue; fi
  echo "[Batch] limit=$B ...";
  PYTHONPATH=. /opt/homebrew/bin/python3.11 scripts/score_with_semantic.py \
    --lexicon ../backend/config/semantic_sets/crossborder.yml \
    --input "$INPUT" --limit "$B" --posts-per "$POSTS_PER" --topn "$TOPN"
  echo "Top list: reports/local-acceptance/crossborder-semantic-what_to_sell-top${TOPN}.csv"
  echo "Top list: reports/local-acceptance/crossborder-semantic-how_to_sell-top${TOPN}.csv"
  echo "Top list: reports/local-acceptance/crossborder-semantic-where_to_sell-top${TOPN}.csv"
  echo "Top list: reports/local-acceptance/crossborder-semantic-how_to_source-top${TOPN}.csv"
  # Quick progress snapshot
  if [[ -f ../backend/data/crossborder_semantic_scored.csv ]]; then
    echo "[Progress] semantic_scored.csv: $(($(wc -l < ../backend/data/crossborder_semantic_scored.csv) - 1)) rows"
  fi
  for f in ../reports/local-acceptance/crossborder-semantic-*-top${TOPN}.csv; do
    [[ -f "$f" ]] || continue; n=$(($(wc -l < "$f") - 1)); echo "[Progress] $(basename "$f"): $n rows";
  done
done

echo "==> Batched semantic scoring done."

