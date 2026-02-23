from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Mapping

import yaml
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.interfaces.semantic_provider import SemanticLoadStrategy

_DEFAULT_CONFIG_PATH = Path("backend/config/signal_keywords.yaml")

_DB_RULE_TYPES = (
    "signal_negative",
    "signal_solution",
    "signal_opportunity",
    "signal_urgency",
    "signal_competitor",
    "signal_pain_pattern",
    "signal_pain_bucket",
)


@dataclass(frozen=True)
class SignalLexicon:
    negative_terms: set[str]
    solution_cues: set[str]
    opportunity_cues: list[str]
    urgency_terms: set[str]
    competitor_cues: tuple[str, ...]
    pain_patterns: list[re.Pattern[str]]
    pain_bucket_rules: list[tuple[str, tuple[str, ...]]]

    def iter_pain_buckets(self) -> list[tuple[str, tuple[str, ...]]]:
        return list(self.pain_bucket_rules)


class SignalLexiconLoader:
    def __init__(
        self,
        config_path: Path | None = None,
        *,
        strategy: SemanticLoadStrategy = SemanticLoadStrategy.DB_YAML_FALLBACK,
    ) -> None:
        self._path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._strategy = strategy
        self._cache: SignalLexicon | None = None
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

    def load(self) -> SignalLexicon:
        with self._lock:
            current_mtime = self._path.stat().st_mtime if self._path.exists() else None
            if self._cache is not None and current_mtime == self._mtime:
                return self._cache

            yaml_payload = self._load_yaml_raw()
            raw_payload = dict(yaml_payload)

            if self._strategy != SemanticLoadStrategy.YAML_ONLY:
                db_payload = self._load_db_raw()
                raw_payload = self._merge_raw(yaml_payload, db_payload)

            lexicon = self._build_lexicon(raw_payload)
            self._cache = lexicon
            self._mtime = current_mtime
            return lexicon

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
                        SELECT term, rule_type, weight, meta
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
            "negative_terms": [],
            "solution_cues": [],
            "opportunity_cues": [],
            "urgency_terms": [],
            "competitor_cues": [],
            "pain_patterns": [],
            "pain_buckets": {},
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
            term_raw = str(row.get("term") or "")
            rule_type = str(row.get("rule_type") or "").strip().lower()
            weight = float(row.get("weight") or 1.0)
            meta = _parse_meta(row.get("meta"))

            if rule_type == "signal_competitor":
                term = term_raw.lower()
                if not term.strip():
                    continue
            else:
                term = term_raw.strip().lower()
                if not term:
                    continue

            order = meta.get("order")
            order_val = int(order) if isinstance(order, int) or str(order).isdigit() else None

            if rule_type == "signal_negative":
                data["negative_terms"].append((term, weight, order_val))
            elif rule_type == "signal_solution":
                data["solution_cues"].append((term, weight, order_val))
            elif rule_type == "signal_opportunity":
                data["opportunity_cues"].append((term, weight, order_val))
            elif rule_type == "signal_urgency":
                data["urgency_terms"].append((term, weight, order_val))
            elif rule_type == "signal_competitor":
                data["competitor_cues"].append((term, weight, order_val))
            elif rule_type == "signal_pain_pattern":
                data["pain_patterns"].append((term, weight, order_val))
            elif rule_type == "signal_pain_bucket":
                bucket = str(meta.get("bucket") or "").strip().lower()
                if not bucket:
                    continue
                bucket_order = meta.get("bucket_order")
                bucket_order_val = None
                if isinstance(bucket_order, int) or str(bucket_order).isdigit():
                    bucket_order_val = int(bucket_order)
                term_order = meta.get("term_order")
                term_order_val = None
                if isinstance(term_order, int) or str(term_order).isdigit():
                    term_order_val = int(term_order)
                payload = data["pain_buckets"].setdefault(
                    bucket,
                    {
                        "bucket_order": bucket_order_val,
                        "terms": [],
                    },
                )
                payload["terms"].append((term, term_order_val))

        return data

    @staticmethod
    def _merge_raw(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        if not override:
            return dict(base)
        merged = dict(base)
        for key in (
            "negative_terms",
            "solution_cues",
            "opportunity_cues",
            "urgency_terms",
            "competitor_cues",
            "pain_patterns",
            "pain_buckets",
        ):
            override_val = override.get(key)
            if override_val:
                merged[key] = override_val
        return merged

    @staticmethod
    def _sorted_terms(items: Iterable[tuple[str, float, int | None]]) -> list[str]:
        items_list = list(items)
        if not items_list:
            return []
        has_order = any(order is not None for _, _, order in items_list)
        if has_order:
            items_list.sort(key=lambda x: ((x[2] if x[2] is not None else 1_000_000), x[0]))
        else:
            items_list.sort(key=lambda x: (-x[1], x[0]))
        return [term for term, _, _ in items_list]

    def _build_lexicon(self, raw: dict[str, Any]) -> SignalLexicon:
        negative_terms_raw = raw.get("negative_terms", [])
        solution_cues_raw = raw.get("solution_cues", [])
        opportunity_cues_raw = raw.get("opportunity_cues", [])
        urgency_terms_raw = raw.get("urgency_terms", [])
        competitor_cues_raw = raw.get("competitor_cues", [])
        pain_patterns_raw = raw.get("pain_patterns", [])
        pain_buckets_raw = raw.get("pain_buckets", {})

        if negative_terms_raw and isinstance(negative_terms_raw[0], tuple):
            negative_terms = set(self._sorted_terms(negative_terms_raw))
        else:
            negative_terms = {str(x).strip().lower() for x in negative_terms_raw if str(x).strip()}

        if solution_cues_raw and isinstance(solution_cues_raw[0], tuple):
            solution_cues = set(self._sorted_terms(solution_cues_raw))
        else:
            solution_cues = {str(x).strip().lower() for x in solution_cues_raw if str(x).strip()}

        if opportunity_cues_raw and isinstance(opportunity_cues_raw[0], tuple):
            opportunity_cues = self._sorted_terms(opportunity_cues_raw)
        else:
            opportunity_cues = [
                str(x).strip().lower() for x in opportunity_cues_raw if str(x).strip()
            ]

        if urgency_terms_raw and isinstance(urgency_terms_raw[0], tuple):
            urgency_terms = set(self._sorted_terms(urgency_terms_raw))
        else:
            urgency_terms = {str(x).strip().lower() for x in urgency_terms_raw if str(x).strip()}

        if competitor_cues_raw and isinstance(competitor_cues_raw[0], tuple):
            competitor_terms = self._sorted_terms(competitor_cues_raw)
            competitor_cues = tuple(competitor_terms)
        else:
            competitor_cues = tuple(
                str(x).lower() for x in competitor_cues_raw if str(x).strip()
            )

        if pain_patterns_raw and isinstance(pain_patterns_raw[0], tuple):
            pattern_terms = self._sorted_terms(pain_patterns_raw)
        else:
            pattern_terms = [
                str(x).strip() for x in pain_patterns_raw if str(x).strip()
            ]
        pain_patterns = self._compile_patterns(pattern_terms)

        pain_bucket_rules: list[tuple[str, tuple[str, ...]]] = []
        if pain_buckets_raw and isinstance(pain_buckets_raw, Mapping):
            ordered_buckets = self._build_bucket_rules(pain_buckets_raw)
            pain_bucket_rules = ordered_buckets

        return SignalLexicon(
            negative_terms=negative_terms,
            solution_cues=solution_cues,
            opportunity_cues=opportunity_cues,
            urgency_terms=urgency_terms,
            competitor_cues=competitor_cues,
            pain_patterns=pain_patterns,
            pain_bucket_rules=pain_bucket_rules,
        )

    @staticmethod
    def _compile_patterns(patterns: Iterable[str]) -> list[re.Pattern[str]]:
        compiled: list[re.Pattern[str]] = []
        for raw in patterns:
            val = str(raw).strip()
            if not val:
                continue
            try:
                compiled.append(re.compile(val, re.IGNORECASE))
            except re.error:
                continue
        return compiled

    @staticmethod
    def _build_bucket_rules(raw: Mapping[str, Any]) -> list[tuple[str, tuple[str, ...]]]:
        buckets: list[tuple[str, tuple[str, ...], int]] = []
        for idx, (bucket, data) in enumerate(raw.items()):
            bucket_name = str(bucket).strip().lower()
            if not bucket_name:
                continue
            if isinstance(data, Mapping):
                terms = [
                    str(t).strip().lower() for t in (data.get("terms") or []) if str(t).strip()
                ]
                bucket_order = data.get("bucket_order")
                order_val = int(bucket_order) if isinstance(bucket_order, int) or str(bucket_order).isdigit() else idx
            else:
                terms = [str(t).strip().lower() for t in (data or []) if str(t).strip()]
                order_val = idx
            buckets.append((bucket_name, tuple(terms), order_val))

        buckets.sort(key=lambda x: (x[2], x[0]))
        return [(bucket, terms) for bucket, terms, _ in buckets]


_DEFAULT_LOADER = SignalLexiconLoader()


def get_signal_lexicon() -> SignalLexicon:
    return _DEFAULT_LOADER.load()


__all__ = ["SignalLexicon", "SignalLexiconLoader", "get_signal_lexicon"]
