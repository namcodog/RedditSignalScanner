from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "card_content_rules.yaml"


@lru_cache(maxsize=1)
def load_card_content_rules() -> dict[str, Any]:
    payload = yaml.safe_load(_RULES_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("card_content_rules.yaml is invalid")
    return payload


__all__ = ["load_card_content_rules"]
