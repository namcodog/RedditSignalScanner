#!/usr/bin/env python3
from __future__ import annotations

"""Merge blacklist suggestions into blacklist.txt with de-duplication.

Inputs:
  --blacklist backend/config/entity_dictionary/blacklist.txt
  --suggestions backend/reports/local-acceptance/blacklist_suggestions.txt
"""

import argparse
from pathlib import Path


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge blacklist suggestions")
    ap.add_argument("--blacklist", type=Path, required=True)
    ap.add_argument("--suggestions", type=Path, required=True)
    args = ap.parse_args()

    base = _read_lines(args.blacklist)
    sugg = _read_lines(args.suggestions)
    merged = sorted(set(base) | set(sugg))
    args.blacklist.parent.mkdir(parents=True, exist_ok=True)
    args.blacklist.write_text("\n".join(merged) + ("\n" if merged else ""), encoding="utf-8")
    print(f"✅ merged blacklist ({len(base)} -> {len(merged)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

