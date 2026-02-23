from __future__ import annotations

from pathlib import Path

import yaml

from app.services.hotpost.keywords import load_hotpost_keywords


def _write_keywords(path: Path) -> None:
    payload = {
        "rant_signals": {
            "strong": ["Worst Purchase", "worst purchase", "  TOTAL WASTE  "]
        },
        "opportunity_signals": {
            "seeking": ["Looking for", "looking for", "need a recommendation"],
            "unmet_need": ["I wish there was"],
            "resonance": ["ME TOO", "+1"],
        },
        "discovery_signals": {
            "positive": ["Great", "great"],
            "hidden_gem": ["Hidden Gem"],
        },
        "intent_label": {
            "already_left": ["Switched from"],
            "considering": ["Thinking of switching"],
        },
        "pain_categories": {
            "pricing": ["Expensive", "  expensive  "],
            "performance": ["slow"],
            "reliability": ["broken"],
            "support": ["support"],
            "ux": ["confusing"],
            "other": ["noise"],
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_load_hotpost_keywords_normalizes(tmp_path: Path) -> None:
    yaml_path = tmp_path / "boom_post_keywords.yaml"
    _write_keywords(yaml_path)

    lexicon = load_hotpost_keywords(config_path=yaml_path)

    assert lexicon.rant_signals["strong"] == ["worst purchase", "total waste"]
    assert lexicon.opportunity_signals["seeking"] == ["looking for", "need a recommendation"]
    assert lexicon.opportunity_signals["resonance"] == ["me too", "+1"]
    assert lexicon.discovery_signals["positive"] == ["great"]
    assert lexicon.intent_label["already_left"] == ["switched from"]
    assert lexicon.pain_categories["pricing"] == ["expensive"]
