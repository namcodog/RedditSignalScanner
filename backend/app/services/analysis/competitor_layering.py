"""
Utilities for tagging competitors into layered categories and summarising them.

Specification reference: Spec010 P0 - 竞品分层标签（workspace / analytics / summary）
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Iterable, Mapping, MutableMapping, Sequence

import yaml


@dataclass(frozen=True)
class LayerDefinition:
    key: str
    label: str
    aliases: set[str]


@dataclass(frozen=True)
class CompetitorLayerConfig:
    default_layer: str
    layers: tuple[LayerDefinition, ...]

    def find_layer(self, name: str) -> LayerDefinition | None:
        lowered = name.lower()
        substring_matches: list[tuple[int, LayerDefinition]] = []
        for layer in self.layers:
            for alias in layer.aliases:
                if lowered == alias:
                    return layer
                if alias in lowered or lowered in alias:
                    substring_matches.append((len(alias), layer))
        if substring_matches:
            substring_matches.sort(key=lambda item: item[0], reverse=True)
            return substring_matches[0][1]
        return None

    def layer_by_key(self, key: str) -> LayerDefinition | None:
        for layer in self.layers:
            if layer.key == key:
                return layer
        return None


class CompetitorLayerLoader:
    """Load competitor layer configuration from YAML with thread-safe caching."""

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path is None:
            base = Path(__file__).resolve()
            resolved: Path | None = None
            for parent in base.parents:
                candidate = parent / "config" / "entity_dictionary" / "competitor_layers.yml"
                if candidate.exists():
                    resolved = candidate
                    break
            if resolved is None:
                resolved = Path.cwd() / "config" / "entity_dictionary" / "competitor_layers.yml"
            self._path = resolved
        else:
            self._path = config_path
        self._lock = Lock()
        self._cached: CompetitorLayerConfig | None = None
        self._mtime: float | None = None

    def load(self) -> CompetitorLayerConfig:
        with self._lock:
            mtime = self._path.stat().st_mtime
            if self._cached is not None and mtime == self._mtime:
                return self._cached

            payload = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
            default_layer = str(payload.get("default_layer") or "summary").strip().lower()
            layers_payload = payload.get("layers") or {}
            layer_defs: list[LayerDefinition] = []
            for key, entry in layers_payload.items():
                aliases = entry.get("aliases") or []
                label = str(entry.get("label") or key.title())
                alias_set = {str(alias).lower() for alias in aliases if str(alias).strip()}
                layer_defs.append(LayerDefinition(key=str(key).lower(), label=label, aliases=alias_set))
            layer_defs.sort(key=lambda item: item.key)
            config = CompetitorLayerConfig(default_layer=default_layer, layers=tuple(layer_defs))

            self._cached = config
            self._mtime = mtime
            return config


_CONFIG_LOADER = CompetitorLayerLoader()


def assign_competitor_layers(
    competitors: Sequence[MutableMapping[str, object]] | Sequence[Mapping[str, object]],
) -> list[dict]:
    """
    Mutate/return competitor payloads with layer annotations.

    Args:
        competitors: Sequence of competitor dictionaries.

    Returns:
        New list of competitor dictionaries with `layer` populated.
    """
    config = _CONFIG_LOADER.load()
    annotated: list[dict] = []
    for item in competitors:
        mutable = dict(item)
        name = str(mutable.get("name") or "").strip()
        layer = str(mutable.get("layer") or "").strip().lower()
        if name:
            matched = config.find_layer(name)
            if matched:
                layer = matched.key
        if not layer:
            layer = config.default_layer
        mutable["layer"] = layer
        annotated.append(mutable)
    return annotated


def build_layer_summary(
    competitors: Sequence[Mapping[str, object]],
) -> list[dict]:
    """
    Build per-layer summary including top competitors and threat hints.
    """
    config = _CONFIG_LOADER.load()
    grouped: dict[str, list[Mapping[str, object]]] = {
        layer.key: [] for layer in config.layers
    }
    grouped.setdefault(config.default_layer, [])

    for comp in competitors:
        layer = str(comp.get("layer") or "").strip().lower()
        if not layer:
            match = config.find_layer(str(comp.get("name") or ""))
            layer = match.key if match else config.default_layer
        grouped.setdefault(layer, []).append(comp)

    summaries: list[dict] = []
    for layer_def in config.layers:
        items = grouped.get(layer_def.key) or []
        if not items:
            continue
        sorted_items = sorted(
            items,
            key=lambda item: int(item.get("mentions") or 0),
            reverse=True,
        )
        top_three = [
            {
                "name": str(item.get("name") or ""),
                "mentions": int(item.get("mentions") or 0),
                "sentiment": item.get("sentiment"),
            }
            for item in sorted_items[:3]
        ]
        threats = _select_threat(sorted_items)
        summaries.append(
            {
                "layer": layer_def.key,
                "label": layer_def.label,
                "top_competitors": top_three,
                "threats": threats,
            }
        )

    # include default layer if it is not already covered
    if config.default_layer not in {entry["layer"] for entry in summaries}:
        items = grouped.get(config.default_layer) or []
        if items:
            sorted_items = sorted(
                items,
                key=lambda item: int(item.get("mentions") or 0),
                reverse=True,
            )
            summaries.append(
                {
                    "layer": config.default_layer,
                    "label": config.default_layer.title(),
                    "top_competitors": [
                        {
                            "name": str(item.get("name") or ""),
                            "mentions": int(item.get("mentions") or 0),
                            "sentiment": item.get("sentiment"),
                        }
                        for item in sorted_items[:3]
                    ],
                    "threats": _select_threat(sorted_items),
                }
            )

    return summaries


def _select_threat(items: Iterable[Mapping[str, object]]) -> str:
    for item in items:
        strengths = item.get("strengths") or []
        if strengths and isinstance(strengths, Sequence) and not isinstance(strengths, (str, bytes)):
            primary = str(strengths[0]).strip()
            if primary:
                return primary
        weaknesses = item.get("weaknesses") or []
        if weaknesses and isinstance(weaknesses, Sequence) and not isinstance(weaknesses, (str, bytes)):
            primary = str(weaknesses[0]).strip()
            if primary:
                return primary
    return ""


__all__ = ["assign_competitor_layers", "build_layer_summary", "CompetitorLayerLoader"]
