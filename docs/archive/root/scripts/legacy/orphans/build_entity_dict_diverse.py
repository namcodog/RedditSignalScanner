#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


GENERIC_SINGLE = {
    # 通用客套/功能类
    "help", "new", "time", "people", "need", "don", "does", "doing", "way",
    "best", "good", "thanks", "using", "order", "orders", "online", "page", "site",
    "www", "email", "year", "month", "day", "guys", "better",
    # 过于通用的电商词
    "product", "products", "store", "stores", "brand", "brands", "marketing",
    "ad", "ads", "company", "experience", "content", "business", "looking",
    "work", "really", "sell", "selling", "sales", "customer", "customers", "account",
    # 头部单词型高频项（会抬高Top10占比）
    "shipping", "items", "item", "start", "commerce", "dropshipping", "ecommerce",
}

WHITELIST_SINGLE = {"fba", "fbm", "ppc", "seo", "vat", "acos", "roas", "ctr", "cvr", "rfq", "moq", "qc", "3pl", "sku"}

# 单词型痛点高频项（优先用多词短语替换）
PAIN_SINGLE_AVOID = {"issue", "issues", "problem", "problems", "wrong", "bug", "error", "fail", "failure", "failed"}


def load_entity_dict(path: Path) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(row)
    return out


def load_candidates(path: Path) -> List[Tuple[str, str, str, int, float]]:
    out: List[Tuple[str, str, str, int, float]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            can = (row.get("canonical") or "").strip()
            cat = (row.get("category") or "features").strip()
            lay = (row.get("layer") or "L2").strip()
            try:
                freq = int(row.get("freq") or 0)
            except Exception:
                freq = 0
            try:
                score = float(row.get("score") or 0.0)
            except Exception:
                score = 0.0
            out.append((can, cat, lay, freq, score))
    # 优先高分高频
    out.sort(key=lambda x: (-x[4], -x[3]))
    return out


def is_phrase(s: str) -> bool:
    return (" " in s) or ("-" in s) or ("/" in s)


def build_diverse(base_rows: List[Dict[str, str]], cand_rows: List[Tuple[str, str, str, int, float]], *, max_brands: int = 30, min_pains: int = 30, total: int = 100, drop_pain_singles: bool = False, pain_swap_n: int = 10) -> List[Dict[str, str]]:
    # 1) 保留 base 中的 brands≤max_brands、pain_points≥min_pains；features 先收紧
    brands: List[Dict[str, str]] = []
    pains: List[Dict[str, str]] = []
    feats: List[Dict[str, str]] = []
    dropped_pain = 0
    for r in base_rows:
        cat = (r.get("category") or "").strip()
        can = (r.get("canonical") or "").strip()
        low = can.lower()
        if cat == "brands" and len(brands) < max_brands:
            brands.append(r)
        elif cat == "pain_points" and len(pains) < min_pains:
            # 可选：对单词型痛点进行替换（用短语）
            if drop_pain_singles and not is_phrase(can):
                if low in PAIN_SINGLE_AVOID and dropped_pain < pain_swap_n:
                    dropped_pain += 1
                    continue
            pains.append(r)
        elif cat == "features":
            # 严格过滤强泛化单词型特征
            if (low in GENERIC_SINGLE) and not is_phrase(can) and low not in WHITELIST_SINGLE:
                continue
            feats.append(r)

    # 2) 用候选补齐 features（短语优先，非泛化，去重）
    seen = { (r["canonical"] or "").strip().lower() for r in (brands + pains + feats) }
    # 先确保 pain_points 数量下限
    if len(pains) < min_pains or (drop_pain_singles and dropped_pain > 0):
        for can, cat, lay, freq, score in cand_rows:
            if cat != "pain_points":
                continue
            low = can.lower()
            if low in seen:
                continue
            if not is_phrase(can):
                # 痛点也优先短语
                continue
            pains.append({
                "canonical": can,
                "category": "pain_points",
                "source_layer": lay,
                "weight": f"{score:.2f}",
                "norm_weight": "1.00",
                "polarity": "negative",
            })
            seen.add(low)
            if len(pains) >= min_pains and (not drop_pain_singles or dropped_pain <= 0 or len(pains) >= min_pains + dropped_pain):
                break

    target_feats = max(0, total - len(brands) - len(pains))
    for can, cat, lay, freq, score in cand_rows:
        low = can.lower()
        if low in seen:
            continue
        if cat != "features":
            continue
        if not is_phrase(can):
            continue
        if low in GENERIC_SINGLE:
            continue
        feats.append({
            "canonical": can,
            "category": "features",
            "source_layer": lay,
            "weight": f"{score:.2f}",
            "norm_weight": "1.00",
            "polarity": "neutral",
        })
        seen.add(low)
        if len(feats) >= target_feats:
            break

    # 3) 合并并裁剪到 total
    # pains 提前，确保最终裁剪不会挤掉痛点，保障 pain_points 覆盖稳定
    rows = brands + pains + feats
    if len(rows) > total:
        rows = rows[:total]
    return rows


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["canonical", "category", "source_layer", "weight", "norm_weight", "polarity"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def main() -> int:
    ap = argparse.ArgumentParser(description="Build diverse entity dict using candidates")
    ap.add_argument("--base", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2.csv"))
    ap.add_argument("--candidates", type=Path, default=Path("backend/reports/local-acceptance/crossborder_candidates.csv"))
    ap.add_argument("--output", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2_diverse.csv"))
    ap.add_argument("--max-brands", type=int, default=30)
    ap.add_argument("--min-pains", type=int, default=30)
    ap.add_argument("--total", type=int, default=100)
    ap.add_argument("--drop-pain-singles", type=int, default=0)
    ap.add_argument("--pain-swap-n", type=int, default=10)
    args = ap.parse_args()

    base = load_entity_dict(args.base)
    cands = load_candidates(args.candidates)
    rows = build_diverse(
        base,
        cands,
        max_brands=args.max_brands,
        min_pains=args.min_pains,
        total=args.total,
        drop_pain_singles=bool(args.drop_pain_singles),
        pain_swap_n=args.pain_swap_n,
    )
    write_csv(rows, args.output)
    print(f"✅ diverse entity dict written: {args.output} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
