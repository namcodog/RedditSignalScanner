from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping

from app.services.brand_intelligence.brand_digest_outputs import (
    render_brand_digest_markdown as render_brand_digest_markdown,
)
from app.services.brand_intelligence.brand_digest_outputs import (
    write_brand_digest_outputs as write_brand_digest_outputs,
)
from app.services.brand_intelligence.models import (
    BrandCandidate,
    BrandDigestReport,
    BrandEvidence,
)
from app.services.brand_intelligence.source_catalog import (
    BrandSourceCatalog,
    catalog_from_lexicon,
    load_brand_source_catalog,
)
from app.services.semantic.unified_lexicon import SemanticTerm, UnifiedLexicon

DEFAULT_LEXICON_PATH = (
    Path(__file__).resolve().parents[3]
    / "config"
    / "semantic_sets"
    / "unified_lexicon.yml"
)

__all__ = [
    "build_brand_digest",
    "build_brand_digest_from_catalog",
    "load_default_catalog",
    "load_default_lexicon",
    "render_brand_digest_markdown",
    "write_brand_digest_outputs",
]


def load_default_lexicon() -> UnifiedLexicon:
    return UnifiedLexicon(DEFAULT_LEXICON_PATH)


def load_default_catalog() -> BrandSourceCatalog:
    return load_brand_source_catalog()


def build_brand_digest(
    cards: Iterable[Mapping[str, object]],
    *,
    lexicon: UnifiedLexicon,
    report_date: str,
) -> BrandDigestReport:
    return build_brand_digest_from_catalog(
        cards,
        catalog=catalog_from_lexicon(lexicon),
        report_date=report_date,
    )


def build_brand_digest_from_catalog(
    cards: Iterable[Mapping[str, object]],
    *,
    catalog: BrandSourceCatalog,
    report_date: str,
) -> BrandDigestReport:
    card_list = list(cards)
    patterns = _catalog_patterns(catalog)
    brands: dict[str, BrandCandidate] = {}
    seen: set[tuple[str, str, str, str, str]] = set()

    for card in card_list:
        card_id = _as_text(card.get("card_id")) or "unknown-card"
        observed_at = _as_text(card.get("published_at")) or report_date
        for source, text, community, permalink in _iter_card_evidence_text(card):
            for canonical, matched, lifecycle, pattern in patterns:
                if not pattern.search(text):
                    continue
                key = (canonical, matched.lower(), card_id, source, text)
                if key in seen:
                    continue
                seen.add(key)
                candidate = brands.setdefault(
                    canonical,
                    BrandCandidate(canonical, source_lifecycle=lifecycle),
                )
                candidate.matched_terms.add(matched)
                candidate.communities.add(community)
                candidate.evidence.append(
                    BrandEvidence(
                        card_id=card_id,
                        community=community,
                        source=source,
                        source_text=text,
                        observed_at=observed_at,
                        permalink=permalink,
                    )
                )

    return BrandDigestReport(
        report_date=report_date,
        card_count=len(card_list),
        brands=tuple(
            sorted(
                brands.values(),
                key=lambda item: (-len(item.evidence), item.canonical_name.lower()),
            )
        ),
    )


def _catalog_patterns(
    catalog: BrandSourceCatalog,
) -> tuple[tuple[str, str, str, re.Pattern[str]], ...]:
    items: list[tuple[str, str, str, re.Pattern[str]]] = []
    for entry in catalog.entries:
        if entry.lifecycle == "rejected":
            continue
        for matched in [entry.canonical_name, *entry.aliases]:
            text = matched.strip()
            if not text:
                continue
            items.append(
                (
                    entry.canonical_name,
                    text,
                    entry.lifecycle,
                    re.compile(rf"\b{re.escape(text)}\b", re.IGNORECASE),
                )
            )
    return tuple(items)


def _brand_patterns(
    terms: Iterable[SemanticTerm],
) -> tuple[tuple[str, str, re.Pattern[str]], ...]:
    items: list[tuple[str, str, re.Pattern[str]]] = []
    for term in terms:
        for matched in [term.canonical, *term.aliases]:
            text = matched.strip()
            if not text:
                continue
            items.append(
                (
                    term.canonical,
                    text,
                    re.compile(rf"\b{re.escape(text)}\b", re.IGNORECASE),
                )
            )
    return tuple(items)


def _iter_card_evidence_text(
    card: Mapping[str, object],
) -> Iterable[tuple[str, str, str, str | None]]:
    community = _as_text(card.get("top_community")) or "unknown-community"
    for key in ("title", "summary_line", "audience", "why_now", "why_now_reason"):
        text = _as_text(card.get(key))
        if text:
            yield key, text, community, _as_text(card.get("source_link"))
    for text in _iter_nested_text(card.get("detail")):
        yield "detail", text, community, _as_text(card.get("source_link"))
    quotes = card.get("quotes")
    if isinstance(quotes, list):
        for quote in quotes:
            if not isinstance(quote, dict):
                continue
            text = _as_text(quote.get("text"))
            if text:
                yield (
                    "quote",
                    text,
                    _as_text(quote.get("community")) or community,
                    _as_text(quote.get("permalink")),
                )


def _iter_nested_text(value: object) -> Iterable[str]:
    if isinstance(value, str):
        text = value.strip()
        if text:
            yield text
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_nested_text(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_nested_text(item)


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
