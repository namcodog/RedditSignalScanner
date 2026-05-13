from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values


BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_ROOT / ".env"


def load_backend_env() -> None:
    for key, value in dotenv_values(ENV_PATH).items():
        if value and _should_override(key):
            os.environ[key] = value


def _should_override(key: str) -> bool:
    current = os.environ.get(key, "")
    return not current or current.startswith("your_")


__all__ = ["load_backend_env"]
