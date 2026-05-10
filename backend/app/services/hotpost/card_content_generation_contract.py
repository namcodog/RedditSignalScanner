from __future__ import annotations

from typing import Any


def build_generation_field_contract_prompt(rules: dict[str, Any]) -> str:
    # Field semantics now live in prompt assets. Keep this function as a
    # compatibility seam for old callers, but do not append another copywriting
    # contract to the system prompt.
    return ""


__all__ = ["build_generation_field_contract_prompt"]
