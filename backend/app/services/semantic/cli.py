from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from app.services.semantic.unified_lexicon import UnifiedLexicon
from app.services.semantic.candidate_extractor import CandidateExtractor


def _cmd_stats(lex: UnifiedLexicon) -> int:
    brands = lex.get_brands()
    feats = lex.get_features()
    pains = lex.get_pain_points()
    print(f"brands={len(brands)} features={len(feats)} pain_points={len(pains)}")
    return 0


def _cmd_validate(lex_path: Path) -> int:
    try:
        UnifiedLexicon(lex_path)
        print("OK")
        return 0
    except Exception as exc:  # pragma: no cover - safety path
        print(f"ERROR: {exc}")
        return 1


def _cmd_search(lex: UnifiedLexicon, query: str) -> int:
    q = (query or "").strip().lower()
    found = [t.canonical for t in (lex.get_brands() + lex.get_features() + lex.get_pain_points()) if q and q in t.canonical.lower()]
    for name in sorted(found):
        print(name)
    return 0


def _cmd_candidates_from_file(lex: UnifiedLexicon, txt_path: Path) -> int:
    texts: list[str] = []
    if txt_path.exists():
        texts = [line.rstrip("\n") for line in txt_path.read_text(encoding="utf-8").splitlines()]
    ext = CandidateExtractor(lex, min_frequency=2)
    rows = ext.extract_from_texts(texts)
    for r in rows:
        print(f"{r.canonical},{r.frequency},{r.suggested_layer},{r.confidence}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Unified Lexicon CLI")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/unified_lexicon.yml"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats")
    val = sub.add_parser("validate")
    val.add_argument("--file", type=Path, default=None)

    sch = sub.add_parser("search")
    sch.add_argument("q", type=str)

    cfile = sub.add_parser("candidates-file")
    cfile.add_argument("--input", type=Path, required=True)

    args = ap.parse_args(argv)
    lex_path = args.lexicon if args.lexicon else Path("backend/config/semantic_sets/unified_lexicon.yml")
    if args.cmd == "validate":
        return _cmd_validate(args.file or lex_path)

    lex = UnifiedLexicon(lex_path)
    if args.cmd == "stats":
        return _cmd_stats(lex)
    if args.cmd == "search":
        return _cmd_search(lex, args.q)
    if args.cmd == "candidates-file":
        return _cmd_candidates_from_file(lex, args.input)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

