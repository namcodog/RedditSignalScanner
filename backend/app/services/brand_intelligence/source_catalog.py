from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.services.brand_intelligence.source_catalog_outputs import (
    render_brand_source_catalog_markdown as render_brand_source_catalog_markdown,
)
from app.services.brand_intelligence.source_catalog_outputs import (
    write_brand_source_catalog_outputs as write_brand_source_catalog_outputs,
)
from app.services.semantic.unified_lexicon import UnifiedLexicon

CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
_PRIORITY = {"candidate": 1, "seed": 2, "approved": 3, "rejected": 4}

__all__ = [
    "BrandSourceCatalog",
    "BrandSourceEntry",
    "catalog_from_lexicon",
    "load_brand_source_catalog",
    "normalize_brand_key",
    "render_brand_source_catalog_markdown",
    "write_brand_source_catalog_outputs",
]


@dataclass(frozen=True)
class BrandSourceEntry:
    canonical_name: str
    lifecycle: str
    aliases: tuple[str, ...]
    sources: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "lifecycle": self.lifecycle,
            "aliases": list(self.aliases),
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class BrandSourceCatalog:
    entries: tuple[BrandSourceEntry, ...]
    summary: dict[str, object]

    def get(self, name: str) -> BrandSourceEntry:
        key = normalize_brand_key(name)
        for entry in self.entries:
            if normalize_brand_key(entry.canonical_name) == key:
                return entry
        raise KeyError(name)

    def to_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "entries": [entry.to_payload() for entry in self.entries],
        }


def load_brand_source_catalog(config_root: Path = CONFIG_ROOT) -> BrandSourceCatalog:
    from app.services.brand_intelligence.source_catalog_loaders import (
        _load_archive,
        _load_noise_text,
        _load_noise_yaml,
    )

    builder = _CatalogBuilder()
    _load_unified(builder, config_root / "semantic_sets" / "unified_lexicon.yml")
    _load_base_csv(builder, config_root / "entity_dictionary" / "brands_base.csv")
    _load_archive(builder, config_root / "semantic_sets" / "archive")
    _load_noise_yaml(builder, config_root / "brand_noise.yaml")
    _load_noise_text(builder, config_root / "nlp" / "stopwords" / "hard_neg_brands.txt")
    return builder.build()


def catalog_from_lexicon(lexicon: UnifiedLexicon) -> BrandSourceCatalog:
    builder = _CatalogBuilder()
    for term in lexicon.get_brands():
        builder.add(
            term.canonical,
            "approved",
            "lexicon",
            aliases=term.aliases,
            source_group="unified_lexicon",
        )
    return builder.build()


def normalize_brand_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


@dataclass
class _MutableEntry:
    canonical_name: str
    lifecycle: str
    aliases: set[str]
    sources: set[str]


class _CatalogBuilder:
    def __init__(self) -> None:
        self._entries: dict[str, _MutableEntry] = {}
        self._source_counts: dict[str, int] = {}
        self._duplicate_keys: set[str] = set()
        self._noise_overlaps: set[str] = set()

    def add(
        self,
        name: str,
        lifecycle: str,
        source: str,
        *,
        aliases: Iterable[str] = (),
        source_group: str,
    ) -> None:
        clean = name.strip()
        if not clean:
            return
        key = normalize_brand_key(clean)
        self._source_counts[source_group] = self._source_counts.get(source_group, 0) + 1
        current = self._entries.get(key)
        if current is None:
            self._entries[key] = _MutableEntry(clean, lifecycle, set(aliases), {source})
            return
        self._duplicate_keys.add(key)
        if lifecycle == "rejected" and current.lifecycle != "rejected":
            self._noise_overlaps.add(key)
        if _PRIORITY[lifecycle] > _PRIORITY[current.lifecycle]:
            current.canonical_name = clean
            current.lifecycle = lifecycle
        current.aliases.update(alias for alias in aliases if alias.strip())
        current.sources.add(source)

    def build(self) -> BrandSourceCatalog:
        entries = tuple(
            BrandSourceEntry(
                canonical_name=item.canonical_name,
                lifecycle=item.lifecycle,
                aliases=tuple(sorted(item.aliases, key=str.lower)),
                sources=tuple(sorted(item.sources)),
            )
            for item in sorted(
                self._entries.values(),
                key=lambda row: normalize_brand_key(row.canonical_name),
            )
        )
        lifecycle_counts: dict[str, int] = {}
        for entry in entries:
            lifecycle_counts[entry.lifecycle] = (
                lifecycle_counts.get(entry.lifecycle, 0) + 1
            )
        return BrandSourceCatalog(
            entries=entries,
            summary={
                "total_entries": len(entries),
                "source_counts": dict(sorted(self._source_counts.items())),
                "lifecycle_counts": lifecycle_counts,
                "duplicate_keys": sorted(self._duplicate_keys),
                "noise_overlaps": sorted(self._noise_overlaps),
            },
        )


def _load_unified(builder: _CatalogBuilder, path: Path) -> None:
    lexicon = UnifiedLexicon(path)
    for term in lexicon.get_brands():
        builder.add(
            term.canonical,
            "approved",
            str(path),
            aliases=term.aliases,
            source_group="unified_lexicon",
        )


def _load_base_csv(builder: _CatalogBuilder, path: Path) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("category") == "brands":
                builder.add(
                    row.get("canonical") or "",
                    "seed",
                    str(path),
                    source_group="brands_base",
                )
