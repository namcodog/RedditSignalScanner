from __future__ import annotations

"""
Suggest pain_points and alias candidates from real posts for cross-border themes.

Outputs two CSVs under backend/reports/local-acceptance/:
  - semantic-suggested-pain_points.csv (theme,phrase,count,examples)
  - semantic-suggested-aliases.csv    (theme,brand,candidate,count,examples)

Heuristics:
  - Pain points are extracted as 1-3 gram phrases containing complaint triggers
    (ban/suspension/policy/delay/refund/chargeback/VAT/customs/侵权/封号/延迟...)
  - Alias candidates are surface forms close to known brands (case/spacing variants,
    common abbreviations like AMZ/TTS/KS/IGG) observed in texts.
"""

import argparse
import asyncio
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import yaml

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient, RedditAPIError


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO_ROOT / "backend" / "reports" / "local-acceptance"

TRIGGERS = {
    # English
    "ban", "banned", "suspend", "suspension", "policy", "violation", "violate",
    "refund", "return", "chargeback", "spam", "scam", "fraud", "locked", "gated",
    "late", "delay", "delayed", "damaged", "lost", "missing", "broken", "out of stock",
    "vat", "tax", "customs", "duty", "seized", "hold", "blocked", "infringement",
    "copyright", "trademark", "takedown", "strike",
    # Chinese
    "封号", "冻结", "违规", "申诉", "侵权", "合规", "关税", "扣留", "清关", "延迟", "丢件",
}

ABBR_HINTS = {
    "Amazon": ["AMZ"],
    "TikTok Shop": ["TikTokShop", "TTS", "TikTok"],
    "Kickstarter": ["KS"],
    "Indiegogo": ["IGG"],
    "AliExpress": ["Aliexpress", "速卖通"],
}

TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9\-+/]{2,}||\w+")


def load_lexicon(path: Path) -> Dict[str, Dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("themes", {})


def _read_toplist(theme: str) -> List[str]:
    # Prefer semantic top200 if present, else fallback to classic under repo root
    repo_root = Path(__file__).resolve().parents[2]
    prefer = repo_root / f"reports/local-acceptance/crossborder-semantic-{theme}-top200.csv"
    fallback = repo_root / f"reports/local-acceptance/crossborder-{theme}-top200.csv"
    paths = [prefer, fallback]
    names: List[str] = []
    for p in paths:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                n = (row.get("name") or "").strip()
                if n:
                    names.append(n if n.startswith("r/") else f"r/{n}")
        break
    return names


async def fetch_posts(client: RedditAPIClient, subreddit: str, *, limit: int) -> List[str]:
    raw = subreddit[2:] if subreddit.lower().startswith("r/") else subreddit
    try:
        posts = await client.fetch_subreddit_posts(raw, limit=limit, time_filter="month", sort="top")
    except (RedditAPIError, Exception):
        return []
    texts: List[str] = []
    for p in posts:
        if p.title:
            texts.append(p.title)
        if p.selftext:
            texts.append(p.selftext)
    return texts


def _ngrams(tokens: List[str], n: int) -> Iterable[str]:
    for i in range(0, max(0, len(tokens) - n + 1)):
        yield " ".join(tokens[i : i + n])


def _contains_trigger(phrase: str) -> bool:
    low = phrase.lower()
    for t in TRIGGERS:
        if t.lower() in low:
            return True
    return False


def extract_pain_points(texts: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for txt in texts:
        toks = [t for t in TOKEN.findall(txt or "") if t and not t.isspace()]
        # 1-gram
        for g in toks:
            if _contains_trigger(g):
                counts[g.lower()] += 1
        # 2/3-gram
        for n in (2, 3):
            for g in _ngrams(toks, n):
                if _contains_trigger(g):
                    counts[g.lower()] += 1
    return counts


def extract_aliases(texts: List[str], brands: List[str]) -> Dict[str, Dict[str, int]]:
    seen: Dict[str, Dict[str, int]] = {b: defaultdict(int) for b in brands}
    all_txt = "\n".join(texts)
    for b in brands:
        # naive variants: case-insensitive and space-stripped occurrences
        variants = set()
        variants.add(b)
        variants.add(b.replace(" ", ""))
        for hint in ABBR_HINTS.get(b, []):
            variants.add(hint)
        for v in variants:
            pat = re.compile(re.escape(v), re.IGNORECASE)
            for m in pat.finditer(all_txt):
                form = m.group(0)
                seen[b][form] += 1
    # remove canonical exact match, keep others
    out: Dict[str, Dict[str, int]] = {}
    for b, forms in seen.items():
        cand: Dict[str, int] = {}
        for form, cnt in forms.items():
            if form.lower() == b.lower():
                continue
            cand[form] = cnt
        if cand:
            out[b] = cand
    return out


async def main() -> None:
    ap = argparse.ArgumentParser(description="Suggest pain_points and aliases from posts")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder.yml"))
    ap.add_argument("--per-theme", type=int, default=20, help="communities per theme to sample")
    ap.add_argument("--posts-per", type=int, default=10)
    args = ap.parse_args()

    themes = load_lexicon(args.lexicon)

    settings = get_settings()
    client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=max(2, settings.reddit_max_concurrency // 2),
    )

    pain_rows: List[Dict[str, str]] = []
    alias_rows: List[Dict[str, str]] = []

    async with client:
        for theme in ("what_to_sell", "how_to_sell", "where_to_sell", "how_to_source"):
            names = _read_toplist(theme)[: args.per_theme]
            # fetch posts
            texts: List[str] = []
            for n in names:
                texts.extend(await fetch_posts(client, n, limit=args.posts_per))

            # pain points
            pcount = extract_pain_points(texts)
            top_pain = sorted(pcount.items(), key=lambda x: x[1], reverse=True)[: 50]
            for phrase, cnt in top_pain:
                pain_rows.append({
                    "theme": theme,
                    "phrase": phrase,
                    "count": str(cnt),
                    "examples": "",
                })

            # aliases
            brands = list(themes.get(theme, {}).get("brands", []) or [])
            alias_map = extract_aliases(texts, brands)
            for brand, forms in alias_map.items():
                top_alias = sorted(forms.items(), key=lambda x: x[1], reverse=True)[: 20]
                for cand, cnt in top_alias:
                    alias_rows.append({
                        "theme": theme,
                        "brand": brand,
                        "candidate": cand,
                        "count": str(cnt),
                    })

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pain_csv = REPORT_DIR / "semantic-suggested-pain_points.csv"
    alias_csv = REPORT_DIR / "semantic-suggested-aliases.csv"
    with pain_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["theme", "phrase", "count", "examples"])
        writer.writeheader()
        for r in pain_rows:
            writer.writerow(r)
    with alias_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["theme", "brand", "candidate", "count"])
        writer.writeheader()
        for r in alias_rows:
            writer.writerow(r)

    print(f"✅ Suggested pain points: {pain_csv}")
    print(f"✅ Suggested aliases:     {alias_csv}")


if __name__ == "__main__":
    asyncio.run(main())
