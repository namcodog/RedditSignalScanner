#!/usr/bin/env python3
from __future__ import annotations

"""Spec 011 Stage 3 – Alias merging workflow.

This script serves three roles:

1. Given semantic candidates + the current lexicon, score alias suggestions
   with Jaro-Winkler + token cosine + layer/category consistency.
2. Render human friendly reports summarising which aliases should be reviewed.
3. Apply an approved alias map back into the semantic set (aliases array).

All paths/thresholds follow the stage-3 spec defaults but can be customised.
"""

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


LAYER_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}


@dataclass
class LexiconTerm:
    canonical: str
    layer: str
    category: str
    aliases: List[str]


@dataclass
class CandidateTerm:
    term: str
    layer: str
    category: str
    freq: int
    score: float


@dataclass
class AliasSuggestion:
    canonical: str
    alias: str
    target_layer: str
    target_category: str
    candidate_layer: str
    candidate_category: str
    jaro: float
    cosine: float
    context_bonus: float
    score: float
    freq: int


@dataclass
class AliasRow(AliasSuggestion):
    decision: str
    notes: str


ACCEPT_DECISIONS = {"accept", "accepted", "approve", "approved", "merge", "yes", "y", "keep"}


TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalise_layer(layer: str) -> str:
    key = str(layer or "").strip().upper()
    return key if key in LAYER_ORDER else ""


def _layer_idx(layer: str) -> int | None:
    norm = _normalise_layer(layer)
    return LAYER_ORDER.get(norm)


def _tokenise(text: str) -> List[str]:
    return [tok.lower() for tok in TOKEN_PATTERN.findall(text.lower()) if tok]


def _counts(text: str) -> Counter[str]:
    tokens = _tokenise(text)
    counts = Counter(tokens)
    compact = re.sub(r"\s+", "", text.lower())
    if len(compact) >= 2:
        for i in range(len(compact) - 1):
            counts[compact[i : i + 2]] += 1
    return counts


