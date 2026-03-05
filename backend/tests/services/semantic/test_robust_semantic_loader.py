import json
from pathlib import Path

import pytest

from app.interfaces.semantic_provider import SemanticLoadStrategy
from app.services.semantic.robust_loader import RobustSemanticLoader


@pytest.mark.asyncio
async def test_yaml_only_load(tmp_path: Path):
    data = [{"canonical": "foo"}]
    yaml_file = tmp_path / "lexicon.json"
    yaml_file.write_text(json.dumps(data), encoding="utf-8")

    loader = RobustSemanticLoader(
        session_factory=None,
        fallback_yaml=yaml_file,
        strategy=SemanticLoadStrategy.YAML_ONLY,
        ttl_seconds=1,
    )
    payload = await loader.load()
    assert payload == data
    metrics = await loader.get_metrics()
    assert metrics.yaml_fallbacks >= 0
    assert hasattr(metrics, "load_latency_p95_ms")


@pytest.mark.asyncio
async def test_db_only_without_session_factory():
    loader = RobustSemanticLoader(session_factory=None, strategy=SemanticLoadStrategy.DB_ONLY)
    with pytest.raises(RuntimeError):
        await loader.load()


@pytest.mark.asyncio
async def test_db_failure_fallback_to_yaml(tmp_path: Path, caplog):
    data = [{"canonical": "bar"}]
    yaml_file = tmp_path / "lexicon.json"
    yaml_file.write_text(json.dumps(data), encoding="utf-8")

    async def failing_session_factory():
        raise RuntimeError("db down")

    loader = RobustSemanticLoader(
        session_factory=failing_session_factory,
        fallback_yaml=yaml_file,
        strategy=SemanticLoadStrategy.DB_YAML_FALLBACK,
        ttl_seconds=1,
    )
    with caplog.at_level("WARNING"):
        payload = await loader.load()
    assert payload == data
