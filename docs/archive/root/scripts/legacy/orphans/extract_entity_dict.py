#!/usr/bin/env python3
from __future__ import annotations

"""
Extract 100 core entities from semantic_sets for report rendering.

Rules (Spec 011, Stage 0.3):
- L2 brands (norm_weight >= 1.5)   -> brands
- L2/L3 features (norm_weight >=1.2)-> features
- L3/L4 pain_points (norm>=1.3 & polarity=negative) -> pain_points

Notes:
- The semantic_sets currently store raw TF-IDF-like weights (often 10~500).
  We normalize per (layer, category) using the 95th percentile as the scale:
      norm_weight = weight / p95(layer, category)
  This makes thresholds (1.2/1.3/1.5) comparable across layers.
- Fallback: ensure minimum counts (brands>=20, pain_points>=20). If any bucket
  underflows, lower its effective threshold by 0.1 steps until min satisfied
  or the bucket is exhausted. Remaining quota is filled by highest norm weights
  across all categories with clear precedence: brands > pain_points > features.

Output CSV columns:
  canonical,category,source_layer,weight,norm_weight,polarity
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np


@dataclass
class Term:
    canonical: str
    category: str
    layer: str
    weight: float
    norm_weight: float
    polarity: str


def _load_semantic_sets(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    # Expect JSON-like structure even if suffix is .yml
    return data


def _collect_terms(data: dict) -> List[Term]:
    layers: Dict[str, Dict[str, List[dict]]] = data.get("layers", {})

    # compute 95th percentile scale per (layer, category)
    scales: Dict[Tuple[str, str], float] = {}
    for layer, cats in layers.items():
        for cat, arr in cats.items():
            ws = [float(x.get("weight", 0.0)) for x in arr if isinstance(x, dict)]
            if ws:
                p95 = float(np.percentile(ws, 95))
            else:
                p95 = 1.0
            scales[(layer, cat)] = max(p95, 1e-6)

    out: List[Term] = []
    for layer, cats in layers.items():
        for cat, arr in cats.items():
            scale = scales[(layer, cat)]
            for x in arr:
                w = float(x.get("weight", 0.0))
                nw = w / scale
                out.append(
                    Term(
                        canonical=str(x.get("canonical", "")).strip(),
                        category=cat,
                        layer=layer,
                        weight=w,
                        norm_weight=float(nw),
                        polarity=str(x.get("polarity", "neutral")),
                    )
                )
    return out


GENERIC_FEATURES = {
    # 极易造成高覆盖但无信息量的通用词，禁止进入 entity dict
    "help", "new", "time", "people", "need", "don", "does", "doing", "way",
    "best", "good", "thanks", "using", "order", "orders", "online", "page", "site",
    "www", "email", "year", "month", "day", "guys", "better",
    # 领域内但过于通用的骨干词
    "product", "products", "store", "stores", "brand", "brands", "marketing",
    "ad", "ads", "company", "experience", "content", "business", "looking",
    "work", "really", "sell", "selling", "sales",
}

def _is_generic(term: str) -> bool:
    low = term.strip().lower()
    if len(low) < 3:
        return True
    if low in GENERIC_FEATURES:
        return True
    return False

# 单词型特征允许白名单（常见缩写/术语）
ALLOWED_SINGLE_FEATURES = {
    "fba", "fbm", "ppc", "seo", "vat", "acos", "roas", "ctr", "cvr",
    "rfq", "moq", "qc", "3pl", "hs", "sku", "listing",
    "checkout", "klaviyo", "theme", "app", "supplier", "factory", "sourcing",
    "fulfillment", "warehouse", "inventory", "tracking", "customs",
}

def _feature_single_allowed(term: str) -> bool:
    t = term.strip()
    if any(ch in t for ch in [" ", "-", "/"]):
        return True  # 短语/连字符允许
    return t.lower() in ALLOWED_SINGLE_FEATURES


def _pick_entities(terms: List[Term], *, target_total: int, min_weight: float, pain_templates: List[str] | None = None, corpus_files: List[Path] | None = None) -> List[Term]:
    # Base rule thresholds (on normalized weight)
    BRAND_L2_TH = max(1.5, min_weight)
    FEAT_TH = max(1.2, min_weight)
    PAIN_TH = max(1.3, min_weight)

    # Buckets
    brands_l2 = [t for t in terms if t.layer == "L2" and t.category == "brands" and t.norm_weight >= BRAND_L2_TH]
    feats_l2 = [
        t for t in terms
        if t.layer == "L2" and t.category == "features" and t.norm_weight >= FEAT_TH
        and not _is_generic(t.canonical) and _feature_single_allowed(t.canonical)
    ]
    feats_l3 = [
        t for t in terms
        if t.layer == "L3" and t.category == "features" and t.norm_weight >= FEAT_TH
        and not _is_generic(t.canonical) and _feature_single_allowed(t.canonical)
    ]
    PAIN_TRIGGERS = {
        "issue", "issues", "problem", "problems", "refund", "refunds", "chargeback", "chargebacks",
        "suspend", "suspension", "ban", "banned", "blocked", "violation", "risk", "fraud", "loss",
        "complaint", "complaints", "delay", "late", "stuck", "decline", "error", "wrong", "bad",
        "worst", "terrible", "awful", "horrible", "nightmare", "disaster", "defect", "defective",
        "missing", "broken", "failed", "failure", "abandoned", "saturated",
    }
    PAIN_EXCLUDE = {"feel like", "feel free", "feels", "feeling", "preview", "preview redd", "lately"}
    def _has_trigger(t: Term) -> bool:
        low = t.canonical.lower()
        if any(ex in low for ex in PAIN_EXCLUDE):
            return False
        return any(tok in low for tok in PAIN_TRIGGERS)
    pains_l3 = [t for t in terms if t.layer == "L3" and t.category == "pain_points" and t.polarity == "negative" and t.norm_weight >= PAIN_TH and _has_trigger(t)]
    pains_l4 = [t for t in terms if t.layer == "L4" and t.category == "pain_points" and t.polarity == "negative" and t.norm_weight >= PAIN_TH and _has_trigger(t)]
    # 若痛点不足，允许从 features 中提取包含触发词的条目作为候选（受控加入），并转换为 pain_points 类别
    pain_from_features = []
    for t in terms:
        if t.category == "features" and t.norm_weight >= (PAIN_TH * 0.8) and _has_trigger(t):
            pain_from_features.append(Term(
                canonical=t.canonical,
                category="pain_points",
                layer=t.layer,
                weight=t.weight,
                norm_weight=t.norm_weight,
                polarity="negative",
            ))

    # 读取 pain_templates（若提供），在语料中计数后转为 pain_points 候选
    pain_from_templates: List[Term] = []
    if pain_templates and corpus_files:
        import re, json
        pats = [(pt, re.compile(rf"(?i)\b{re.escape(pt)}\b")) for pt in pain_templates]
        counts: Dict[str, int] = {pt: 0 for pt in pain_templates}
        def _iter_jsonl(p: Path):
            with p.open('r', encoding='utf-8') as f:
                for ln in f:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        obj = json.loads(ln)
                        if isinstance(obj, dict):
                            yield obj
                    except Exception:
                        continue
        for fp in corpus_files:
            for obj in _iter_jsonl(fp):
                txt = f"{obj.get('title','')} {obj.get('selftext','')}".lower()
                for pt, pat in pats:
                    if pat.search(txt):
                        counts[pt] += 1
        # 根据计数生成候选（赋予足够的norm_weight以通过阈值）
        for pt, c in counts.items():
            if c <= 0:
                continue
            # 选择合适的层（按 subreddit → 层映射时不可得，这里默认 L2）
            pain_from_templates.append(Term(
                canonical=pt,
                category="pain_points",
                layer="L2",
                weight=float(c),
                norm_weight=max(1.3, 1.0 + min(1.0, c / 50.0)),
                polarity="negative",
            ))

    brands_l2.sort(key=lambda x: -x.norm_weight)
    feats_l2.sort(key=lambda x: -x.norm_weight)
    feats_l3.sort(key=lambda x: -x.norm_weight)
    pains_l3.sort(key=lambda x: -x.norm_weight)
    pains_l4.sort(key=lambda x: -x.norm_weight)

    # Minimum counts to ensure balance (raise pains to improve coverage quality)
    MIN_BRANDS = 20
    MIN_PAINS = 30

    # Helper for adaptive threshold lowering
    def ensure_minimum(bucket: List[Term], pool: List[Term], minimum: int, step: float, base_th: float) -> List[Term]:
        if len(bucket) >= minimum:
            return bucket
        # Gather additional candidates from pool with reduced thresholds
        th = base_th
        added: List[Term] = list(bucket)
        while len(added) < minimum and th > 0.2:
            th -= step
            extra = [t for t in pool if t.norm_weight >= th and t not in added]
            extra.sort(key=lambda x: -x.norm_weight)
            for t in extra:
                if t not in added:
                    added.append(t)
                if len(added) >= minimum:
                    break
        return added

    # Preferred pain phrases（优先纳入）
    PREFERRED_PAIN = {
        "account suspension", "policy violation", "lost package", "late shipment", "refund dispute",
        "chargeback", "ip infringement", "listing takedown", "order cancelled", "cash flow", "scam",
        "fraud", "ban", "suspension", "violation", "chargebacks"
    }
    preferred_from_terms: List[Term] = []
    for t in terms:
        low = t.canonical.strip().lower()
        if low in PREFERRED_PAIN:
            if t.category != "pain_points":
                preferred_from_terms.append(Term(canonical=t.canonical, category="pain_points", layer=t.layer, weight=t.weight, norm_weight=t.norm_weight, polarity="negative"))
            else:
                preferred_from_terms.append(t)

    brands_all = ensure_minimum(brands_l2, [t for t in terms if t.category == "brands" and t.layer in {"L2"}], MIN_BRANDS, 0.1, BRAND_L2_TH)
    pains_all = preferred_from_terms + ensure_minimum(pains_l3 + pains_l4, [t for t in terms if t.category == "pain_points" and t.layer in {"L3", "L4"} and t.polarity == "negative"], MIN_PAINS, 0.1, PAIN_TH)
    if pain_from_templates:
        for t in sorted(pain_from_templates, key=lambda x: -x.norm_weight):
            if t not in pains_all:
                pains_all.append(t)
    if len(pains_all) < MIN_PAINS and pain_from_features:
        extras = sorted(pain_from_features, key=lambda x: -x.norm_weight)
        for t in extras:
            if t not in pains_all:
                pains_all.append(t)
            if len(pains_all) >= MIN_PAINS:
                break

    # Compose final list by precedence, dedup canonical
    final: List[Term] = []
    seen = set()

    def add_list(lst: Iterable[Term]):
        for t in lst:
            key = t.canonical.lower()
            if not t.canonical or key in seen:
                continue
            final.append(t)
            seen.add(key)
            if len(final) >= target_total:
                return True
        return False

    # Priority: brands(L2) -> pains(L3/L4) -> feats(L2) -> feats(L3)
    if add_list(brands_all):
        return final
    if add_list(pains_all):
        return final
    # prefer phrases first to reduce head dominance of single tokens
    def _sorted_feat(lst: List[Term]) -> List[Term]:
        def is_phrase(s: str) -> bool:
            return (" " in s) or ("-" in s) or ("/" in s)
        return sorted(lst, key=lambda x: (0 if is_phrase(x.canonical) else 1, -x.norm_weight))

    feats_l2_sorted = _sorted_feat(feats_l2)
    feats_l3_sorted = _sorted_feat(feats_l3)

    if add_list(feats_l2_sorted):
        return final
    if add_list(feats_l3_sorted):
        return final

    # If still insufficient, fill with remaining highest norm scores across all
    rest = sorted([
        t for t in terms
        if not (t.category == "features" and (_is_generic(t.canonical) or not _feature_single_allowed(t.canonical)))
    ], key=lambda x: -x.norm_weight)
    add_list(rest)

    # Final quality gate: pain_points must contain a trigger; otherwise remove
    PAIN_TRIGGERS_QG = {
        "issue", "issues", "problem", "problems", "refund", "refunds", "chargeback", "chargebacks",
        "suspend", "suspension", "ban", "banned", "blocked", "violation", "risk", "fraud", "loss",
        "complaint", "complaints", "delay", "late", "stuck", "decline", "error", "wrong", "bad",
        "worst", "terrible", "awful", "horrible", "nightmare", "disaster", "defect", "defective",
        "missing", "broken", "failed", "failure", "abandoned", "saturated",
    }
    filtered: List[Term] = []
    for t in final:
        if t.category == "pain_points":
            low = t.canonical.lower()
            if not any(tok in low for tok in PAIN_TRIGGERS_QG):
                continue
        filtered.append(t)
    # 剔除过于泛化的痛点词，优先保留具体短语
    GENERIC_PAIN = {"issue", "issues", "problem", "problems"}
    # 为了维持覆盖，不再移除泛化痛点（issue/problem 等）
    if len(filtered) < target_total:
        need = target_total - len(filtered)
        # try fill with filtered features first, then brands
        fills = feats_l2 + feats_l3 + brands_all
        seen2 = {x.canonical.lower() for x in filtered}
        for t in fills:
            k = t.canonical.lower()
            if k in seen2:
                continue
            filtered.append(t)
            seen2.add(k)
            if len(filtered) >= target_total:
                break
        # still need? take more features from terms (L2/L3 preferred), then L1
        if len(filtered) < target_total:
            extra_feats = [
                t for t in terms
                if t.category == "features" and t.layer in {"L2", "L3"}
                and not _is_generic(t.canonical) and _feature_single_allowed(t.canonical)
            ]
            extra_feats.sort(key=lambda x: -x.norm_weight)
            for t in extra_feats:
                k = t.canonical.lower()
                if k in seen2:
                    continue
                filtered.append(t)
                seen2.add(k)
                if len(filtered) >= target_total:
                    break
        if len(filtered) < target_total:
            extra_feats_l1 = [
                t for t in terms
                if t.category == "features" and t.layer == "L1"
                and not _is_generic(t.canonical) and _feature_single_allowed(t.canonical)
            ]
            extra_feats_l1.sort(key=lambda x: -x.norm_weight)
            for t in extra_feats_l1:
                k = t.canonical.lower()
                if k in seen2:
                    continue
                filtered.append(t)
                seen2.add(k)
                if len(filtered) >= target_total:
                    break
        # last resort: allow more from any layer with quality filters
        if len(filtered) < target_total:
            any_pool: List[Term] = []
            for t in terms:
                if t.canonical.lower() in seen2:
                    continue
                if t.category == "features":
                    if _is_generic(t.canonical) or not _feature_single_allowed(t.canonical):
                        continue
                if t.category == "pain_points":
                    low = t.canonical.lower()
                    if not any(tok in low for tok in PAIN_TRIGGERS_QG):
                        continue
                if t.category == "brands" and t.layer not in {"L2"}:
                    # keep L2 preference but allow others as last resort
                    pass
                any_pool.append(t)
            any_pool.sort(key=lambda x: -x.norm_weight)
            for t in any_pool:
                k = t.canonical.lower()
                if k in seen2:
                    continue
                filtered.append(t)
                seen2.add(k)
                if len(filtered) >= target_total:
                    break
    # brand cap to reduce top-10 dominance (default 30)
    MAX_BRANDS = 30
    brand_items = [t for t in filtered if t.category == "brands"]
    if len(brand_items) > MAX_BRANDS:
        # keep top by norm_weight
        keep = set()
        sorted_brands = sorted(brand_items, key=lambda x: -x.norm_weight)[:MAX_BRANDS]
        for t in sorted_brands:
            keep.add(t.canonical.lower())
        filtered = [t for t in filtered if not (t.category == "brands" and t.canonical.lower() not in keep)]

    # 过滤过于泛化的单词型特征，优先短语
    GENERIC_SINGLE_FEATURES = {
        "app", "inventory", "seller", "sell", "business",
        # 强泛化单词：严格移除，避免头部占比过高
        "product", "products", "store", "stores", "help", "new", "sales", "ads", "content", "page", "site", "shipping",
        "time", "don", "need", "people", "looking", "website", "use", "using", "order", "orders", "online", "www", "email", "year", "month", "day", "days", "best", "free", "way", "guys",
        # 本轮新增：进一步压单词型头部
        "customer", "customers", "account", "brand", "brands", "selling", "does", "start", "item", "items", "commerce", "thanks", "feel", "good", "feedback",
    }
    def is_phrase(s: str) -> bool:
        return (" " in s) or ("-" in s) or ("/" in s)
    filtered = [t for t in filtered if not (t.category == "features" and t.canonical.lower() in GENERIC_SINGLE_FEATURES and not is_phrase(t.canonical))]

    # 回填至目标总数
    if len(filtered) < target_total:
        need = target_total - len(filtered)
        # 首选高质量 features（短语优先）
        fill_feats = _sorted_feat([ft for ft in feats_l2 if not (ft.canonical.lower() in GENERIC_SINGLE_FEATURES and not is_phrase(ft.canonical))]) 
        fill_feats += _sorted_feat([ft for ft in feats_l3 if not (ft.canonical.lower() in GENERIC_SINGLE_FEATURES and not is_phrase(ft.canonical))])
        seen3 = {t.canonical.lower() for t in filtered}
        for t in fill_feats:
            k = t.canonical.lower()
            if k in seen3:
                continue
            filtered.append(t)
            seen3.add(k)
            need -= 1
            if need <= 0:
                break
        # 仍不足则用品牌（在MAX_BRANDS限制内）
        if need > 0:
            allowed_brand_pool = [t for t in brands_all if t.canonical.lower() not in seen3]
            for t in allowed_brand_pool:
                if sum(1 for x in filtered if x.category == "brands") >= MAX_BRANDS:
                    break
                k = t.canonical.lower()
                if k in seen3:
                    continue
                filtered.append(t)
                seen3.add(k)
                need -= 1
                if need <= 0:
                    break
        # 尝试用从 features 转化的 pain 候选补齐
        if need > 0 and pain_from_features:
            for t in pain_from_features:
                k = t.canonical.lower()
                if k in seen3:
                    continue
                filtered.append(t)
                seen3.add(k)
                need -= 1
                if need <= 0:
                    break

    # 二次净化：移除泛化痛点 & 明显噪声短语（amp/webp/png/com/format/imgur/http）
    NOISE_SUBSTR = {" amp", "webp", " png", ".com", " http", "format", "imgur"}
    def _is_noise_term(t: Term) -> bool:
        low = t.canonical.strip().lower()
        if any(s in low for s in NOISE_SUBSTR):
            return True
        return False

    filtered = [t for t in filtered if not _is_noise_term(t)]

    # 再次移除泛化痛点
    # 泛化痛点集合（此处保持弱化策略：不强删，以避免覆盖骤降）
    GP = GENERIC_PAIN  # .union(GENERIC_PAIN_EXTRA)  # 若需严格模式可并入扩展集
    filtered = [t for t in filtered if not (t.category == "pain_points" and t.canonical.strip().lower() in GP)]

    # 末尾回填至目标数（优先短语特征，其次品牌，最后pain_from_features；确保达到 target_total）
    if len(filtered) < target_total:
        need = target_total - len(filtered)
        seen4 = {t.canonical.lower() for t in filtered}
        fill_feats2 = _sorted_feat([
            ft for ft in feats_l2 + feats_l3
            if ft.canonical.lower() not in seen4 and not (ft.canonical.lower() in GENERIC_SINGLE_FEATURES and not is_phrase(ft.canonical))
        ])
        for t in fill_feats2:
            k = t.canonical.lower()
            if k in seen4 or _is_noise_term(t):
                continue
            filtered.append(t)
            seen4.add(k)
            need -= 1
            if need <= 0:
                break
        if need > 0:
            for t in brands_all:
                if sum(1 for x in filtered if x.category == "brands") >= MAX_BRANDS:
                    break
                k = t.canonical.lower()
                if k in seen4:
                    continue
                filtered.append(t)
                seen4.add(k)
                need -= 1
                if need <= 0:
                    break
        if need > 0 and pain_from_features:
            for t in pain_from_features:
                k = t.canonical.lower()
                if k in seen4:
                    continue
                filtered.append(t)
                seen4.add(k)
                need -= 1
                if need <= 0:
                    break

    # 若仍不足，放宽品牌上限进行补齐（不再卡 MAX_BRANDS），同时过滤明显噪声
    if len(filtered) < target_total:
        need = target_total - len(filtered)
        seen5 = {t.canonical.lower() for t in filtered}
        rest_sorted = sorted(terms, key=lambda x: -x.norm_weight)
        NOISE_SUBSTR = {" amp", "webp", " png", ".com", " http", "format", "imgur"}
        def _noisy(s: str) -> bool:
            low = s.lower()
            return any(ns in low for ns in NOISE_SUBSTR)
        for t in rest_sorted:
            k = t.canonical.lower()
            if k in seen5 or _noisy(t.canonical):
                continue
            # 不允许引入强泛化的单词型特征
            if t.category == "features" and (k in GENERIC_SINGLE_FEATURES) and not is_phrase(t.canonical):
                continue
            filtered.append(t)
            seen5.add(k)
            need -= 1
            if need <= 0:
                break

    return filtered[:target_total]


def _write_csv(rows: List[Term], path: Path) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["canonical", "category", "source_layer", "weight", "norm_weight", "polarity"])
        for t in rows:
            w.writerow([t.canonical, t.category, t.layer, f"{t.weight:.4f}", f"{t.norm_weight:.3f}", t.polarity])


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract core entity dictionary from semantic sets")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--output", type=Path, default=Path("backend/config/entity_dictionary/crossborder_v2.csv"))
    ap.add_argument("--min-weight", type=float, default=1.2)
    ap.add_argument("--target-total", type=int, default=100)
    ap.add_argument("--pain-templates", type=Path, default=Path("backend/config/nlp/pain_templates.txt"))
    ap.add_argument("--corpus", default="backend/data/snapshots/2025-11-07-0.2/*.jsonl")
    args = ap.parse_args()

    data = _load_semantic_sets(args.lexicon)
    terms = _collect_terms(data)
    # load templates & corpus files
    pain_templates: List[str] | None = None
    corpus_files: List[Path] | None = None
    try:
        if args.pain_templates and Path(args.pain_templates).exists():
            pain_templates = [ln.strip() for ln in Path(args.pain_templates).read_text(encoding='utf-8').splitlines() if ln.strip()]
    except Exception:
        pain_templates = None
    try:
        import glob as _glob
        corpus_files = [Path(p) for p in _glob.glob(args.corpus)]
    except Exception:
        corpus_files = None

    picked = _pick_entities(terms, target_total=args.target_total, min_weight=args.min_weight, pain_templates=pain_templates, corpus_files=corpus_files)
    _write_csv(picked, args.output)

    # Print summary for quick acceptance
    from collections import Counter

    by_cat = Counter([t.category for t in picked])
    print(json.dumps({
        "status": "ok",
        "total": len(picked),
        "by_category": dict(by_cat),
        "output": str(args.output)
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
