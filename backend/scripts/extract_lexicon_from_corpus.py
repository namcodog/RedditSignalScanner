#!/usr/bin/env python3
"""
从阶段 0 语料中提取四层语义（L1-L4）并生成 500 词的语义库（semantic_sets）。

设计目标：
- 离线友好：Sentence-Transformers、KeyBERT 不可用时自动降级（使用 TF-IDF + Hashing 相似度）
- 可配置：目标总数、最小频次、相似度阈值
- 可追溯：可选导出 layer_mapping.csv

输出：
- YAML（以 JSON 形式输出到 .yml，YAML 能兼容 JSON 语法）
- 可选 CSV：canonical,layer,category,weight,polarity,precision_tag

用法：
  python backend/scripts/extract_lexicon_from_corpus.py \
    --corpus "backend/data/reddit_corpus/*.jsonl" \
    --L1-baseline backend/config/semantic_sets/L1_baseline_embeddings.pkl \
    --output backend/config/semantic_sets/crossborder_v2.0.yml \
    --target-total-terms 500 \
    --min-freq 3 \
    --output-mapping backend/config/semantic_sets/layer_mapping.csv
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import glob
import json
import math
import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer, HashingVectorizer


# ----------------------------- 常量与类型 -----------------------------

NEGATIVE_TOKENS = {
    "scam",
    "saturated",
    "too competitive",
    "refund",
    "chargeback",
    "suspend",
    "suspension",
    "ban",
    "blocked",
    "violation",
    "risk",
    "fraud",
    "loss",
    "complaint",
    "delay",
    "stuck",
    "decline",
    "issue",
    "problem",
    "bug",
}

KNOWN_BRANDS = {
    "Amazon",
    "Shopify",
    "Klaviyo",
    "eBay",
    "Etsy",
    "Walmart",
    "TikTok",
    "Meta",
    "Facebook",
    "Google",
}

# 扩展停用词列表（sklearn 的 'english' 不够全面）
EXTENDED_STOPWORDS = {
    "the", "and", "for", "you", "that", "with", "what", "this", "have", "are",
    "but", "your", "how", "can", "from", "they", "just", "like", "any", "not",
    "was", "been", "has", "had", "were", "will", "would", "could", "should",
    "may", "might", "must", "shall", "can", "could", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why", "all",
    "each", "other", "some", "such", "only", "own", "same", "than", "too",
    "very", "can", "will", "just", "don", "should", "now", "get", "make",
    "know", "think", "take", "see", "come", "want", "look", "use", "find",
    "give", "tell", "work", "call", "try", "ask", "need", "feel", "become",
    "leave", "put", "mean", "keep", "let", "begin", "seem", "help", "talk",
    "turn", "start", "show", "hear", "play", "run", "move", "live", "believe",
    "hold", "bring", "happen", "write", "provide", "sit", "stand", "lose",
    "pay", "meet", "include", "continue", "set", "learn", "change", "lead",
    "understand", "watch", "follow", "stop", "create", "speak", "read", "allow",
    "add", "spend", "grow", "open", "walk", "win", "offer", "remember", "love",
    "consider", "appear", "buy", "wait", "serve", "die", "send", "expect",
    "build", "stay", "fall", "cut", "reach", "kill", "remain", "suggest",
    "raise", "pass", "sell", "require", "report", "decide", "pull",
}


LAYER_BY_SUBREDDIT = {
    "ecommerce": "L1",
    "AmazonSeller": "L2",
    "Shopify": "L2",  # 亦承担 L3 语义
    "dropship": "L3",  # 亦承担 L4 情绪
    "dropshipping": "L4",
}


@dataclass
class Baseline:
    terms: List[str]
    embeddings: np.ndarray
    meta: dict


# ----------------------------- 工具函数 -----------------------------

def _iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
            except Exception:
                continue


def _normalise_subreddit(name: str) -> str:
    # 纠正规范名（处理 shopify → Shopify 等大小写差异）
    key = name.strip()
    if not key:
        return key
    if key.lower() == "shopify":
        return "Shopify"
    if key.lower() == "amazonseller":
        return "AmazonSeller"
    return key


def _load_posts(paths: List[Path]) -> List[dict]:
    rows: List[dict] = []
    for p in paths:
        for obj in _iter_jsonl(p):
            obj["subreddit"] = _normalise_subreddit(str(obj.get("subreddit", "")))
            rows.append(obj)
    return rows


def _texts_by_layer(rows: List[dict]) -> Dict[str, List[str]]:
    buckets: Dict[str, List[str]] = {"L1": [], "L2": [], "L3": [], "L4": []}
    for r in rows:
        sub = str(r.get("subreddit", ""))
        layer = LAYER_BY_SUBREDDIT.get(sub)
        if not layer:
            continue
        text = f"{r.get('title','')} {r.get('selftext','')}".strip()
        if text:
            buckets[layer].append(text)
    return buckets


def _extract_candidates(texts: List[str], *, max_features: int = 1000) -> List[Tuple[str, float, int]]:
    """返回[(term, tfidf_score, freq)]。包含 1-3gram 以兼顾单词与短语。"""
    if not texts:
        return []
    # 小样本兼容：当文本数不足 2 时降级 min_df=1，避免空词表报错
    min_df = 1 if len(texts) < 2 else 2
    try:
        tfidf = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=max_features,
            min_df=min_df,
            stop_words='english'  # 过滤英文停用词
        )
        X = tfidf.fit_transform(texts)
        features = list(tfidf.get_feature_names_out())
        tfidf_scores = np.asarray(X.sum(axis=0)).ravel()
        if not features:
            return []
    except ValueError:
        return []

    # 频次
    try:
        cnt = CountVectorizer(ngram_range=(1, 3), vocabulary=features, stop_words='english')
        C = cnt.fit_transform(texts)
        freqs = np.asarray(C.sum(axis=0)).ravel()
    except ValueError:
        return []

    order = np.argsort(-tfidf_scores)
    result: List[Tuple[str, float, int]] = [
        (features[i], float(tfidf_scores[i]), int(freqs[i])) for i in order
    ]
    return result


def _load_baseline(path: Path) -> Baseline:
    with path.open("rb") as f:
        b: Baseline = pickle.load(f)
        # 基线兼容性：若是旧格式 dict
        if isinstance(b, dict):  # type: ignore[truthy-bool]
            return Baseline(terms=b["terms"], embeddings=b["embeddings"], meta=b.get("meta", {}))
        return b


def _encode_terms(terms: List[str], baseline: Baseline) -> np.ndarray:
    # 与基线一致的降级策略：若 meta.method 以 "st::" 开头，尝试同模型，否则使用 HashingVectorizer
    method = str(baseline.meta.get("method", ""))
    if method.startswith("st::"):
        model_name = method.split("::", 1)[1]
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            model = SentenceTransformer(model_name)
            return np.asarray(model.encode(terms), dtype=float)
        except Exception:
            pass
    # 回退 Hashing，维度与基线保持一致
    dim = int(baseline.embeddings.shape[1] if baseline.embeddings.size else 128)
    hv = HashingVectorizer(
        analyzer="char", ngram_range=(3, 5), n_features=dim, alternate_sign=False
    )
    return hv.transform(terms).toarray()


def _cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if b.ndim == 1:
        b = b.reshape(1, -1)
    a_n = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_n = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return float((a_n @ b_n.T).max())


def _categorise(term: str) -> str:
    # 简单分类：包含负向词 → pain_points；首字母大写/已知品牌 → brands；其它 → features
    t = term.strip()
    low = t.lower()
    for neg in NEGATIVE_TOKENS:
        if neg in low:
            return "pain_points"
    if (t[:1].isupper() and " " not in t) or (t.split(" ")[0] in KNOWN_BRANDS):
        return "brands"
    return "features"


def _precision_tag(term: str, category: str) -> str:
    if category == "brands":
        return "exact"
    if " " in term or "-" in term or "/" in term:
        return "phrase"
    return "phrase"


def _polarity(category: str) -> str:
    return "negative" if category == "pain_points" else "neutral"


def _distribute_target(total: int) -> Dict[str, int]:
    # 近似分配到各层：L1 22%，L2 28%，L3 22%，L4 28%（向上取整）
    alloc = {
        "L1": int(math.ceil(total * 0.22)),
        "L2": int(math.ceil(total * 0.28)),
        "L3": int(math.ceil(total * 0.22)),
        "L4": total,  # 占位，后续纠偏
    }
    used = alloc["L1"] + alloc["L2"] + alloc["L3"]
    alloc["L4"] = max(0, total - used)
    return alloc


def _select_terms(
    candidates: List[Tuple[str, float, int]],
    *,
    baseline: Baseline,
    min_freq: int,
    per_layer_quota: int,
    sim_threshold: float,
) -> List[dict]:
    selected: List[dict] = []
    terms: List[str] = []
    weights: List[float] = []
    for term, w, freq in candidates:
        if freq < min_freq:
            continue
        # 过滤停用词（单词级别）
        if term.lower() in EXTENDED_STOPWORDS:
            continue
        # 过滤纯数字
        if term.isdigit():
            continue
        # 过滤过短的词（单字母）
        if len(term) <= 1:
            continue
        terms.append(term)
        weights.append(float(w))
        if len(terms) >= per_layer_quota * 3:  # 候选池上限（冗余）
            break
    if not terms:
        return []
    embs = _encode_terms(terms, baseline)
    # 与基线比较，过滤掉相似度过低的术语（防止跑偏）
    filtered: List[dict] = []
    for i, term in enumerate(terms):
        sim = _cos_sim(embs[i], baseline.embeddings)
        if sim < sim_threshold:
            continue
        cat = _categorise(term)
        filtered.append(
            {
                "canonical": term,
                "aliases": [],
                "precision_tag": _precision_tag(term, cat),
                "weight": float(weights[i]),
                "polarity": _polarity(cat),
                "category": cat,
            }
        )
        if len(filtered) >= per_layer_quota:
            break
    return filtered


def _build_output_structure() -> Dict[str, Dict[str, List[dict]]]:
    def _empty_layer() -> Dict[str, List[dict]]:
        return {"brands": [], "features": [], "pain_points": []}

    return {"L1": _empty_layer(), "L2": _empty_layer(), "L3": _empty_layer(), "L4": _empty_layer()}


def extract_lexicon(
    corpus_files: List[Path],
    baseline_path: Path,
    *,
    target_total: int = 500,
    min_freq: int = 3,
    sim_threshold: float = 0.2,
) -> Tuple[Dict[str, Dict[str, List[dict]]], List[dict]]:
    baseline = _load_baseline(baseline_path)
    rows = _load_posts(corpus_files)
    texts_layer = _texts_by_layer(rows)
    alloc = _distribute_target(target_total)

    out = _build_output_structure()
    mapping_rows: List[dict] = []

    for layer, texts in texts_layer.items():
        if not texts:
            continue
        per_layer_quota = alloc.get(layer, 0)
        cands = _extract_candidates(texts, max_features=max(1000, per_layer_quota * 6))
        chosen = _select_terms(
            cands, baseline=baseline, min_freq=min_freq, per_layer_quota=per_layer_quota, sim_threshold=sim_threshold
        )
        for item in chosen:
            out[layer][item["category"]].append(
                {k: item[k] for k in ("canonical", "aliases", "precision_tag", "weight", "polarity")}
            )
            mapping_rows.append(
                {
                    "canonical": item["canonical"],
                    "layer": layer,
                    "category": item["category"],
                    "weight": item["weight"],
                    "polarity": item["polarity"],
                    "precision_tag": item["precision_tag"],
                }
            )

    return out, mapping_rows


def _write_yaml_as_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_mapping_csv(rows: List[dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["canonical", "layer", "category", "weight", "polarity", "precision_tag"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _resolve_glob(pattern: str) -> List[Path]:
    base = Path(os.getcwd())
    if any(ch in pattern for ch in "*?[]"):
        return [Path(p) for p in glob.glob(pattern)]
    # 允许传目录
    p = Path(pattern)
    if p.is_dir():
        return list(sorted(p.glob("*.jsonl")))
    return [p]


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract four-layer semantic lexicon from corpus")
    ap.add_argument("--corpus", required=True, help="Glob pattern or directory of JSONL files")
    ap.add_argument("--L1-baseline", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--target-total-terms", type=int, default=500)
    ap.add_argument("--min-freq", type=int, default=3)
    ap.add_argument("--sim-threshold", type=float, default=0.2)
    ap.add_argument("--output-mapping", default="")
    args = ap.parse_args()

    files = _resolve_glob(args.corpus)
    if not files:
        print(json.dumps({"status": "error", "message": "no corpus files"}, ensure_ascii=False))
        return 2

    lexicon, mapping = extract_lexicon(
        files,
        Path(args.__dict__["L1_baseline"]) if hasattr(args, "L1_baseline") else Path(args.__dict__["L1-baseline"]),
        target_total=int(args.__dict__["target_total_terms"]),
        min_freq=int(args.min_freq),
        sim_threshold=float(args.__dict__["sim_threshold"]),
    )

    # 补元数据与计数
    def _count_terms(layer_obj: Dict[str, List[dict]]) -> int:
        return sum(len(v) for v in layer_obj.values())

    counts = {layer: _count_terms(obj) for layer, obj in lexicon.items()}
    total = sum(counts.values())

    payload = {
        "version": "v2.0",
        "domain": "crossborder",
        "layers": lexicon,
        "stats": {"by_layer": counts, "total": total},
    }

    out_path = Path(args.output)
    _write_yaml_as_json(payload, out_path)
    if args.output_mapping:
        _write_mapping_csv(mapping, Path(args.output_mapping))

    print(json.dumps({"status": "ok", "total": total, "by_layer": counts, "output": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
