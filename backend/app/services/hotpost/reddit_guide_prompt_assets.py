from __future__ import annotations

from functools import lru_cache
from pathlib import Path


_ASSET_ROOT = Path(__file__).resolve().parents[3] / "config" / "prompt_assets"
_SHARED_BASE_PATH = _ASSET_ROOT / "shared_base_prompt.md"
_SOUL_PATH = _ASSET_ROOT / "reddit_guide_soul_prompt.md"
_THINKING_PATH = _ASSET_ROOT / "reddit_guide_thinking_contract.md"
_FEW_SHOTS_PATH = _ASSET_ROOT / "reddit_guide_few_shots.md"
_SIGNAL_FIELD_SEMANTICS_PATH = _ASSET_ROOT / "signal_field_semantics.md"
_SIGNAL_COMPACT_PROMPT_PATH = _ASSET_ROOT / "signal_compact_prompt.md"
_HOT_FIELD_SEMANTICS_PATH = _ASSET_ROOT / "hot_field_semantics.md"
_HOT_COMPACT_PROMPT_PATH = _ASSET_ROOT / "hot_compact_prompt.md"
_BREAKDOWN_FIELD_SEMANTICS_PATH = _ASSET_ROOT / "breakdown_field_semantics.md"
_BREAKDOWN_COMPACT_PROMPT_PATH = _ASSET_ROOT / "breakdown_compact_prompt.md"


def _read_asset(path: Path) -> str:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Prompt asset is empty: {path}")
    return content


@lru_cache(maxsize=1)
def load_shared_base_prompt() -> str:
    return _read_asset(_SHARED_BASE_PATH)


@lru_cache(maxsize=1)
def load_reddit_guide_soul_prompt() -> str:
    return _read_asset(_SOUL_PATH)


@lru_cache(maxsize=1)
def load_reddit_guide_thinking_contract() -> str:
    return _read_asset(_THINKING_PATH)


@lru_cache(maxsize=1)
def load_reddit_guide_few_shots() -> str:
    return _read_asset(_FEW_SHOTS_PATH)


@lru_cache(maxsize=1)
def load_signal_field_semantics() -> str:
    return _read_asset(_SIGNAL_FIELD_SEMANTICS_PATH)


@lru_cache(maxsize=1)
def load_signal_compact_prompt() -> str:
    return _read_asset(_SIGNAL_COMPACT_PROMPT_PATH)


@lru_cache(maxsize=1)
def load_hot_field_semantics() -> str:
    return _read_asset(_HOT_FIELD_SEMANTICS_PATH)


@lru_cache(maxsize=1)
def load_hot_compact_prompt() -> str:
    return _read_asset(_HOT_COMPACT_PROMPT_PATH)


@lru_cache(maxsize=1)
def load_breakdown_field_semantics() -> str:
    return _read_asset(_BREAKDOWN_FIELD_SEMANTICS_PATH)


@lru_cache(maxsize=1)
def load_breakdown_compact_prompt() -> str:
    return _read_asset(_BREAKDOWN_COMPACT_PROMPT_PATH)


def build_reddit_guide_prompt_prefix(*, mode_name: str) -> str:
    if mode_name == "潜力快帖":
        sections = [
            load_shared_base_prompt(),
            load_signal_compact_prompt(),
            load_signal_field_semantics(),
        ]
    elif mode_name == "近期爆帖":
        sections = [
            load_shared_base_prompt(),
            load_hot_compact_prompt(),
            load_hot_field_semantics(),
        ]
        sections.append(_few_shots_for_heading("近期爆帖示例"))
    elif mode_name == "跨区热议":
        sections = [
            load_shared_base_prompt(),
            load_breakdown_compact_prompt(),
            load_breakdown_field_semantics(),
        ]
        sections.append(_few_shots_for_heading("跨区热议示例"))
    else:
        sections = [
            load_reddit_guide_soul_prompt(),
            load_reddit_guide_thinking_contract(),
        ]
        sections.append(load_reddit_guide_few_shots())
    sections.append(f"当前输出模式：{mode_name}。")
    return "\n\n".join(section for section in sections if section.strip()) + "\n"


def _few_shots_for_heading(heading: str) -> str:
    content = load_reddit_guide_few_shots()
    marker = f"## {heading}"
    start = content.find(marker)
    if start < 0:
        return content
    next_start = content.find("\n## ", start + len(marker))
    if next_start < 0:
        return content[start:].strip()
    return content[start:next_start].strip()


__all__ = [
    "build_reddit_guide_prompt_prefix",
    "load_breakdown_compact_prompt",
    "load_breakdown_field_semantics",
    "load_shared_base_prompt",
    "load_reddit_guide_few_shots",
    "load_hot_compact_prompt",
    "load_hot_field_semantics",
    "load_reddit_guide_soul_prompt",
    "load_signal_field_semantics",
    "load_signal_compact_prompt",
    "load_reddit_guide_thinking_contract",
]
