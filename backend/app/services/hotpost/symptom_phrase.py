from __future__ import annotations

import re


_PRECISE_PATTERNS = (
    r"(keeps track of [^.,;!?]{4,56})",
    r"(keeps full context[^.,;!?]{0,28})",
    r"(keeps the whole task[^.,;!?]{0,28})",
    r"(keeps the whole brief[^.,;!?]{0,28})",
    r"(retains? context[^.,;!?]{0,28})",
    r"(follows all requirements[^.,;!?]{0,28})",
    r"(follows long instructions[^.,;!?]{0,28})",
    r"(follows the whole brief[^.,;!?]{0,28})",
    r"(drops? constraints[^.,;!?]{0,36})",
    r"(ignores? parts of the prompt[^.,;!?]{0,28})",
    r"(forgets? earlier requirements[^.,;!?]{0,28})",
    r"(loses? context[^.,;!?]{0,28})",
    r"(only does the first half[^.,;!?]{0,28})",
    r"(derails after [^.,;!?]{4,36})",
    r"(miss(?:es|ing) parts of the brief[^.,;!?]{0,24})",
    r"(rewrit(?:e|es|ing) [^.,;!?]{4,56})",
    r"(crash(?:es|ing)? [^.,;!?]{2,40})",
    r"(freez(?:e|es|ing) [^.,;!?]{2,40})",
    r"(总是[^，。！？]{2,24})",
    r"(每次[^，。！？]{2,24})",
    r"(经常[^，。！？]{2,24})",
    r"(老是[^，。！？]{2,24})",
    r"(不如[^，。！？]{2,24})",
    r"(听不懂[^，。！？]{2,24})",
    r"(改写成[^，。！？]{2,24})",
    r"(退款[^，。！？]{2,24})",
    r"(客服[^，。！？]{2,24})",
)

_FALLBACK_PATTERNS = (
    r"(follows [^.,;!?]{4,64})",
    r"(keeps [^.,;!?]{4,64})",
    r"(retains? [^.,;!?]{4,64})",
    r"(loses? [^.,;!?]{4,64})",
    r"(forgets? [^.,;!?]{4,64})",
    r"(miss(?:es|ing) [^.,;!?]{4,64})",
    r"(only does [^.,;!?]{4,64})",
    r"(every time [^.,;!?]{4,40})",
    r"(always [^.,;!?]{4,40})",
    r"(drops? [^.,;!?]{4,64})",
    r"(rewrit(?:e|es|ing) [^.,;!?]{4,64})",
    r"(crash(?:es|ing)? [^.,;!?]{2,40})",
    r"(freez(?:e|es|ing) [^.,;!?]{2,40})",
    r"(总是[^，。！？]{2,24})",
    r"(每次[^，。！？]{2,24})",
    r"(经常[^，。！？]{2,24})",
    r"(老是[^，。！？]{2,24})",
    r"(不如[^，。！？]{2,24})",
    r"(听不懂[^，。！？]{2,24})",
    r"(改写成[^，。！？]{2,24})",
    r"(退款[^，。！？]{2,24})",
    r"(客服[^，。！？]{2,24})",
)

_SPLIT_MARKERS = (
    " and ",
    " but ",
    " while ",
    " because ",
    " so ",
    " instead of ",
    " whereas ",
    " though ",
    "，但",
    "但是",
    "然后",
)


def _safe_trim(phrase: str, *, max_chars: int) -> str:
    if len(phrase) <= max_chars:
        return phrase
    trimmed = phrase[:max_chars].rstrip()
    if " " in trimmed:
        return trimmed.rsplit(" ", 1)[0].strip("，。,.!?！？;: ")
    return trimmed


def _finalize_phrase(candidate: str) -> str:
    phrase = " ".join(str(candidate).split()).strip("，。,.!?！？;: ")
    lowered = phrase.lower()
    for marker in _SPLIT_MARKERS:
        idx = lowered.find(marker)
        if idx > 0:
            phrase = phrase[:idx].strip("，。,.!?！？;: ")
            lowered = phrase.lower()
    return _safe_trim(phrase, max_chars=40)


def extract_symptom_phrase(quote: str) -> str:
    cleaned = " ".join(str(quote or "").split())
    if not cleaned:
        return ""
    for pattern in _PRECISE_PATTERNS:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            phrase = _finalize_phrase(match.group(1))
            if phrase:
                return phrase
    for pattern in _FALLBACK_PATTERNS:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            phrase = _finalize_phrase(match.group(1))
            if phrase:
                return phrase
    return _finalize_phrase(cleaned[:48]) or cleaned[:32]


__all__ = ["extract_symptom_phrase"]
