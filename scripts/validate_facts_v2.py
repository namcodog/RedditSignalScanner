#!/usr/bin/env python3
"""Validator for facts v2 (schema_version>=2).
Checks: schema_version, quotes linkage, ps_metric completeness, brand_pain gates,
missing rate diagnostics.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

MIN_QUOTES = 1
MIN_BRAND_MENTIONS = 3
MIN_BRAND_AUTHORS = 2
MIN_BRAND_EVIDENCE = 3


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema_version(data: dict[str, Any]) -> list[str]:
    if str(data.get("schema_version")) < "2":
        return ["schema_version < 2"]
    return []


def validate_quotes(data: dict[str, Any]) -> list[str]:
    quotes = (data.get("evidence") or {}).get("quotes") or []
    errs = []
    if len(quotes) < MIN_QUOTES:
        errs.append(f"quotes less than {MIN_QUOTES}")
    for idx, q in enumerate(quotes):
        if not q.get("comment_id") or not q.get("permalink"):
            errs.append(f"quote[{idx}] missing comment_id/permalink")
    return errs


def validate_ps_metric(data: dict[str, Any]) -> list[str]:
    ps = data.get("ps_metric") or {}
    errs = []
    if ps:
        if ps.get("numerator") is None or ps.get("denominator") is None:
            errs.append("ps_metric missing numerator/denominator")
        if ps.get("status") == "insufficient_sample" and not ps.get("reason"):
            errs.append("ps_metric insufficient_sample but no reason")
    return errs


def validate_brand_pain(data: dict[str, Any]) -> list[str]:
    errs = []
    for i, b in enumerate(data.get("brand_pain") or []):
        status = b.get("status")
        if status == "ok":
            if (b.get("mentions", 0) or 0) < MIN_BRAND_MENTIONS:
                errs.append(f"brand_pain[{i}] ok but mentions < {MIN_BRAND_MENTIONS}")
            if (b.get("unique_authors", 0) or 0) < MIN_BRAND_AUTHORS:
                errs.append(f"brand_pain[{i}] ok but unique_authors < {MIN_BRAND_AUTHORS}")
            if len(b.get("evidence_quote_ids") or []) < MIN_BRAND_EVIDENCE:
                errs.append(f"brand_pain[{i}] ok but evidence < {MIN_BRAND_EVIDENCE}")
        if status == "insufficient_sample" and not b.get("reason"):
            errs.append(f"brand_pain[{i}] insufficient_sample but no reason")
    return errs


def validate_missing_rate(data: dict[str, Any]) -> list[str]:
    diag = data.get("diagnostics") or {}
    missing = (diag.get("missing_flags") or {})
    errs = []
    # If everything missing, flag as abnormal
    if all(missing.values()) and missing:
        errs.append("all missing_flags set to True (abnormal)")
    return errs


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: scripts/validate_facts_v2.py <facts.json>")
        sys.exit(1)
    data = load(Path(sys.argv[1]))
    errors = []
    errors += validate_schema_version(data)
    errors += validate_quotes(data)
    errors += validate_ps_metric(data)
    errors += validate_brand_pain(data)
    errors += validate_missing_rate(data)
    if errors:
        print("❌ Validation failed:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("✅ Validation passed")

if __name__ == "__main__":
    main()
