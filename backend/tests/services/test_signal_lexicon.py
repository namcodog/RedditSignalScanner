from __future__ import annotations

import uuid

import pytest
import yaml
from sqlalchemy import text

from app.db.session import SessionFactory
from app.interfaces.semantic_provider import SemanticLoadStrategy
from app.services.analysis.signal_lexicon import SignalLexiconLoader


def _write_yaml(path) -> None:
    payload = {
        "negative_terms": ["yaml_negative"],
        "solution_cues": ["yaml_solution"],
        "opportunity_cues": ["yaml_opportunity"],
        "urgency_terms": ["yaml_urgent"],
        "competitor_cues": [" vs "],
        "pain_patterns": [r"\\btest pain\\b"],
        "pain_buckets": {"broken": ["error"]},
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@pytest.mark.asyncio
async def test_signal_lexicon_yaml_only(tmp_path) -> None:
    yaml_path = tmp_path / "signal_keywords.yaml"
    _write_yaml(yaml_path)

    loader = SignalLexiconLoader(config_path=yaml_path, strategy=SemanticLoadStrategy.YAML_ONLY)
    lexicon = loader.load()

    assert "yaml_negative" in lexicon.negative_terms
    assert "yaml_solution" in lexicon.solution_cues
    assert "yaml_opportunity" in lexicon.opportunity_cues
    assert "yaml_urgent" in lexicon.urgency_terms
    assert " vs " in lexicon.competitor_cues
    assert lexicon.pain_patterns
    assert ("broken", ("error",)) in lexicon.pain_bucket_rules


@pytest.mark.asyncio
async def test_signal_lexicon_db_overrides_yaml(tmp_path) -> None:
    yaml_path = tmp_path / "signal_keywords.yaml"
    _write_yaml(yaml_path)

    async with SessionFactory() as session:
        concept_id = int(uuid.uuid4().int % 1_000_000_000)
        await session.execute(
            text(
                """
                INSERT INTO semantic_concepts (id, code, name, domain, is_active)
                VALUES (:id, :code, :name, :domain, true)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": concept_id,
                "code": f"signal_test_{concept_id}",
                "name": "signal test",
                "domain": "general",
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO semantic_rules (concept_id, term, rule_type, weight, is_active, meta)
                VALUES (:concept_id, :term, :rule_type, 1.0, true, :meta)
                """
            ),
            {
                "concept_id": concept_id,
                "term": "db_negative",
                "rule_type": "signal_negative",
                "meta": "{\"order\": 0}",
            },
        )
        await session.commit()

    loader = SignalLexiconLoader(config_path=yaml_path, strategy=SemanticLoadStrategy.DB_YAML_FALLBACK)
    lexicon = loader.load()

    assert "db_negative" in lexicon.negative_terms
    assert "yaml_negative" not in lexicon.negative_terms
