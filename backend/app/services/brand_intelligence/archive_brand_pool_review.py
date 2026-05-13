from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, cast

import yaml

CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"


@dataclass(frozen=True)
class ArchiveBrandPoolItem:
    canonical_name: str
    review_status: str
    domains: tuple[str, ...]
    source_files: tuple[str, ...]
    flags: tuple[str, ...]
    raw_count: int

    def to_payload(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "review_status": self.review_status,
            "domains": list(self.domains),
            "source_files": list(self.source_files),
            "flags": list(self.flags),
            "raw_count": self.raw_count,
        }


@dataclass(frozen=True)
class ArchiveBrandPoolReport:
    items: tuple[ArchiveBrandPoolItem, ...]
    raw_rows: int

    @property
    def summary(self) -> dict[str, object]:
        domain_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        for item in self.items:
            status_counts[item.review_status] = (
                status_counts.get(item.review_status, 0) + 1
            )
            for domain in item.domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        return {
            "source": "user_vetted_archive",
            "db_writes": False,
            "raw_rows": self.raw_rows,
            "brand_count": len(self.items),
            "duplicate_rows": self.raw_rows - len(self.items),
            "status_counts": dict(sorted(status_counts.items())),
            "domain_counts": dict(sorted(domain_counts.items())),
        }

    def to_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "items": [item.to_payload() for item in self.items],
        }


def build_archive_brand_pool_review(
    config_root: Path = CONFIG_ROOT,
) -> ArchiveBrandPoolReport:
    labels = _load_domain_labels(config_root / "brand_domain_labels.json")
    noise_terms = _load_noise_terms(config_root)
    rows = list(_iter_archive_rows(config_root / "semantic_sets" / "archive", labels))
    grouped: dict[str, _MutableArchiveBrand] = {}
    for name, domain, source_file in rows:
        key = _normalize(name)
        current = grouped.get(key)
        if current is None:
            grouped[key] = _MutableArchiveBrand(
                name.strip(), {domain}, {source_file}, 1
            )
            continue
        current.domains.add(domain)
        current.source_files.add(source_file)
        current.raw_count += 1
    items = tuple(
        _to_item(row, noise_terms)
        for row in sorted(grouped.values(), key=lambda item: _normalize(item.name))
    )
    return ArchiveBrandPoolReport(items=items, raw_rows=len(rows))


@dataclass
class _MutableArchiveBrand:
    name: str
    domains: set[str]
    source_files: set[str]
    raw_count: int


def _to_item(
    row: _MutableArchiveBrand, noise_terms: frozenset[str]
) -> ArchiveBrandPoolItem:
    flags = ("noise_overlap",) if _normalize(row.name) in noise_terms else ()
    return ArchiveBrandPoolItem(
        canonical_name=row.name,
        review_status="needs_review" if flags else "ready_for_review",
        domains=tuple(sorted(row.domains)),
        source_files=tuple(sorted(row.source_files)),
        flags=flags,
        raw_count=row.raw_count,
    )


def _iter_archive_rows(
    archive_dir: Path,
    labels: Mapping[str, str],
) -> Iterable[tuple[str, str, str]]:
    for path in sorted(archive_dir.glob("brands_*.yml")):
        payload = _load_mapping(path)
        category = str(payload.get("category") or path.stem)
        domain = labels.get(category, category)
        brands = payload.get("brands")
        if not isinstance(brands, list):
            continue
        for brand in brands:
            if isinstance(brand, str) and brand.strip():
                yield brand, domain, path.name


def _load_domain_labels(path: Path) -> Mapping[str, str]:
    if not path.exists():
        return {}
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def _load_noise_terms(config_root: Path) -> frozenset[str]:
    terms: set[str] = set()
    for value in _iter_noise_yaml(config_root / "brand_noise.yaml"):
        terms.add(_normalize(value))
    path = config_root / "nlp" / "stopwords" / "hard_neg_brands.txt"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if value and not value.startswith("#"):
                terms.add(_normalize(value))
    return frozenset(terms)


def _iter_noise_yaml(path: Path) -> Iterable[str]:
    if not path.exists():
        return ()
    payload: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _iter_strings(payload)


def _iter_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)


def _load_mapping(path: Path) -> Mapping[str, object]:
    payload: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {}
    return cast(Mapping[str, object], payload)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
