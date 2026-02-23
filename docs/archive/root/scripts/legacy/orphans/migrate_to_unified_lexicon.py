from __future__ import annotations

"""
Unified lexicon migration tool.

Goal: produce a single unified YAML lexicon by merging a base file with
optional extras (from code constants or a small YAML snippet). This is a
pragmatic implementation for Week 4-5 tooling; it avoids over-engineering.
"""

import argparse
from pathlib import Path
from typing import Dict, List

import yaml


def _load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _append_list_unique(dst: List[str], items: List[str]) -> None:
    seen = {x.lower() for x in dst}
    for it in items:
        v = str(it).strip()
        if v and v.lower() not in seen:
            dst.append(v)
            seen.add(v.lower())


def _extract_from_code() -> dict:
    """Collect small extras from existing code constants (best effort)."""
    brands: List[str] = []
    features: List[str] = []
    pains: List[str] = []
    try:
        # BRAND_PATTERNS in comments_labeling
        from app.services.labeling.comments_labeling import BRAND_PATTERNS  # type: ignore
        brands += [name for name, _ in BRAND_PATTERNS]
    except Exception:
        pass
    try:
        from app.services.text_classifier import PRICE_KWS, SUBS_KWS, CONTENT_KWS, INSTALL_KWS, ECO_KWS  # type: ignore
        pains += list(PRICE_KWS) + list(SUBS_KWS)
        features += list(CONTENT_KWS) + list(INSTALL_KWS)
        brands += list(ECO_KWS)  # loosely map ecosystem to L1-ish
    except Exception:
        pass
    return {"brands": brands, "features": features, "pain_points": pains}


def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Migrate to unified lexicon YAML")
    ap.add_argument("--input", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.2_calibrated.yml"))
    ap.add_argument("--output", type=Path, default=Path("backend/config/semantic_sets/unified_lexicon.yml"))
    ap.add_argument("--merge-from", type=Path, default=None, help="Optional YAML snippet to merge (themes/unified)")
    ap.add_argument("--include-hardcoded", action="store_true", help="Merge from code constants (brands/features/pain)")
    args = ap.parse_args(argv)

    base = _load_yaml(args.input)
    themes = dict(base.get("themes") or {})
    # choose an existing theme as seed if present, else create unified
    if themes:
        # take first theme
        theme_name = next(iter(themes.keys()))
        seed = dict(themes.get(theme_name) or {})
    else:
        seed = {"brands": [], "features": [], "pain_points": [], "aliases": {}, "exclude": [], "weights": {"brands": 1.5, "features": 1.0, "pain_points": 1.2}}

    # Normalize base lists
    for key in ("brands", "features", "pain_points"):
        seed[key] = list(seed.get(key) or [])

    # Merge external snippet
    if args.merge_from:
        extra = _load_yaml(args.merge_from)
        ext_themes = dict(extra.get("themes") or {})
        ext = ext_themes.get("unified") or next(iter(ext_themes.values()), {})
        for key in ("brands", "features", "pain_points"):
            _append_list_unique(seed[key], list(ext.get(key) or []))

    # Merge from code constants
    if args.include_hardcoded:
        extras = _extract_from_code()
        for key in ("brands", "features", "pain_points"):
            _append_list_unique(seed[key], list(extras.get(key) or []))

    unified = {"themes": {"unified": seed}}
    out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(unified, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Wrote unified lexicon to {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())

