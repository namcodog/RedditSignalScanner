"""Facts reader that prefers v2_package with fallback to legacy fields."""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Mapping


def load_facts(path: Path | str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # Prefer v2_package if present
    if isinstance(data, Mapping) and "v2_package" in data:
        return data["v2_package"]  # type: ignore[return-value]
    return data  # fallback legacy

