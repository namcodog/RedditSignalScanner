from __future__ import annotations

from pathlib import Path

from app.api.v1 import api

SOURCE = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "api"
    / "v1"
    / "endpoints"
    / "brand_intelligence.py"
)


def test_brand_registry_api_is_registered() -> None:
    paths = {route.path for route in api.api_router.routes}

    assert "/brand-intelligence/registry" in paths


def test_brand_registry_api_uses_shared_read_service_only() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "read_brand_registry_view" in source
    assert 'consumer_profile_id="consumer_safe"' in source
    assert "BrandRegistry" not in source
    assert ".commit(" not in source
    assert ".add(" not in source
