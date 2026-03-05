"""
YAML -> DB 语义资产迁移脚本。

用法：
    python -m backend.scripts.migrate_semantics
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

import yaml
from sqlalchemy import create_engine, text

from app.core.config import get_settings


def get_engine():
    settings = get_settings()
    url = settings.database_url.replace("asyncpg", "psycopg")
    return create_engine(url, future=True)


def upsert_concept(conn, code: str, name: str, description: str = "", domain: str = "general") -> int:
    row = conn.execute(
        text(
            """
            INSERT INTO semantic_concepts(code, name, description, domain)
            VALUES (:code, :name, :description, :domain)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                description = EXCLUDED.description,
                domain = EXCLUDED.domain,
                updated_at = NOW()
            RETURNING id
            """
        ),
        {"code": code, "name": name, "description": description or "", "domain": domain},
    ).scalar_one()
    return int(row)


def upsert_rule(
    conn,
    concept_id: int,
    term: str,
    rule_type: str,
    weight: float,
    meta: Dict,
    *,
    normalize_term: bool = True,
) -> None:
    term_value = term.strip().lower() if normalize_term else term.lower()
    conn.execute(
        text(
            """
            INSERT INTO semantic_rules(concept_id, term, rule_type, weight, meta)
            VALUES (:concept_id, :term, :rule_type, :weight, :meta)
            ON CONFLICT (concept_id, term, rule_type) DO UPDATE
            SET weight = EXCLUDED.weight,
                meta = EXCLUDED.meta,
                updated_at = NOW(),
                is_active = true
            """
        ),
        {
            "concept_id": concept_id,
            "term": term_value,
            "rule_type": rule_type,
            "weight": weight,
            "meta": json.dumps(meta or {}),
        },
    )


def load_pain_dictionary(conn, root: Path) -> int:
    path = root / "pain_dictionary.yaml"
    if not path.exists():
        return 0
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    concept_id = upsert_concept(conn, "pain_keywords", "通用痛点词库", "pain_dictionary.yaml")
    count = 0
    for term, info in payload.items():
        meta = {}
        if isinstance(info, dict):
            meta = {k: v for k, v in info.items() if k not in {"title_cn"}}
        upsert_rule(conn, concept_id, term, "pain_keywords", 1.0, meta)
        count += 1
    return count


def load_blacklist(conn, root: Path) -> Tuple[int, int]:
    path = root / "community_blacklist.yaml"
    if not path.exists():
        return 0, 0
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    blacklist_concept = upsert_concept(conn, "global_blacklist", "全局黑名单", "community_blacklist.yaml")
    filter_concept = upsert_concept(conn, "global_filter_keywords", "全局过滤关键词", "community_blacklist.yaml")
    blk_count = 0
    filt_count = 0

    for item in payload.get("blacklisted_communities", []) or []:
        if isinstance(item, dict) and item.get("name"):
            meta = {"reason": item.get("reason")}
            upsert_rule(conn, blacklist_concept, item["name"], "keyword", -999.0, meta)
            blk_count += 1
    for name in payload.get("blacklist", []) or []:
        upsert_rule(conn, blacklist_concept, name, "keyword", -999.0, {})
        blk_count += 1

    for item in payload.get("filter_keywords", []) or []:
        if isinstance(item, dict):
            term = item.get("keyword")
        else:
            term = item
        if term:
            upsert_rule(conn, filter_concept, term, "keyword", -0.5, {})
            filt_count += 1

    for item in payload.get("downrank_keywords", []) or []:
        if isinstance(item, dict):
            term = item.get("keyword")
        else:
            term = item
        if term:
            upsert_rule(conn, filter_concept, term, "keyword", -0.2, {"tag": "downrank"})
            filt_count += 1

    for item in payload.get("downranked_communities", []) or []:
        if isinstance(item, dict) and item.get("name"):
            meta = {"reason": item.get("reason")}
            upsert_rule(conn, blacklist_concept, item["name"], "keyword", -1.0, meta)
            blk_count += 1

    return blk_count, filt_count


def load_signal_keywords(conn, root: Path) -> int:
    path = root / "signal_keywords.yaml"
    if not path.exists():
        return 0
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    concept_id = upsert_concept(conn, "signal_keywords", "信号词库", "signal_keywords.yaml")
    count = 0

    def _upsert_list(items: Iterable[str], rule_type: str, *, normalize_term: bool = True) -> None:
        nonlocal count
        for idx, raw in enumerate(items):
            term = str(raw or "")
            if not term.strip():
                continue
            meta = {"order": idx}
            upsert_rule(
                conn,
                concept_id,
                term,
                rule_type,
                1.0,
                meta,
                normalize_term=normalize_term,
            )
            count += 1

    _upsert_list(payload.get("negative_terms", []) or [], "signal_negative")
    _upsert_list(payload.get("solution_cues", []) or [], "signal_solution")
    _upsert_list(payload.get("opportunity_cues", []) or [], "signal_opportunity")
    _upsert_list(payload.get("urgency_terms", []) or [], "signal_urgency")
    _upsert_list(payload.get("competitor_cues", []) or [], "signal_competitor", normalize_term=False)
    _upsert_list(payload.get("pain_patterns", []) or [], "signal_pain_pattern")

    pain_buckets = payload.get("pain_buckets", {}) or {}
    for bucket_idx, (bucket, terms) in enumerate(pain_buckets.items()):
        bucket_name = str(bucket or "").strip()
        if not bucket_name:
            continue
        for term_idx, term_raw in enumerate(terms or []):
            term = str(term_raw or "")
            if not term.strip():
                continue
            meta = {"bucket": bucket_name, "bucket_order": bucket_idx, "term_order": term_idx}
            upsert_rule(
                conn,
                concept_id,
                term,
                "signal_pain_bucket",
                1.0,
                meta,
            )
            count += 1

    return count


def load_need_taxonomy(conn, root: Path) -> int:
    path = root / "need_taxonomy.yaml"
    if not path.exists():
        return 0
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    concept_id = upsert_concept(conn, "need_taxonomy", "需求词库", "need_taxonomy.yaml")
    count = 0

    def _upsert_group(items: Iterable[str], rule_type: str, category: str | None = None) -> None:
        nonlocal count
        for idx, raw in enumerate(items):
            term = str(raw or "")
            if not term.strip():
                continue
            meta = {"order": idx}
            if category:
                meta["category"] = category
            upsert_rule(conn, concept_id, term, rule_type, 1.0, meta)
            count += 1

    intent_phrases = payload.get("intent_phrases", {}) or {}
    for category, phrases in intent_phrases.items():
        if not category:
            continue
        _upsert_group(phrases or [], "need_intent_phrase", str(category))

    need_keywords = payload.get("need_keywords", {}) or {}
    for category, words in need_keywords.items():
        if not category:
            continue
        _upsert_group(words or [], "need_keyword", str(category))

    noise_keywords = payload.get("noise_keywords", []) or []
    _upsert_group(noise_keywords, "need_noise")

    return count


def main() -> None:
    root = Path("backend/config")
    engine = get_engine()
    with engine.begin() as conn:
        pain = load_pain_dictionary(conn, root)
        blk, filt = load_blacklist(conn, root)
        signal = load_signal_keywords(conn, root)
        need_taxonomy = load_need_taxonomy(conn, root)
    print(
        f"✅ Migrated pain_keywords={pain}, blacklist={blk}, filter_keywords={filt}, "
        f"signal_keywords={signal}, need_taxonomy={need_taxonomy}"
    )


if __name__ == "__main__":
    main()
