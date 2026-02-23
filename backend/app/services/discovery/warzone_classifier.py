from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import yaml


@dataclass(frozen=True, slots=True)
class WarzoneGuess:
    warzone: str
    confidence: float
    reasons: list[str]


class WarzoneClassifier:
    """Rule-based warzone (8 verticals) classifier, v0.

    Input: a list of texts (evidence post titles/bodies).
    Output: (warzone_guess, confidence, reasons).

    Design goal: simple + explainable + safe-by-default (unknown when no evidence).
    """

    def __init__(self, config_path: Path | str) -> None:
        self._path = Path(config_path)
        payload = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        zones = payload.get("warzones") or {}
        if not isinstance(zones, dict):
            zones = {}

        mapping: dict[str, list[str]] = {}
        for zone, cfg in zones.items():
            if not isinstance(zone, str) or not zone.strip():
                continue
            kws = []
            if isinstance(cfg, dict):
                raw = cfg.get("keywords") or []
            else:
                raw = []
            if isinstance(raw, list):
                for kw in raw:
                    s = str(kw or "").strip()
                    if s:
                        kws.append(s.lower())
            if kws:
                mapping[zone.strip()] = kws

        self._mapping = mapping

    def classify_texts(self, texts: Sequence[str]) -> WarzoneGuess:
        if not self._mapping:
            return WarzoneGuess(warzone="unknown", confidence=0.0, reasons=[])

        joined = "\n".join(str(t or "") for t in texts).lower()
        if not joined.strip():
            return WarzoneGuess(warzone="unknown", confidence=0.0, reasons=[])

        scores: dict[str, int] = {}
        reasons: dict[str, list[str]] = {}
        for zone, kws in self._mapping.items():
            hits: list[str] = []
            count = 0
            for kw in kws:
                if not kw:
                    continue
                if kw in joined:
                    count += 1
                    hits.append(kw)
            if count > 0:
                scores[zone] = count
                # keep top reasons in a stable order
                reasons[zone] = sorted(set(hits))

        if not scores:
            return WarzoneGuess(warzone="unknown", confidence=0.0, reasons=[])

        best_zone = max(scores.items(), key=lambda kv: (kv[1], kv[0]))[0]
        best = float(scores.get(best_zone, 0))
        total = float(sum(scores.values()) or 0.0)
        conf = (best / total) if total > 0 else 0.0
        return WarzoneGuess(
            warzone=best_zone,
            confidence=round(max(0.0, min(1.0, conf)), 3),
            reasons=reasons.get(best_zone, []),
        )


__all__ = ["WarzoneClassifier", "WarzoneGuess"]

