from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import cast

import yaml

from app.services.brand_intelligence.source_catalog import _CatalogBuilder


def _load_archive(builder: _CatalogBuilder, archive_dir: Path) -> None:
    if not archive_dir.exists():
        return
    for path in sorted(archive_dir.glob("brands_*.yml")):
        payload = _load_mapping(path)
        category = str(payload.get("category") or path.stem)
        brands = payload.get("brands")
        if not isinstance(brands, list):
            continue
        for brand in brands:
            if isinstance(brand, str):
                builder.add(
                    brand,
                    "candidate",
                    f"archive/{path.name}:{category}",
                    source_group="archive",
                )


def _load_noise_yaml(builder: _CatalogBuilder, path: Path) -> None:
    if not path.exists():
        return
    payload: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for value in _iter_strings(payload):
        builder.add(value, "rejected", str(path), source_group="noise")


def _load_noise_text(builder: _CatalogBuilder, path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            builder.add(value, "rejected", str(path), source_group="noise")


def _load_mapping(path: Path) -> Mapping[str, object]:
    payload: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {}
    return cast(Mapping[str, object], payload)


def _iter_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
