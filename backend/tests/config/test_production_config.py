from pathlib import Path

from app.services.crawler_config import get_crawler_config
from app.services.semantic.unified_lexicon import UnifiedLexicon


def test_crawler_ttl_consistency() -> None:
    cfg = get_crawler_config()
    assert cfg.global_settings.hot_cache_ttl_hours == 4320
    assert all(t.hot_cache_ttl_hours == 4320 for t in cfg.tiers)


def test_unified_lexicon_loads() -> None:
    # lexicon path from repo root
    lex_path = Path(__file__).resolve().parents[2] / "config/semantic_sets/crossborder_v2.1.yml"
    assert lex_path.exists()
    lex = UnifiedLexicon(lex_path)
    terms = lex.get_brands() + lex.get_features() + lex.get_pain_points()
    assert len(terms) > 100