def _cosine_similarity(a: str, b: str) -> float:
    ca = _counts(a)
    cb = _counts(b)
    if not ca or not cb:
        return 0.0
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    if dot == 0:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in ca.values()))
    norm_b = math.sqrt(sum(v * v for v in cb.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _jaro_winkler(a: str, b: str) -> float:
    s1 = a.strip().lower()
    s2 = b.strip().lower()
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    max_dist = max(len1, len2) // 2 - 1
    match = 0
    hash1 = [0] * len1
    hash2 = [0] * len2

    for i in range(len1):
        start = max(0, i - max_dist)
        end = min(len2, i + max_dist + 1)
        for j in range(start, end):
            if hash2[j]:
                continue
            if s1[i] != s2[j]:
                continue
            hash1[i] = hash2[j] = 1
            match += 1
            break

    if match == 0:
        return 0.0

    t = 0
    point = 0
    for i in range(len1):
        if not hash1[i]:
            continue
        while not hash2[point]:
            point += 1
        if s1[i] != s2[point]:
            t += 1
        point += 1
    t /= 2

    jaro = (match / len1 + match / len2 + (match - t) / match) / 3.0

    # Winkler bonus for shared prefix (max 4 chars)
    prefix = 0
    for ch1, ch2 in zip(s1, s2):
        if ch1 == ch2:
            prefix += 1
        else:
            break
        if prefix == 4:
            break
    winkler = jaro + 0.1 * prefix * (1 - jaro)
    return float(max(0.0, min(1.0, winkler)))


def _freq_bonus(freq: int) -> float:
    if freq <= 0:
        return 0.0
    return min(0.03, math.log1p(freq) / 300.0)


def _context_bonus(candidate: CandidateTerm, target: LexiconTerm, layer_aware: bool) -> float:
    bonus = 0.0
    if layer_aware:
        cand_idx = _layer_idx(candidate.layer)
        tgt_idx = _layer_idx(target.layer)
        if cand_idx is not None and tgt_idx is not None:
            if cand_idx == tgt_idx:
                bonus += 0.05
            else:
                diff = abs(cand_idx - tgt_idx)
                if diff == 1:
                    bonus += 0.02
                else:
                    bonus -= 0.02 * diff
    if candidate.category and target.category:
        if candidate.category == target.category:
            bonus += 0.03
        else:
            bonus -= 0.01
    bonus += _freq_bonus(candidate.freq)
    return bonus


def _load_semantic_sets(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_lexicon_terms(path: Path) -> List[LexiconTerm]:
    data = _load_semantic_sets(path)
    out: List[LexiconTerm] = []
    for layer, categories in data.get("layers", {}).items():
        for category, arr in categories.items():
            if not isinstance(arr, list):
                continue
            for item in arr:
                canonical = str(item.get("canonical", "")).strip()
                if not canonical:
                    continue
                aliases = [str(a).strip() for a in item.get("aliases", []) if str(a).strip()]
                out.append(
                    LexiconTerm(
                        canonical=canonical,
                        layer=str(layer),
                        category=str(category),
                        aliases=aliases,
                    )
                )
    return out


def load_candidate_terms(path: Path, *, min_freq: int = 1) -> List[CandidateTerm]:
    rows: dict[str, CandidateTerm] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_term = row.get("canonical") or row.get("term") or row.get("candidate") or row.get("alias")
            if not raw_term:
                continue
            term = raw_term.strip()
            if not term:
                continue
            freq = _to_int(row.get("freq") or row.get("count"), 0)
            if freq < min_freq:
                continue
            score = _to_float(row.get("score") or row.get("weight"), 0.0)
            layer = row.get("layer") or row.get("layers") or ""
            category = row.get("category") or row.get("theme") or ""
            key = term.lower()
            existing = rows.get(key)
            if existing and existing.freq >= freq:
                continue
            rows[key] = CandidateTerm(term=term, layer=layer, category=category, freq=freq, score=score)
    return list(rows.values())


def compute_alias_candidates(
    *,
    lexicon_terms: Sequence[LexiconTerm],
    candidate_terms: Sequence[CandidateTerm],
    min_score: float,
    layer_aware: bool,
    top_k: int,
) -> List[AliasSuggestion]:
    suggestions: List[AliasSuggestion] = []
    if min_score <= 0:
        min_score = 0.0
    alias_blacklist = {t.canonical.lower(): True for t in lexicon_terms}
    for term in lexicon_terms:
        for alias in term.aliases:
            alias_blacklist[alias.lower()] = True

    for candidate in candidate_terms:
        alias_norm = candidate.term.lower()
        if alias_norm in alias_blacklist:
            continue
        for target in lexicon_terms:
            jaro = _jaro_winkler(candidate.term, target.canonical)
            cosine = _cosine_similarity(candidate.term, target.canonical)
            context_bonus = _context_bonus(candidate, target, layer_aware)
            combined = max(0.0, min(1.0, 0.7 * jaro + 0.3 * cosine + context_bonus))
            if combined < min_score:
                continue
            suggestions.append(
                AliasSuggestion(
                    canonical=target.canonical,
                    alias=candidate.term,
                    target_layer=target.layer,
                    target_category=target.category,
                    candidate_layer=candidate.layer,
                    candidate_category=candidate.category,
                    jaro=jaro,
                    cosine=cosine,
                    context_bonus=context_bonus,
                    score=combined,
                    freq=candidate.freq,
                )
            )

    if not suggestions:
        return []

    buckets: dict[str, List[AliasSuggestion]] = defaultdict(list)
    for sug in suggestions:
        buckets[sug.alias.lower()].append(sug)

    trimmed: List[AliasSuggestion] = []
    for alias, arr in buckets.items():
        arr.sort(key=lambda s: (s.score, s.freq), reverse=True)
        trimmed.extend(arr[: max(1, top_k)])

    trimmed.sort(key=lambda s: (s.score, s.freq), reverse=True)
    return trimmed


def write_alias_map(rows: Sequence[AliasSuggestion], path: Path) -> None:
    if not rows:
        path.write_text("canonical,alias,target_layer,target_category,candidate_layer,candidate_category,jaro,cosine,context_bonus,score,freq,decision,notes\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "canonical",
                "alias",
                "target_layer",
                "target_category",
                "candidate_layer",
                "candidate_category",
                "jaro",
                "cosine",
                "context_bonus",
                "score",
                "freq",
                "decision",
                "notes",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.canonical,
                    row.alias,
                    row.target_layer,
                    row.target_category,
                    row.candidate_layer,
                    row.candidate_category,
                    f"{row.jaro:.4f}",
                    f"{row.cosine:.4f}",
                    f"{row.context_bonus:.4f}",
                    f"{row.score:.4f}",
                    row.freq,
                    "pending",
                    "",
                ]
            )


def read_alias_map(path: Path) -> List[AliasRow]:
    rows: List[AliasRow] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = row.get("canonical", "").strip()
            alias = row.get("alias", "").strip()
            if not canonical or not alias:
                continue
            rows.append(
                AliasRow(
                    canonical=canonical,
                    alias=alias,
                    target_layer=row.get("target_layer", ""),
                    target_category=row.get("target_category", ""),
                    candidate_layer=row.get("candidate_layer", ""),
                    candidate_category=row.get("candidate_category", ""),
                    jaro=_to_float(row.get("jaro"), 0.0),
                    cosine=_to_float(row.get("cosine"), 0.0),
                    context_bonus=_to_float(row.get("context_bonus"), 0.0),
                    score=_to_float(row.get("score"), 0.0),
                    freq=_to_int(row.get("freq"), 0),
                    decision=row.get("decision", "").strip().lower(),
                    notes=row.get("notes", "").strip(),
                )
            )
    return rows


def apply_alias_rows_to_lexicon(
    data: dict,
    rows: Sequence[AliasRow],
    accept_decisions: set[str],
    *,
    auto_accept: bool = False,
) -> int:
    layers = data.setdefault("layers", {})
    applied = 0
    for row in rows:
        accepted = auto_accept or row.decision in accept_decisions
        if not accepted:
            continue
        target_layer = row.target_layer or row.candidate_layer
        target_category = row.target_category or row.candidate_category
        layer_block = layers.get(target_layer)
        if not isinstance(layer_block, dict):
            continue
        category_arr = layer_block.get(target_category)
        if not isinstance(category_arr, list):
            continue
        target_entry = None
        for item in category_arr:
            if str(item.get("canonical", "")) == row.canonical:
                target_entry = item
                break
        if target_entry is None:
            continue
        aliases = target_entry.setdefault("aliases", [])
        alias_lower = row.alias.lower()
        if alias_lower == row.canonical.lower():
            continue
        if any(str(existing).lower() == alias_lower for existing in aliases):
            continue
        aliases.append(row.alias)
        applied += 1
    return applied


def generate_alias_report(rows: Sequence[AliasRow], output_path: Path) -> None:
    total = len(rows)
    accepted = sum(1 for r in rows if r.decision in ACCEPT_DECISIONS)
    content = [
        "# Alias Suggestions Report",
        "",
        f"Total suggestions: {total}",
        f"Approved (marked): {accepted}",
        "",
    ]
    current_canonical = None
    for row in rows:
        header = f"## {row.canonical} ({row.target_layer or row.candidate_layer}/{row.target_category or row.candidate_category})"
        if header != current_canonical:
            content.append(header)
            content.append("| alias | score | jaro | cosine | freq | ctx | decision | notes |")
            content.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            current_canonical = header
        ctx = (
            f"{row.candidate_layer or '?'}→{row.target_layer or '?'} / "
            f"{row.candidate_category or '?'}→{row.target_category or '?'}"
        )
        content.append(
            "| {alias} | {score:.3f} | {jaro:.3f} | {cosine:.3f} | {freq} | {ctx} | {decision} | {notes} |".format(
                alias=row.alias,
                score=row.score,
                jaro=row.jaro,
                cosine=row.cosine,
                freq=row.freq,
                ctx=ctx,
                decision=row.decision or "pending",
                notes=row.notes or "",
            )
        )
    output_path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Alias merge helper")
    parser.add_argument("--candidates", type=Path, help="CSV with semantic candidates")
    parser.add_argument("--lexicon", type=Path, help="Semantic lexicon JSON/YAML")
    parser.add_argument("--output", type=Path, help="Output path (alias map or updated lexicon)")
    parser.add_argument("--alias-map", type=Path, help="Existing alias map CSV")
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--min-freq", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--layer-aware", action="store_true")
    parser.add_argument("--generate-report", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--auto-approve", action="store_true", help="Apply all rows without checking decision column")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.generate_report:
        if not args.alias_map or not args.output:
            raise SystemExit("--alias-map and --output are required for --generate-report")
        rows = read_alias_map(args.alias_map)
        rows.sort(key=lambda r: (r.canonical, -r.score))
        generate_alias_report(rows, args.output)
        print(f"Report written to {args.output}")
        return

    if args.apply:
        if not args.alias_map or not args.lexicon or not args.output:
            raise SystemExit("--alias-map, --lexicon and --output are required for --apply")
        data = _load_semantic_sets(args.lexicon)
        rows = read_alias_map(args.alias_map)
        applied = apply_alias_rows_to_lexicon(data, rows, ACCEPT_DECISIONS, auto_accept=args.auto_approve)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Applied {applied} alias entries → {args.output}")
        return

    # Default: compute alias suggestions
    if not args.candidates or not args.lexicon or not args.output:
        raise SystemExit("--candidates, --lexicon and --output are required to compute alias suggestions")
    lex_terms = load_lexicon_terms(args.lexicon)
    candidates = load_candidate_terms(args.candidates, min_freq=args.min_freq)
    suggestions = compute_alias_candidates(
        lexicon_terms=lex_terms,
        candidate_terms=candidates,
        min_score=args.threshold,
        layer_aware=args.layer_aware,
        top_k=max(1, args.top_k),
    )
    write_alias_map(suggestions, args.output)
    print(f"Alias suggestions: {len(suggestions)} rows → {args.output}")


if __name__ == "__main__":
    main()
