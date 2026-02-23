from __future__ import annotations


def normalize_subreddit_name(name: str | None) -> str:
    """Return canonical subreddit name: always lowercase and with leading 'r/'.

    Examples:
    - 'r/Fitness' -> 'r/fitness'
    - 'R/fitness' -> 'r/fitness'
    - 'fitness'   -> 'r/fitness'
    - None/空     -> ''
    """
    if not name:
        return ""
    base = str(name).strip()
    # 去掉已有的 r/ 前缀（大小写不敏感）
    if base.lower().startswith("r/"):
        base = base[2:]
    return f"r/{base.lower()}"


def subreddit_key(name: str | None) -> str:
    """Canonical key for internal storage/join (alias)."""
    return normalize_subreddit_name(name)


__all__ = ["normalize_subreddit_name", "subreddit_key"]
