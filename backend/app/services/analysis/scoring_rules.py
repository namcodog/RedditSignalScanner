"""Scoring rules loader for opportunity heuristics."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Sequence, Dict, Any, Tuple, Mapping

import yaml
from sqlalchemy import create_engine, text

from app.core.config import get_settings


@dataclass(frozen=True)
class KeywordRule:
    keyword: str
    weight: float
    rule_id: int | None = None


@dataclass(frozen=True)
class NegationRule:
    pattern: str
    impact: float
    rule_id: int | None = None


@dataclass(frozen=True)
class ScoringRules:
    positive_keywords: Sequence[KeywordRule]
    negative_keywords: Sequence[KeywordRule]
    negation_patterns: Sequence[NegationRule]
    # Optional: parameters for opportunity potential users estimation (Spec010)
    opportunity_estimator: "OpportunityEstimatorConfig | None" = None
    need_weights: Mapping[str, float] | None = None
    dual_label_bonus: float | None = None


@dataclass(frozen=True)
class OpportunityEstimatorConfig:
    base: float = 100.0
    freq_weight: float = 50.0
    avg_score_weight: float = 2.0
    keyword_weight: float = 20.0
    theme_relevance: float = 0.0
    intent_factor: float = 0.0
    participation_rate: float = 0.0


class ScoringRulesLoader:
    """Load scoring configuration from YAML with lightweight caching."""

    def __init__(self, config_path: Path | None = None) -> None:
        base = Path(__file__).resolve()
        if config_path is None:
            resolved = None
            for parent in base.parents:
                candidate = parent / "config" / "scoring_rules.yaml"
                if candidate.exists():
                    resolved = candidate
                    break
            if resolved is None:
                resolved = Path.cwd() / "config" / "scoring_rules.yaml"
            self._path = resolved
        else:
            self._path = config_path
        self._cache: ScoringRules | None = None
        self._mtime: float | None = None
        self._lock = Lock()
        self._engine = None
        self._rule_id_index: Dict[str, list[int]] = {}
        self._layer_index: Dict[str, list[KeywordRule]] = {}
        try:
            settings = get_settings()
            db_url = settings.database_url.replace("asyncpg", "psycopg")
            self._engine = create_engine(db_url, future=True)
        except Exception:
            self._engine = None

    def load(self) -> ScoringRules:
        with self._lock:
            current_mtime = self._path.stat().st_mtime
            if self._cache is not None and current_mtime == self._mtime:
                return self._cache

            # 优先从数据库加载，失败则回退 YAML
            rules = self._load_from_db()
            if rules is None:
                with self._path.open("r", encoding="utf-8") as fh:
                    payload = yaml.safe_load(fh) or {}
                est = self._parse_opportunity_estimator(payload.get("opportunity_estimator", {}) or {})
                need_weights = self._parse_need_weights(payload.get("need_weights", {}) or {})
                dual_label_bonus = self._parse_dual_label_bonus(payload.get("dual_label_bonus"))
                rules = ScoringRules(
                    positive_keywords=self._parse_keyword_rules(
                        payload.get("positive_keywords", []), default_weight=0.1
                    ),
                    negative_keywords=self._parse_keyword_rules(
                        payload.get("negative_keywords", []), default_weight=-0.2
                    ),
                    negation_patterns=self._parse_negation_rules(
                        payload.get("negation_patterns", [])
                    ),
                    opportunity_estimator=est,
                    need_weights=need_weights,
                    dual_label_bonus=dual_label_bonus,
                )
                self._rule_id_index = {}
                self._layer_index = {
                    "L1": list(rules.positive_keywords) + list(rules.negative_keywords)
                }

            self._cache = rules
            self._mtime = current_mtime
            return rules

    def _load_from_db(self) -> ScoringRules | None:
        if self._engine is None:
            return None
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text(
                        """
                        SELECT r.id, r.term, r.weight, r.rule_type
                             , r.meta
                        FROM semantic_rules r
                        JOIN semantic_concepts c ON c.id = r.concept_id
                        WHERE r.is_active = true AND c.is_active = true
                        """
                    )
                ).mappings().all()
        except Exception:
            return None

        if not rows:
            return None

        positive, negative, negations = self._build_rules_from_rows(rows)

        # 与 YAML 配置的机会估计参数兼容：仍从文件读取
        with self._path.open("r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh) or {}
        est = self._parse_opportunity_estimator(payload.get("opportunity_estimator", {}) or {})
        need_weights = self._parse_need_weights(payload.get("need_weights", {}) or {})
        dual_label_bonus = self._parse_dual_label_bonus(payload.get("dual_label_bonus"))

        return ScoringRules(
            positive_keywords=positive,
            negative_keywords=negative,
            negation_patterns=negations,
            opportunity_estimator=est,
            need_weights=need_weights,
            dual_label_bonus=dual_label_bonus,
        )

    def increment_hit_counts(self, rule_ids: Sequence[int]) -> None:
        if self._engine is None or not rule_ids:
            return
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE semantic_rules SET hit_count = hit_count + 1, last_hit_at = NOW() WHERE id = ANY(:ids)"
                    ),
                    {"ids": list(set(rule_ids))},
                )
        except Exception:
            # 安全兜底：写入失败不影响主流程
            return

    def get_rule_ids_for_keywords(self, keywords: Sequence[str]) -> list[int]:
        ids: list[int] = []
        for kw in keywords:
            hits = self._rule_id_index.get(kw)
            if hits:
                ids.extend(hits)
        return ids

    @property
    def layer_index(self) -> Dict[str, list[KeywordRule]]:
        return self._layer_index

    @staticmethod
    def _parse_keyword_rules(
        items: Iterable[object], *, default_weight: float
    ) -> List[KeywordRule]:
        rules: List[KeywordRule] = []
        for item in items:
            if isinstance(item, dict):
                keyword = str(item.get("keyword", "")).strip().lower()
                weight = item.get("weight", default_weight)
            else:
                keyword = str(item).strip().lower()
                weight = default_weight

            if not keyword:
                continue

            try:
                weight_value = float(weight)
            except (TypeError, ValueError):
                weight_value = default_weight

            rules.append(KeywordRule(keyword=keyword, weight=weight_value))
        return rules

    @staticmethod
    def _parse_opportunity_estimator(data: object) -> OpportunityEstimatorConfig:
        try:
            if not isinstance(data, dict):
                return OpportunityEstimatorConfig()
            return OpportunityEstimatorConfig(
                base=float(data.get("base", 100.0) or 100.0),
                freq_weight=float(data.get("freq_weight", 50.0) or 50.0),
                avg_score_weight=float(data.get("avg_score_weight", 2.0) or 2.0),
                keyword_weight=float(data.get("keyword_weight", 20.0) or 20.0),
                theme_relevance=float(data.get("theme_relevance", 0.0) or 0.0),
                intent_factor=float(data.get("intent_factor", 0.0) or 0.0),
                participation_rate=float(data.get("participation_rate", 0.0) or 0.0),
            )
        except Exception:
            return OpportunityEstimatorConfig()

    @staticmethod
    def _parse_need_weights(data: object) -> Mapping[str, float]:
        if not isinstance(data, dict):
            return {}
        weights: dict[str, float] = {}
        for key, value in data.items():
            name = str(key).strip()
            if not name:
                continue
            try:
                weights[name] = float(value)
            except (TypeError, ValueError):
                continue
        return weights

    @staticmethod
    def _parse_dual_label_bonus(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_negation_rules(items: Iterable[object]) -> List[NegationRule]:
        rules: List[NegationRule] = []
        for item in items:
            if isinstance(item, dict):
                pattern = str(item.get("pattern", "")).strip().lower()
                impact = item.get("impact", -0.5)
            else:
                pattern = str(item).strip().lower()
                impact = -0.5

            if not pattern:
                continue

            try:
                impact_value = float(impact)
            except (TypeError, ValueError):
                impact_value = -0.5

            rules.append(NegationRule(pattern=pattern, impact=impact_value))
        return rules

    def _build_rules_from_rows(self, rows: Sequence[Mapping[str, Any]]) -> Tuple[list[KeywordRule], list[KeywordRule], list[NegationRule]]:
        positive: list[KeywordRule] = []
        negative: list[KeywordRule] = []
        negations: list[NegationRule] = []
        index: Dict[str, list[int]] = {}
        layers: Dict[str, list[KeywordRule]] = defaultdict(list)

        for row in rows:
            term = str(row.get("term", "")).strip().lower()
            rule_type = str(row.get("rule_type", "keyword")).lower()
            meta_raw = row.get("meta") or {}
            if isinstance(meta_raw, str):
                try:
                    meta = json.loads(meta_raw)
                except Exception:
                    meta = {}
            elif isinstance(meta_raw, Mapping):
                meta = dict(meta_raw)
            else:
                meta = {}
            layer = str(meta.get("layer", "L1") or "L1").upper()

            try:
                weight = float(row.get("weight") or 0.0)
            except (TypeError, ValueError):
                weight = 0.0
            try:
                rule_id = int(row.get("id") or 0)
            except (TypeError, ValueError):
                rule_id = 0

            if not term:
                continue

            if rule_type == "regex":
                negations.append(NegationRule(pattern=term, impact=weight, rule_id=rule_id or None))
            elif weight >= 0:
                rule = KeywordRule(keyword=term, weight=weight, rule_id=rule_id or None)
                positive.append(rule)
                layers[layer].append(rule)
            else:
                rule = KeywordRule(keyword=term, weight=weight, rule_id=rule_id or None)
                negative.append(rule)
                layers[layer].append(rule)

            if rule_id:
                index.setdefault(term, []).append(rule_id)

        if not layers:
            layers["L1"] = []
        self._rule_id_index = index
        self._layer_index = {k: v for k, v in layers.items()}
        return positive, negative, negations


__all__ = [
    "KeywordRule",
    "NegationRule",
    "ScoringRules",
    "ScoringRulesLoader",
    "OpportunityEstimatorConfig",
]
