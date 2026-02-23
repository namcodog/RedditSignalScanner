"""Factory for SemanticProvider instances."""
from __future__ import annotations

from app.db.session import SessionFactory
from app.interfaces.semantic_provider import SemanticProvider, SemanticLoadStrategy
from app.services.semantic.robust_loader import RobustSemanticLoader

_default_provider: SemanticProvider | None = None


def get_semantic_provider() -> SemanticProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = RobustSemanticLoader(
            session_factory=SessionFactory,
            strategy=SemanticLoadStrategy.DB_YAML_FALLBACK,
        )
    return _default_provider
