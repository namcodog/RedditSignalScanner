from __future__ import annotations

import re
from typing import Any, Sequence

_WHITESPACE_RE = re.compile(r"\s+")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_PAIN_PLACEHOLDER_RE = re.compile(r"^(关键痛点|痛点|pain point)\s*\d*$", re.IGNORECASE)
_GENERIC_OPPORTUNITY_RE = re.compile(r"^(产品机会|机会)\s*\d*$", re.IGNORECASE)

META_LEAK_FRAGMENTS = (
    "系统生成",
    "统一结构",
    "前端",
    "同骨架",
    "口径",
    "不依赖前端拼装",
    "先在该社区验证问题复现频率",
    "社区名单由本轮分析真实数据生成",
    "这是一组",
    "这一组卡片",
    "如何阅读",
)

SYSTEMY_COPY_FRAGMENTS = (
    "趋势可用于继续决策",
    "结论已形成可读结构",
    "结论力度会随证据强度自动升级或保守",
    "痛点销售比",
    "立即投放",
    "测试广告",
    "先验证",
    "案例切入",
    "payout帖",
)

_LOW_SIGNAL_TOKENS = {
    "a",
    "ad",
    "ads",
    "ali",
    "an",
    "at",
    "att",
    "black",
    "edc",
}

_LOW_SIGNAL_FRAGMENTS = (
    "i analyzed",
    "analyzed reddit",
    "reddit discussions",
    "reddit sentiment at scale",
    "saas founders think",
    "would love",
    "looking for",
    "suggestions to",
    "quality items",
    "matte black",
    "can't post poll",
    "cannot post poll",
    "removed by moderators",
    "this post was removed",
    "post removed by moderators",
    "automoderator",
    "not enough karma",
    "account too new",
    "this thread is locked",
    "locked by moderators",
    "rule 1",
    "rule 2",
    "rule 3",
    "use the weekly thread",
    "please use the weekly thread",
    "contact the moderators",
)

_MARKETPLACE_TITLE_PREFIXES = (
    "[wts]",
    "[wtb]",
    "[wtt]",
    "wts ",
    "wtb ",
    "wtt ",
    "timestamp:",
    "fs:",
    "for sale:",
)

_MARKETPLACE_FRAGMENTS = (
    "no trades",
    "includes shipping",
    "pricing includes shipping",
    "out of production",
    "blade show",
    "conus",
    "sv $",
    "timestamp/photos",
)

_RAW_POST_TITLE_PREFIXES = (
    "looking for",
    "would love",
    "suggestions to",
    "hello",
    "help",
    "i need",
    "i want",
    "my ",
)


def _txt(value: Any) -> str:
    if value in (None, ""):
        return ""
    return _WHITESPACE_RE.sub(" ", str(value)).strip()


def contains_meta_leak(value: Any) -> bool:
    text = _txt(value)
    return bool(text) and any(fragment in text for fragment in META_LEAK_FRAGMENTS)


def contains_systemy_copy(value: Any) -> bool:
    text = _txt(value)
    return bool(text) and any(fragment in text for fragment in SYSTEMY_COPY_FRAGMENTS)


def contains_cjk_text(value: Any) -> bool:
    return bool(_CJK_RE.search(_txt(value)))


def is_low_signal_scaffold_pain_title(value: Any) -> bool:
    text = _txt(value)
    if not text:
        return True
    if not text.startswith("高频抱怨"):
        return False
    if "：" not in text and ":" not in text:
        return True
    suffix = text.split("：", 1)[-1] if "：" in text else text.split(":", 1)[-1]
    suffix = suffix.strip()
    if not suffix:
        return True
    return not contains_cjk_text(suffix)


def is_placeholder_pain_title(value: Any) -> bool:
    text = _txt(value)
    if not text:
        return True
    return bool(_PAIN_PLACEHOLDER_RE.match(text)) or is_low_signal_scaffold_pain_title(text)


def is_low_signal_opportunity_title(value: Any) -> bool:
    text = _txt(value)
    if not text:
        return True
    if bool(_GENERIC_OPPORTUNITY_RE.match(text)):
        return True
    if text.startswith("高频抱怨"):
        return True
    if text.startswith("产品机会："):
        suffix = text.split("：", 1)[-1].strip()
        if not suffix or not contains_cjk_text(suffix):
            return True
    return False


def looks_like_raw_post_title(value: Any) -> bool:
    text = _txt(value)
    if not text:
        return False
    lowered = text.lower()
    return lowered.endswith("?") or any(
        lowered.startswith(prefix) for prefix in _RAW_POST_TITLE_PREFIXES
    )


def looks_like_marketplace_listing(value: Any) -> bool:
    text = _txt(value)
    if not text:
        return False
    lowered = text.lower()
    return lowered.startswith(_MARKETPLACE_TITLE_PREFIXES) or any(
        fragment in lowered for fragment in _MARKETPLACE_FRAGMENTS
    )


def is_low_signal_business_text(value: Any, *, allow_reddit_tag: bool = False) -> bool:
    text = _txt(value)
    if not text:
        return True
    if contains_meta_leak(text):
        return True
    if looks_like_marketplace_listing(text):
        return True

    lowered = text.lower()
    if allow_reddit_tag and lowered.startswith("r/"):
        return False
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return True
    if lowered in _LOW_SIGNAL_TOKENS:
        return True
    if looks_like_raw_post_title(text):
        return True
    if any(fragment in lowered for fragment in _LOW_SIGNAL_FRAGMENTS):
        return True
    if _CJK_RE.search(text):
        return False

    words = _LATIN_WORD_RE.findall(lowered)
    if not words:
        return False
    if len(words) == 1 and len(words[0]) <= 6:
        return True
    if len(words) <= 4 and len(lowered) <= 40 and not any(char.isdigit() for char in lowered):
        return True
    if len(words) <= 5 and max(len(word) for word in words) <= 8:
        return True
    return False


def sanitize_business_text(
    value: Any,
    *,
    fallback: str = "",
    allow_reddit_tag: bool = False,
    reject_low_signal: bool = False,
    reject_systemy: bool = False,
) -> str:
    text = _txt(value)
    if not text:
        return fallback
    if contains_meta_leak(text):
        return fallback
    if reject_systemy and contains_systemy_copy(text):
        return fallback
    if reject_low_signal and is_low_signal_business_text(
        text,
        allow_reddit_tag=allow_reddit_tag,
    ):
        return fallback
    return text


def clean_business_terms(
    values: Sequence[Any],
    *,
    allow_reddit_tag: bool = False,
    require_cjk: bool = False,
) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = sanitize_business_text(
            value,
            allow_reddit_tag=allow_reddit_tag,
            reject_low_signal=True,
        )
        if require_cjk and not contains_cjk_text(text):
            continue
        if not text or text in cleaned:
            continue
        cleaned.append(text)
    return cleaned


__all__ = [
    "META_LEAK_FRAGMENTS",
    "clean_business_terms",
    "contains_cjk_text",
    "contains_meta_leak",
    "contains_systemy_copy",
    "is_low_signal_opportunity_title",
    "is_low_signal_scaffold_pain_title",
    "is_placeholder_pain_title",
    "is_low_signal_business_text",
    "looks_like_marketplace_listing",
    "looks_like_raw_post_title",
    "sanitize_business_text",
]
