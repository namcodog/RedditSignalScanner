from __future__ import annotations

"""
Build semantic lexicon v0 for cross-border themes from current toplists.

Inputs (defaults to existing four CSVs under reports/local-acceptance):
  - crossborder-what_to_sell-top200.csv
  - crossborder-how_to_sell-top200.csv
  - crossborder-where_to_sell-top200.csv
  - crossborder-how_to_source-top200.csv

Outputs:
  - backend/config/semantic_sets/crossborder.yml (YAML)
  - reports/local-acceptance/semantic-lexicon-preview.csv (theme,type,term)

Heuristics:
  - Seed with a curated minimal list of brands/features/pain_points relevant to cross-border.
  - Augment brands by extracting platform/vendor tokens from subreddit names in the toplists.
  - Deduplicate and sort; provide lightweight aliases and exclude lists.
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Set

import yaml


DEFAULT_LISTS = [
    Path("reports/local-acceptance/crossborder-what_to_sell-top200.csv"),
    Path("reports/local-acceptance/crossborder-how_to_sell-top200.csv"),
    Path("reports/local-acceptance/crossborder-where_to_sell-top200.csv"),
    Path("reports/local-acceptance/crossborder-how_to_source-top200.csv"),
]

OUT_YAML = Path("backend/config/semantic_sets/crossborder.yml")
OUT_PREVIEW = Path("backend/reports/local-acceptance/semantic-lexicon-preview.csv")


# Minimal curated seeds for v0 (can be extended later)
SEED_BRANDS = {
    "Amazon": ["AMZ", "亚马逊"],
    "Etsy": ["Etsy"],
    "Shopify": ["Shopify"],
    "Walmart": ["Walmart"],
    "eBay": ["Ebay", "易趣"],
    "TikTok Shop": ["TikTok", "抖音海外"],
    "Temu": ["Temu"],
    "Shopee": ["Shopee"],
    "Lazada": ["Lazada"],
    "Alibaba": ["阿里巴巴"],
    "Aliexpress": ["速卖通", "AliExpress"],
    "Kickstarter": ["KS"],
    "Indiegogo": ["Indiegogo"],
}

SEED_FEATURES = [
    "FBA",
    "FBM",
    "listing",
    "PPC",
    "SEO",
    "ACoS",
    "ROAS",
    "CTR",
    "CVR",
    "A/B test",
    "sponsored ads",
    "coupon",
    "discount",
    "returns",
    "refund",
    "chargeback",
    "3PL",
    "fulfillment",
    "MOQ",
    "RFQ",
    "QC",
    "inspection",
    "HS code",
    "VAT",
    "customs",
    "wholesale",
    "private label",
    "white label",
    "dropship",
    "dropshipping",
]

SEED_PAIN_POINTS = [
    "saturated",
    "suspension",
    "policy violation",
    "infringement",
    "trademark",
    "copyright",
    "counterfeit",
    "tax",
    "compliance",
    "logistics delay",
    "lost package",
    "ban",
    "scam",
    "spam",
]

EXCLUDE_NOISE = ["meme", "funny", "gaming", "movie", "anime", "gif", "porn"]


def _read_names(paths: List[Path]) -> List[str]:
    names: List[str] = []
    for p in paths:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw = (row.get("name") or "").strip()
                if raw:
                    names.append(raw)
    return names


def _augment_brands_from_names(names: List[str]) -> Dict[str, List[str]]:
    brands: Dict[str, List[str]] = {k: list(v) for k, v in SEED_BRANDS.items()}
    CANDIDATES = {
        "Amazon": ["Amazon", "AMZ"],
        "Etsy": ["Etsy"],
        "Shopify": ["Shopify"],
        "Walmart": ["Walmart"],
        "eBay": ["eBay", "Ebay"],
        "TikTok Shop": ["TikTok", "tiktokshop", "TikTokShop"],
        "Temu": ["Temu"],
        "Shopee": ["Shopee"],
        "Lazada": ["Lazada"],
        "Alibaba": ["Alibaba"],
        "Aliexpress": ["Aliexpress", "AliExpress"],
        "Kickstarter": ["Kickstarter", "KS"],
        "Indiegogo": ["Indiegogo"],
        "Wix": ["Wix"],
        "BigCommerce": ["BigCommerce"],
        "Mercari": ["Mercari"],
        "Depop": ["Depop"],
        "Poshmark": ["Poshmark"],
        "Etsy Sellers": ["EtsySellers", "EtsyCommunity"],
    }
    for raw in names:
        low = raw.lower()
        for brand, cues in CANDIDATES.items():
            for cue in cues:
                if cue.lower() in low:
                    arr = brands.setdefault(brand, [])
                    # ensure cue present as alias if different form
                    if cue not in arr:
                        arr.append(cue)
    # normalise unique
    return {k: sorted(list(dict.fromkeys(v))) for k, v in brands.items()}


def build_yaml_payload(names: List[str]) -> dict:
    brands = _augment_brands_from_names(names)
    # Basic weights per bucket (can be tuned later)
    weights = {"brands": 1.5, "features": 1.0, "pain_points": 1.2}
    return {
        "version": 0,
        "domain": "crossborder",
        "themes": {
            "what_to_sell": {
                "brands": sorted(brands.keys()),
                "features": sorted(SEED_FEATURES),
                "pain_points": sorted(SEED_PAIN_POINTS),
                "aliases": brands,
                "exclude": EXCLUDE_NOISE,
                "weights": weights,
            },
            "how_to_sell": {
                "brands": sorted(brands.keys()),
                "features": sorted(SEED_FEATURES),
                "pain_points": sorted(SEED_PAIN_POINTS),
                "aliases": brands,
                "exclude": EXCLUDE_NOISE,
                "weights": weights,
            },
            "where_to_sell": {
                "brands": sorted(brands.keys()),
                "features": sorted([t for t in SEED_FEATURES if t not in {"A/B test"}]),
                "pain_points": sorted(SEED_PAIN_POINTS),
                "aliases": brands,
                "exclude": EXCLUDE_NOISE,
                "weights": weights,
            },
            "how_to_source": {
                "brands": sorted(brands.keys()),
                "features": sorted(SEED_FEATURES + ["supplier", "factory", "sourcing", "inspection"]),
                "pain_points": sorted(SEED_PAIN_POINTS + ["MOQ too high", "quality issue", "delay"]),
                "aliases": brands,
                "exclude": EXCLUDE_NOISE,
                "weights": weights,
            },
        },
    }


def write_preview(payload: dict, out_csv: Path) -> None:
    rows: List[Dict[str, str]] = []
    for theme, cfg in payload.get("themes", {}).items():
        for key in ("brands", "features", "pain_points"):
            for term in cfg.get(key, []) or []:
                rows.append({"theme": theme, "type": key, "term": term})
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["theme", "type", "term"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build semantic lexicon v0 for cross-border")
    ap.add_argument("--lists", nargs="*", type=Path, help="Toplist CSV files to learn from")
    ap.add_argument("--output", type=Path, default=OUT_YAML, help="Output YAML path")
    ap.add_argument("--preview", type=Path, default=OUT_PREVIEW, help="Preview CSV path")
    args = ap.parse_args()

    lists = args.lists if args.lists else DEFAULT_LISTS
    names = _read_names(lists)
    payload = build_yaml_payload(names)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    write_preview(payload, args.preview)
    print(f"✅ Semantic lexicon written: {args.output}")
    print(f"📝 Preview: {args.preview}")


if __name__ == "__main__":
    main()

