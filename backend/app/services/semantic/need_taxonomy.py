from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

import yaml
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.interfaces.semantic_provider import SemanticLoadStrategy

_DEFAULT_CONFIG_PATH = Path("backend/config/need_taxonomy.yaml")

_DB_RULE_TYPES = (
    "need_keyword",
    "need_intent_phrase",
    "need_noise",
)


@dataclass(frozen=True)
class NeedTaxonomy:
    categories: list[str]
    intent_phrases: dict[str, list[str]]
    need_keywords: dict[str, list[str]]
    noise_keywords: set[str]


class NeedTaxonomyLoader:
    def __init__(
        self,
        config_path: Path | None = None,
        *,
        strategy: SemanticLoadStrategy = SemanticLoadStrategy.DB_YAML_FALLBACK,
    ) -> None:
        self._path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._strategy = strategy
        self._cache: NeedTaxonomy | None = None
        self._mtime: float | None = None
        self._lock = Lock()
        self._engine = None
        if strategy != SemanticLoadStrategy.YAML_ONLY:
            try:
                settings = get_settings()
                db_url = settings.database_url.replace("asyncpg", "psycopg")
                self._engine = create_engine(db_url, future=True)
            except Exception:
                self._engine = None

    def load(self) -> NeedTaxonomy:
        with self._lock:
            current_mtime = self._path.stat().st_mtime if self._path.exists() else None
            if self._cache is not None and current_mtime == self._mtime:
                return self._cache

            yaml_payload = self._load_yaml_raw()
            raw_payload = dict(yaml_payload)

            if self._strategy != SemanticLoadStrategy.YAML_ONLY:
                db_payload = self._load_db_raw()
                raw_payload = self._merge_raw(yaml_payload, db_payload)

            taxonomy = self._build_taxonomy(raw_payload)
            self._cache = taxonomy
            self._mtime = current_mtime
            return taxonomy

    def _load_yaml_raw(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            payload = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
            if isinstance(payload, dict):
                return payload
        except Exception:
            return {}
        return {}

    def _load_db_raw(self) -> dict[str, Any]:
        if self._engine is None:
            return {}
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text(
                        """
                        SELECT term, rule_type, meta
                        FROM semantic_rules
                        WHERE is_active = true
                          AND rule_type = ANY(:types)
                        """
                    ),
                    {"types": list(_DB_RULE_TYPES)},
                ).mappings().all()
        except Exception:
            return {}

        data: dict[str, Any] = {
            "intent_phrases": {},
            "need_keywords": {},
            "noise_keywords": [],
        }

        def _parse_meta(raw: Any) -> Mapping[str, Any]:
            if raw is None:
                return {}
            if isinstance(raw, Mapping):
                return raw
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, Mapping):
                        return parsed
                except Exception:
                    return {}
            return {}

        for row in rows:
            rule_type = str(row.get("rule_type") or "").strip().lower()
            term = str(row.get("term") or "").strip().lower()
            if not term:
                continue
            meta = _parse_meta(row.get("meta"))
            category = str(meta.get("category") or "").strip()
            order = meta.get("order")
            order_val = int(order) if isinstance(order, int) or str(order).isdigit() else None

            if rule_type == "need_keyword":
                if not category:
                    continue
                entry = data["need_keywords"].setdefault(category, [])
                entry.append((term, order_val))
            elif rule_type == "need_intent_phrase":
                if not category:
                    continue
                entry = data["intent_phrases"].setdefault(category, [])
                entry.append((term, order_val))
            elif rule_type == "need_noise":
                data["noise_keywords"].append(term)

        return data

    @staticmethod
    def _merge_raw(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        if not override:
            return dict(base)
        merged = dict(base)
        for key in ("intent_phrases", "need_keywords"):
            override_val = override.get(key) or {}
            base_val = merged.get(key) or {}
            if override_val:
                merged_val = dict(base_val)
                for cat, terms in override_val.items():
                    merged_val[cat] = terms
                merged[key] = merged_val
        override_noise = override.get("noise_keywords") or []
        if override_noise:
            merged["noise_keywords"] = override_noise
        return merged

    @staticmethod
    def _sorted_terms(items: list[tuple[str, int | None]]) -> list[str]:
        items_list = list(items)
        if not items_list:
            return []
        has_order = any(order is not None for _, order in items_list)
        if has_order:
            items_list.sort(key=lambda x: ((x[1] if x[1] is not None else 1_000_000), x[0]))
        else:
            items_list.sort(key=lambda x: x[0])
        return [term for term, _ in items_list]

    def _build_taxonomy(self, raw: dict[str, Any]) -> NeedTaxonomy:
        categories = [str(c) for c in (raw.get("need_categories") or []) if str(c).strip()]

        intent_raw = raw.get("intent_phrases", {}) or {}
        intent_phrases: dict[str, list[str]] = {}
        for cat, phrases in intent_raw.items():
            if phrases and isinstance(phrases[0], tuple):
                intent_phrases[str(cat)] = self._sorted_terms(phrases)
            else:
                intent_phrases[str(cat)] = [str(p).strip().lower() for p in phrases if str(p).strip()]

        need_raw = raw.get("need_keywords", {}) or {}
        need_keywords: dict[str, list[str]] = {}
        for cat, words in need_raw.items():
            if words and isinstance(words[0], tuple):
                need_keywords[str(cat)] = self._sorted_terms(words)
            else:
                need_keywords[str(cat)] = [str(w).strip().lower() for w in words if str(w).strip()]

        noise_raw = raw.get("noise_keywords", []) or []
        noise_keywords = {str(w).strip().lower() for w in noise_raw if str(w).strip()}

        return NeedTaxonomy(
            categories=categories,
            intent_phrases=intent_phrases,
            need_keywords=need_keywords,
            noise_keywords=noise_keywords,
        )


_DEFAULT_LOADER = NeedTaxonomyLoader()


def get_need_taxonomy() -> NeedTaxonomy:
    return _DEFAULT_LOADER.load()


__all__ = ["NeedTaxonomy", "NeedTaxonomyLoader", "get_need_taxonomy"]
