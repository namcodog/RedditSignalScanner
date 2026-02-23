from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


DEFAULT_LAYER_MAP: Dict[str, str] = {
    "r/shopify": "L2",
    "r/amazonfba": "L2",
    "r/dropshipping": "L3",
    "r/ppc": "L3",
}


@dataclass
class LayerRouter:
    mapping: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_LAYER_MAP))
    default_layer: str = "L1"

    def __post_init__(self) -> None:
        # normalize keys to lower-case with prefix
        normalized: Dict[str, str] = {}
        for key, layer in self.mapping.items():
            norm_key = self.normalize_subreddit(key)
            if norm_key:
                normalized[norm_key] = layer.upper()
        self.mapping = normalized
        self.default_layer = self.default_layer.upper()

    @staticmethod
    def normalize_subreddit(subreddit: str) -> str:
        key = (subreddit or "").strip().lower()
        if not key:
            return ""
        if not key.startswith("r/"):
            key = f"r/{key}"
        return key

    def route(self, subreddit: str) -> Tuple[str, str]:
        norm = self.normalize_subreddit(subreddit)
        if not norm:
            return self.default_layer, norm
        layer = self.mapping.get(norm, self.default_layer)
        return layer, norm


__all__ = ["LayerRouter", "DEFAULT_LAYER_MAP"]
