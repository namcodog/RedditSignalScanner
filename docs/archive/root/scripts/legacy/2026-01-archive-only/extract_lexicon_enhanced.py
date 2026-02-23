#!/usr/bin/env python3
"""
增强版语义词库提取脚本（Stage 0.2）

新增功能：
1. 使用 spacy NER 识别品牌/组织（ORG, PRODUCT）
2. 使用 textblob 情感分析识别痛点
3. 使用 KeyBERT 提取关键短语和别名
4. 生成高质量的 500 词语义库

用法：
  python backend/scripts/extract_lexicon_enhanced.py \
    --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
    --L1-baseline backend/config/semantic_sets/L1_baseline_embeddings.pkl \
    --output backend/config/semantic_sets/crossborder_v2.1.yml \
    --target-total-terms 500 \
    --min-freq 3 \
    --output-mapping backend/config/semantic_sets/layer_mapping.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from collections import Counter, defaultdict
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

import numpy as np
import spacy
from keybert import KeyBERT
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from textblob import TextBlob

# 加载 NLP 模型
print("🔄 加载 NLP 模型...")
_HAS_NER = True
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    # 降级：无预训练模型时使用 blank 英文模型，相关函数将回退到正则
    nlp = spacy.blank("en")
    _HAS_NER = False
kw_model = KeyBERT()
print(f"✅ NLP 模型加载完成 (NER={'on' if _HAS_NER else 'off'})")

# 常量
NEGATIVE_TOKENS = {
    "scam", "saturated", "competitive", "refund", "refunds", "chargeback", "chargebacks",
    "suspend", "suspension", "ban", "blocked", "violation", "risk", "fraud", "loss",
    "complaint", "complaints", "delay", "delayed", "late", "stuck", "decline", "declined",
    "issue", "issues", "problem", "problems", "bug", "fail", "failed", "failure", "error",
    "wrong", "bad", "worst", "terrible", "awful", "horrible", "nightmare", "disaster",
    "frustrat", "disappoint", "broken", "defect", "defective", "damaged", "missing",
    "cancel", "cancellation", "warning", "strike",
}

# 痛点启发式（用于不足时的回填）
PAIN_HEURISTIC_TOKENS = NEGATIVE_TOKENS.union(
    {
        "return", "returns", "fee", "fees", "penalty", "duty", "customs", "strike",
        "complaint", "charge", "charges", "review", "negative", "delay", "late",
        "defect", "broken", "warranty",
    }
)

KNOWN_BRANDS = {
    # 平台/电商/支付/社媒/工具（可按需继续扩充）
    "Amazon", "Shopify", "Klaviyo", "eBay", "Etsy", "Walmart", "TikTok", "TikTok Shop",
    "Meta", "Facebook", "Google", "Instagram", "Pinterest", "Stripe", "PayPal",
    "AliExpress", "Alibaba", "DHgate", "Oberlo", "Spocket", "Temu", "Shopee", "Lazada",
    "Kickstarter", "Indiegogo", "Wix", "BigCommerce", "Mercari", "Depop", "Poshmark",
    "Klarna", "WooCommerce", "DHL", "FedEx", "UPS",
}

LAYER_BY_SUBREDDIT = {
    "ecommerce": "L1",
    "AmazonSeller": "L2",
    "Shopify": "L2",
    "dropship": "L3",
    "dropshipping": "L4",
}

EXTENDED_STOPWORDS = {
    # 常见停用词
    "the", "and", "for", "you", "that", "with", "what", "this", "have", "are",
    "but", "your", "how", "can", "from", "they", "just", "like", "any", "not",
    "was", "been", "has", "had", "were", "will", "would", "could", "should",
    "get", "make", "know", "think", "take", "see", "want", "use", "find",
    # 论坛碎片/URL 片段
    "ve", "re", "ll", "im", "amp", "www", "http", "https", "com", "t", "m", "co",
    "idk", "lol", "btw", "aka", "etc", "u", "ur",
}

# 明确禁止作为品牌的通用词（硬负样本护栏）
HARD_NEG_BRAND = {
    "commerce", "brand", "brands", "theme", "post", "posts", "shop", "shops",
    "tax", "taxes", "lot", "product", "products", "store", "stores", "website",
    "company", "companies", "page", "account", "orders", "order", "marketing",
    "ad", "ads", "adverts", "site", "sites", "people", "customer", "customers",
    # 用户反馈的误判补充
    "problem", "problems", "issue", "issues", "card", "cards", "sale", "sales",
    "review", "reviews", "conversion", "conversions", "content", "bank", "banks",
    "seo",
}


@dataclass
class Baseline:
    terms: List[str]
    embeddings: np.ndarray
    meta: dict


def _iter_jsonl(path: Path):
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


def _load_baseline(path: Path) -> Baseline:
    with path.open("rb") as f:
        b = pickle.load(f)
        if isinstance(b, dict):
            return Baseline(terms=b["terms"], embeddings=b["embeddings"], meta=b.get("meta", {}))
        return b


def _encode_terms(terms: List[str], baseline: Baseline) -> np.ndarray:
    method = str(baseline.meta.get("method", ""))
    if method.startswith("st::"):
        model_name = method.split("::", 1)[1]
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(model_name)
            return np.asarray(model.encode(terms), dtype=float)
        except Exception:
            pass
    # 回退 Hashing
    from sklearn.feature_extraction.text import HashingVectorizer
    dim = int(baseline.embeddings.shape[1] if baseline.embeddings.size else 128)
    hv = HashingVectorizer(analyzer="char", ngram_range=(3, 5), n_features=dim, alternate_sign=False)
    return hv.transform(terms).toarray()


def _cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if b.ndim == 1:
        b = b.reshape(1, -1)
    a_n = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_n = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return float((a_n @ b_n.T).max())


def extract_brands_with_ner(texts: List[str]) -> Set[str]:
    """使用 spacy NER 提取品牌/组织"""
    brands = set()
    print(f"🔍 使用 spacy NER 提取品牌（处理 {len(texts)} 条文本）...")
    
    # 采样处理（避免太慢）
    sample_size = min(1000, len(texts))
    if _HAS_NER:
        for text in texts[:sample_size]:
            doc = nlp(text[:1000])  # 限制长度
            for ent in doc.ents:
                if ent.label_ in ["ORG", "PRODUCT"]:
                    brand = ent.text.strip()
                    # 过滤：长度 2-30，首字母大写
                    if 2 <= len(brand) <= 30 and brand[0].isupper() and brand.lower() not in HARD_NEG_BRAND:
                        brands.add(brand)
    else:
        # 无 NER 时，为避免误判，退化为仅使用已知品牌表
        return set()
    
    print(f"✅ 提取到 {len(brands)} 个品牌候选")
    return brands


def extract_pain_points_with_sentiment(texts: List[str]) -> Dict[str, int]:
    """使用 textblob 情感分析 + KeyBERT 提取痛点短语"""
    print(f"🔍 使用情感分析提取痛点（处理 {len(texts)} 条文本）...")

    negative_texts = []
    # 增加采样数量，降低情感阈值
    for text in texts[:3000]:  # 从 1000 增加到 3000
        try:
            blob = TextBlob(text[:500])
            # 降低阈值：从 -0.1 到 -0.05（捕获更多负面文本）
            if blob.sentiment.polarity < -0.05:
                negative_texts.append(text[:500])
        except Exception:
            continue

    print(f"✅ 识别到 {len(negative_texts)} 条负面文本")

    if not negative_texts:
        return {}

    # 使用 KeyBERT 提取负面短语（使用 MMR 而不是 maxsum，避免性能问题）
    pain_phrases = Counter()
    combined = " ".join(negative_texts[:200])  # 增加到 200 条

    try:
        print("🔍 使用 KeyBERT 提取痛点短语...")
        keywords = kw_model.extract_keywords(
            combined,
            keyphrase_ngram_range=(2, 4),
            stop_words='english',
            top_n=120,  # 进一步提高覆盖
            use_mmr=True,
            diversity=0.7,
        )
        for phrase, score in keywords:
            # 过滤：包含负面词
            low = phrase.lower()
            if any(neg in low for neg in NEGATIVE_TOKENS):
                pain_phrases[phrase] += int(score * 100)
            # 常见痛点复合短语规则加分
            if re.search(r"(account\s+suspension|policy\s+violation|lost\s+package|chargebacks?|refunds?|return\s+rate|late\s+shipment|cash\s+flow|low\s+conversion|ad\s+disapproval|listing\s+takedown|ip\s+infringement)", low):
                pain_phrases[phrase] += 50
    except Exception as e:
        print(f"⚠️  KeyBERT 提取失败: {e}")

    print(f"✅ 提取到 {len(pain_phrases)} 个痛点短语")
    return dict(pain_phrases)


def generate_aliases_with_keybert(term: str, texts: List[str], top_n: int = 3) -> List[str]:
    """使用 KeyBERT 为术语生成别名"""
    # 简化：只为高频词生成别名
    if len(term.split()) > 2:  # 短语太长，跳过
        return []

    # 从文本中找相关短语
    combined = " ".join(texts[:50])  # 采样（减少文本量）
    if len(combined) < 100:  # 文本太少，跳过
        return []

    try:
        keywords = kw_model.extract_keywords(
            combined,
            keyphrase_ngram_range=(1, 3),
            stop_words='english',
            top_n=top_n * 5,
            use_mmr=True,  # 使用 MMR 替代 maxsum
            diversity=0.5,
        )
        aliases = []
        for phrase, score in keywords:
            # 简单相似性：包含或共享首词，且长度差不大
            if phrase.lower() != term.lower():
                low_t = term.lower()
                low_p = phrase.lower()
                if (low_t in low_p or low_p in low_t) and abs(len(low_t) - len(low_p)) <= 4:
                    aliases.append(phrase)
                    if len(aliases) >= top_n:
                        break
        return aliases
    except Exception:
        return []


def extract_candidates_tfidf(texts: List[str], max_features: int = 1000) -> List[Tuple[str, float, int]]:
    """使用 TF-IDF 提取候选词"""
    if not texts:
        return []

    min_df = 1 if len(texts) < 2 else 2
    try:
        tfidf = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=max_features,
            min_df=min_df,
            stop_words='english'
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
    result = [(features[i], float(tfidf_scores[i]), int(freqs[i])) for i in order]
    return result


def categorise_term(term: str, brands: Set[str], pain_points: Dict[str, int]) -> str:
    """分类术语：brands / pain_points / features"""
    # 0. 非品牌硬负样本
    small = term.strip().lower()
    if small in HARD_NEG_BRAND:
        return "features"

    # 1. 品牌优先（不区分大小写）
    brands_lower = {b.lower() for b in brands}
    known_brands_lower = {b.lower() for b in KNOWN_BRANDS}

    if small in brands_lower or small in known_brands_lower:
        return "brands"

    # 2. 痛点
    if small in {p.lower() for p in pain_points.keys()}:
        return "pain_points"

    # 3. 包含负面词
    if any(neg in small for neg in NEGATIVE_TOKENS):
        return "pain_points"

    # 4. 默认 features
    return "features"


def precision_tag(term: str, category: str) -> str:
    if category == "brands":
        return "exact"
    if " " in term or "-" in term or "/" in term:
        return "phrase"
    # 单词型特征默认 exact（词边界）
    return "exact"


def polarity_tag(category: str, term: str) -> str:
    if category == "pain_points":
        return "negative"
    # 简单正面词检测
    positive_words = {"best", "great", "good", "excellent", "amazing", "love", "perfect"}
    if any(pos in term.lower() for pos in positive_words):
        return "positive"
    return "neutral"


def distribute_target(total: int) -> Dict[str, int]:
    """分配目标数量到各层"""
    alloc = {
        "L1": int(math.ceil(total * 0.22)),
        "L2": int(math.ceil(total * 0.28)),
        "L3": int(math.ceil(total * 0.22)),
        "L4": total,
    }
    used = alloc["L1"] + alloc["L2"] + alloc["L3"]
    alloc["L4"] = max(0, total - used)
    return alloc


def _is_noise_term(term: str) -> bool:
    t = term.strip()
    if not t:
        return True
    low = t.lower()
    if len(low) < 3:
        return True
    if low.isdigit():
        return True
    if low in EXTENDED_STOPWORDS:
        return True
    if low.startswith("http") or ".com" in low or ".io" in low:
        return True
    if re.fullmatch(r"[a-z]\.?[a-z]?", low):
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="增强版语义词库提取（Stage 0.2）")
    parser.add_argument("--corpus", required=True, help="语料路径（支持通配符）")
    parser.add_argument("--L1-baseline", required=True, help="L1 基线 embeddings.pkl")
    parser.add_argument("--output", required=True, help="输出 YAML 路径")
    parser.add_argument("--target-total-terms", type=int, default=500, help="目标总词数")
    parser.add_argument("--min-freq", type=int, default=3, help="最小频次")
    parser.add_argument("--output-mapping", help="输出 CSV 映射表")
    args = parser.parse_args()

    # 1. 加载语料
    print(f"📂 加载语料: {args.corpus}")
    from glob import glob
    paths = [Path(p) for p in glob(args.corpus)]
    if not paths:
        print(f"❌ 未找到语料文件: {args.corpus}")
        return

    posts = _load_posts(paths)
    print(f"✅ 加载 {len(posts)} 条帖子")

    # 2. 按层分组
    texts_by_layer = _texts_by_layer(posts)
    for layer, texts in texts_by_layer.items():
        print(f"  {layer}: {len(texts)} 条文本")

    # 3. 加载 L1 基线
    print(f"📂 加载 L1 基线: {args.L1_baseline}")
    baseline = _load_baseline(Path(args.L1_baseline))
    print(f"✅ 基线: {len(baseline.terms)} 词, {baseline.embeddings.shape[1]} 维")

    # 4. 提取品牌（使用 spacy NER）
    all_texts = sum(texts_by_layer.values(), [])
    brands = extract_brands_with_ner(all_texts)
    brands.update(KNOWN_BRANDS)  # 合并已知品牌

    # 5. 提取痛点（使用情感分析）
    pain_points = extract_pain_points_with_sentiment(all_texts)

    # 6. 分层提取候选词
    print("\n🔍 分层提取候选词...")
    layer_candidates: Dict[str, List[Tuple[str, float, int]]] = {}
    for layer in ["L1", "L2", "L3", "L4"]:
        texts = texts_by_layer[layer]
        if not texts:
            layer_candidates[layer] = []
            continue
        candidates = extract_candidates_tfidf(texts, max_features=1000)
        # 过滤低频词
        candidates = [(t, s, f) for t, s, f in candidates if f >= args.min_freq]
        # 过滤停用词
        candidates = [(t, s, f) for t, s, f in candidates if t.lower() not in EXTENDED_STOPWORDS]
        layer_candidates[layer] = candidates
        print(f"  {layer}: {len(candidates)} 个候选词")

    # 7. 分配目标数量
    target_by_layer = distribute_target(args.target_total_terms)
    print(f"\n📊 目标分配: {target_by_layer}")

    # 8. 构建最终词库
    print("\n🔨 构建最终词库...")
    lexicon = {
        "version": "v2.0",
        "domain": "crossborder",
        "layers": {
            "L1": {"brands": [], "features": [], "pain_points": []},
            "L2": {"brands": [], "features": [], "pain_points": []},
            "L3": {"brands": [], "features": [], "pain_points": []},
            "L4": {"brands": [], "features": [], "pain_points": []},
        },
        "stats": {"by_layer": {}, "total": 0},
    }

    mapping_rows = []

    # 类别配额占比（可按需微调，满足“均衡命中”）
    CAT_RATIOS = {"brands": 0.10, "pain_points": 0.20, "features": 0.70}
    global_seen: Set[str] = set()

    # 采用更合理的层遍历顺序（平台/执行优先，其次基础与情绪层）
    for layer in ["L2", "L3", "L4", "L1"]:
        candidates = layer_candidates[layer]
        target = target_by_layer[layer]

        # 先分类后选取，避免某一类挤占名额
        groups: Dict[str, List[Tuple[str, float, int]]] = defaultdict(list)
        for term, score, freq in candidates:
            if _is_noise_term(term):
                continue
            cat = categorise_term(term, brands, pain_points)
            groups[cat].append((term, score, freq))

        for cat in groups:
            groups[cat].sort(key=lambda x: -x[1])

        qb = max(1, int(math.ceil(target * CAT_RATIOS["brands"])))
        qp = max(1, int(math.ceil(target * CAT_RATIOS["pain_points"])))
        qf = max(0, target - qb - qp)

        # 若痛点不足，启发式从 features 中回填“可能的痛点”
        if len(groups.get("pain_points", [])) < qp and groups.get("features"):
            deficit = qp - len(groups.get("pain_points", []))
            extras: List[Tuple[str, float, int]] = []
            for term, score, freq in groups["features"]:
                low = term.lower()
                if any(tok in low for tok in PAIN_HEURISTIC_TOKENS):
                    extras.append((term, score, freq))
                if len(extras) >= deficit * 2:  # 候选冗余
                    break
            if extras:
                keep_features = []
                extras_set = {t for t, _, _ in extras}
                for t in groups["features"]:
                    if t[0] not in extras_set:
                        keep_features.append(t)
                groups["features"] = keep_features
                groups.setdefault("pain_points", []).extend(extras)
                groups["pain_points"].sort(key=lambda x: -x[1])

        picked = 0
        def _take(cat: str, quota: int):
            nonlocal picked
            taken = 0
            for term, tfidf_score, freq in groups.get(cat, []):
                # 全局去重（canonical 小写对齐）
                key = term.strip().lower()
                if key in global_seen:
                    continue
                # 生成别名（仅高权重）
                aliases: List[str] = []
                if tfidf_score > 50:
                    aliases = generate_aliases_with_keybert(term, texts_by_layer[layer], top_n=2)
                entry = {
                    "canonical": term,
                    "aliases": aliases,
                    "precision_tag": precision_tag(term, cat),
                    "weight": round(tfidf_score, 2),
                    "polarity": polarity_tag(cat, term),
                }
                lexicon["layers"][layer][cat].append(entry)
                mapping_rows.append({
                    "canonical": term,
                    "layer": layer,
                    "category": cat,
                    "weight": round(tfidf_score, 2),
                    "polarity": polarity_tag(cat, term),
                    "precision_tag": precision_tag(term, cat),
                })
                global_seen.add(key)
                picked += 1
                taken += 1
                if taken >= quota:
                    break

        _take("brands", qb)
        _take("pain_points", qp)
        _take("features", qf)

        # 若本层未达标，用 features 兜底补齐到 target（允许跨层重复，但提高覆盖度）
        if picked < target:
            need = target - picked
            taken = 0
            for term, tfidf_score, freq in groups.get("features", []):
                if taken >= need:
                    break
                key = term.strip().lower()
                # 兜底阶段不做全局去重，以保证数量达标
                aliases: List[str] = []
                if tfidf_score > 50:
                    aliases = generate_aliases_with_keybert(term, texts_by_layer[layer], top_n=2)
                entry = {
                    "canonical": term,
                    "aliases": aliases,
                    "precision_tag": precision_tag(term, "features"),
                    "weight": round(tfidf_score, 2),
                    "polarity": polarity_tag("features", term),
                }
                lexicon["layers"][layer]["features"].append(entry)
                mapping_rows.append({
                    "canonical": term,
                    "layer": layer,
                    "category": "features",
                    "weight": round(tfidf_score, 2),
                    "polarity": polarity_tag("features", term),
                    "precision_tag": precision_tag(term, "features"),
                })
                taken += 1
            picked += taken

        layer_total = picked
        lexicon["stats"]["by_layer"][layer] = layer_total
        print(
            f"  {layer}: {layer_total} 词 (brands: {len(lexicon['layers'][layer]['brands'])}, features: {len(lexicon['layers'][layer]['features'])}, pain_points: {len(lexicon['layers'][layer]['pain_points'])})"
        )

    lexicon["stats"]["total"] = sum(lexicon["stats"]["by_layer"].values())

    # 9. 保存 YAML
    print(f"\n💾 保存词库: {args.output}")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=2)

    # 10. 保存映射表
    if args.output_mapping:
        print(f"💾 保存映射表: {args.output_mapping}")
        Path(args.output_mapping).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_mapping, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["canonical", "layer", "category", "weight", "polarity", "precision_tag"])
            writer.writeheader()
            writer.writerows(mapping_rows)

    print(f"\n✅ 完成！总计 {lexicon['stats']['total']} 词")
    print(json.dumps({"status": "ok", "total": lexicon["stats"]["total"], "by_layer": lexicon["stats"]["by_layer"], "output": args.output}))


if __name__ == "__main__":
    main()
