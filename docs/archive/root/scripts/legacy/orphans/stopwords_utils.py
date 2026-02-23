from __future__ import annotations

import re
from pathlib import Path
from typing import List, Set, Tuple


def _read_lines(p: Path) -> List[str]:
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]


def load_stopwords(base_dir: Path) -> Tuple[Set[str], Set[str], Set[str], Set[str], List[re.Pattern[str]], Set[str]]:
    """
    Returns:
      token_stops: set of single tokens to drop
      phrase_stops: set of multi-word phrases to drop
      reddit_stops: Reddit-specific tokens
      ecommerce_tokens: domain tokens (usually only for candidate extraction)
      regex_stops: compiled regex patterns to drop
      keep_tokens: tokens that must NOT be dropped
    """
    token_stops: Set[str] = set()
    phrase_stops: Set[str] = set()
    reddit_stops: Set[str] = set()
    ecommerce_tokens: Set[str] = set()
    keep_tokens: Set[str] = set()
    regex_stops: List[re.Pattern[str]] = []

    token_stops.update(_read_lines(base_dir / "global.txt"))
    reddit_stops.update(_read_lines(base_dir / "reddit.txt"))
    ecommerce_tokens.update(_read_lines(base_dir / "ecommerce.txt"))
    phrase_stops.update(_read_lines(base_dir / "phrases.txt"))
    keep_tokens.update(_read_lines(base_dir / "keep.txt"))
    for pat in _read_lines(base_dir / "regex.txt"):
        try:
            regex_stops.append(re.compile(pat))
        except re.error:
            continue

    return token_stops, phrase_stops, reddit_stops, ecommerce_tokens, regex_stops, keep_tokens

