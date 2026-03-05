from __future__ import annotations

import uuid

import pytest
import yaml
from sqlalchemy import text

from app.db.session import SessionFactory
from app.interfaces.semantic_provider import SemanticLoadStrategy
from app.services.semantic.need_taxonomy import NeedTaxonomyLoader


def _write_yaml(path) -> None:
    payload = {
        "need_categories": ["Survival", "Efficiency", "Belonging", "Aesthetic", "Growth"],
        "intent_phrases": {
            "Growth": ["how to"],
            "Efficiency": ["best tool"],
        },
        "need_keywords": {
            "Growth": ["yaml_growth"],
        },
        "noise_keywords": ["yaml_noise"],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@pytest.mark.asyncio
async def test_need_taxonomy_yaml_only(tmp_path) -> None:
    yaml_path = tmp_path / "need_taxonomy.yaml"
    _write_yaml(yaml_path)

    loader = NeedTaxonomyLoader(config_path=yaml_path, strategy=SemanticLoadStrategy.YAML_ONLY)
    taxonomy = loader.load()

    assert "Growth" in taxonomy.categories
    assert "how to" in taxonomy.intent_phrases["Growth"]
    assert "yaml_growth" in taxonomy.need_keywords["Growth"]
    assert "yaml_noise" in taxonomy.noise_keywords


@pytest.mark.asyncio
async def test_need_taxonomy_db_overrides_yaml(tmp_path) -> None:
    yaml_path = tmp_path / "need_taxonomy.yaml"
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
                "code": f"need_taxonomy_{concept_id}",
                "name": "need taxonomy",
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
                "term": "db_growth",
                "rule_type": "need_keyword",
                "meta": "{\"category\": \"Growth\", \"order\": 0}",
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
                "term": "db_noise",
                "rule_type": "need_noise",
                "meta": "{}",
            },
        )
        await session.commit()

    loader = NeedTaxonomyLoader(config_path=yaml_path, strategy=SemanticLoadStrategy.DB_YAML_FALLBACK)
    taxonomy = loader.load()

    assert "db_growth" in taxonomy.need_keywords["Growth"]
    assert "yaml_growth" not in taxonomy.need_keywords["Growth"]
    assert "db_noise" in taxonomy.noise_keywords
    assert "yaml_noise" not in taxonomy.noise_keywords
