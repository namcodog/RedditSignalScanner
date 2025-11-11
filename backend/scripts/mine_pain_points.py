#!/usr/bin/env python3
"""
从真实 Reddit 数据中挖掘 pain_points 候选词

输入：
  - crossborder_candidates.json（已抓取的社区数据）
  - 现有的 semantic_sets/crossborder.yml

输出：
  - pain_points_candidates.csv（候选痛点词 + 证据）

方法：
  1. 提取所有帖子标题 + 正文
  2. 使用情感分析识别负面内容
  3. 提取负面内容中的高频短语（2-4 gram）
  4. 过滤掉已有的 pain_points
  5. 按频次 + 情感强度排序
"""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml


def load_existing_pain_points(lexicon_path: Path) -> Set[str]:
    """加载现有的 pain_points"""
    if not lexicon_path.exists():
        return set()
    
    with lexicon_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    pain_points = set()
    for theme_config in data.get("themes", {}).values():
        pain_points.update(theme_config.get("pain_points", []))
    
    return pain_points


def load_posts(data_path: Path) -> List[Dict]:
    """加载帖子数据"""
    if not data_path.exists():
        return []
    
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    posts = []
    for community in data:
        for post in community.get("posts", []):
            posts.append({
                "title": post.get("title", ""),
                "selftext": post.get("selftext", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "subreddit": community.get("name", ""),
            })
    
    return posts


def extract_negative_phrases(posts: List[Dict]) -> List[Tuple[str, int, List[str]]]:
    """
    提取负面短语
    
    返回：[(phrase, frequency, evidence_posts), ...]
    """
    # 负面关键词（简单启发式）
    NEGATIVE_SIGNALS = [
        "problem", "issue", "fail", "failed", "error", "bug", "broken",
        "slow", "expensive", "difficult", "hard", "confusing", "frustrating",
        "scam", "fraud", "ban", "banned", "suspend", "suspended",
        "delay", "late", "lost", "missing", "wrong", "bad", "terrible",
        "avoid", "warning", "beware", "don't", "never", "hate",
        "complaint", "complain", "disappointed", "regret", "waste",
    ]
    
    # 收集包含负面信号的文本
    negative_texts = []
    for post in posts:
        text = f"{post['title']} {post['selftext']}".lower()
        if any(signal in text for signal in NEGATIVE_SIGNALS):
            negative_texts.append({
                "text": text,
                "title": post["title"],
                "subreddit": post["subreddit"],
            })
    
    # 提取 2-4 gram 短语
    phrase_counter = Counter()
    phrase_evidence = {}
    
    for item in negative_texts:
        text = item["text"]
        words = re.findall(r'\b[a-z]+\b', text)
        
        # 2-gram
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if any(signal in phrase for signal in NEGATIVE_SIGNALS):
                phrase_counter[phrase] += 1
                if phrase not in phrase_evidence:
                    phrase_evidence[phrase] = []
                if len(phrase_evidence[phrase]) < 5:  # 最多保留5个证据
                    phrase_evidence[phrase].append(f"{item['subreddit']}: {item['title']}")
        
        # 3-gram
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            if any(signal in phrase for signal in NEGATIVE_SIGNALS):
                phrase_counter[phrase] += 1
                if phrase not in phrase_evidence:
                    phrase_evidence[phrase] = []
                if len(phrase_evidence[phrase]) < 5:
                    phrase_evidence[phrase].append(f"{item['subreddit']}: {item['title']}")
        
        # 4-gram
        for i in range(len(words) - 3):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]} {words[i+3]}"
            if any(signal in phrase for signal in NEGATIVE_SIGNALS):
                phrase_counter[phrase] += 1
                if phrase not in phrase_evidence:
                    phrase_evidence[phrase] = []
                if len(phrase_evidence[phrase]) < 5:
                    phrase_evidence[phrase].append(f"{item['subreddit']}: {item['title']}")
    
    # 转换为列表
    results = []
    for phrase, freq in phrase_counter.most_common(200):
        evidence = phrase_evidence.get(phrase, [])
        results.append((phrase, freq, evidence))
    
    return results


def filter_candidates(
    phrases: List[Tuple[str, int, List[str]]],
    existing: Set[str],
    min_frequency: int = 5,
) -> List[Dict]:
    """
    过滤候选词
    
    规则：
    1. 频次 >= min_frequency
    2. 不在现有词库中
    3. 不是纯停用词
    """
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "should", "could", "may", "might", "can", "this", "that",
        "these", "those", "i", "you", "he", "she", "it", "we", "they",
    }
    
    candidates = []
    for phrase, freq, evidence in phrases:
        # 频次过滤
        if freq < min_frequency:
            continue
        
        # 已存在过滤
        if phrase in existing or phrase.lower() in {p.lower() for p in existing}:
            continue
        
        # 停用词过滤
        words = phrase.split()
        if all(w in STOPWORDS for w in words):
            continue
        
        # 长度过滤（太短或太长）
        if len(words) < 2 or len(words) > 4:
            continue
        
        candidates.append({
            "phrase": phrase,
            "frequency": freq,
            "evidence_count": len(evidence),
            "evidence_samples": " | ".join(evidence[:3]),  # 最多3个样例
            "confidence": min(freq / 50.0, 1.0),  # 简单置信度
            "lifecycle_stage": "candidate",
            "polarity": "negative",
            "source": "auto_mined",
        })
    
    return candidates


def main():
    parser = argparse.ArgumentParser(description="Mine pain_points from Reddit data")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("backend/data/crossborder_candidates.json"),
        help="Input JSON data",
    )
    parser.add_argument(
        "--lexicon",
        type=Path,
        default=Path("backend/config/semantic_sets/crossborder.yml"),
        help="Existing lexicon YAML",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/reports/local-acceptance/pain_points_candidates.csv"),
        help="Output CSV",
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        default=5,
        help="Minimum frequency threshold",
    )
    args = parser.parse_args()
    
    print(f"📖 Loading existing pain_points from {args.lexicon}...")
    existing = load_existing_pain_points(args.lexicon)
    print(f"   Found {len(existing)} existing pain_points")
    
    print(f"📖 Loading posts from {args.data}...")
    posts = load_posts(args.data)
    print(f"   Loaded {len(posts)} posts")
    
    print(f"🔍 Extracting negative phrases...")
    phrases = extract_negative_phrases(posts)
    print(f"   Extracted {len(phrases)} candidate phrases")
    
    print(f"🧹 Filtering candidates (min_freq={args.min_freq})...")
    candidates = filter_candidates(phrases, existing, args.min_freq)
    print(f"   Filtered to {len(candidates)} high-quality candidates")
    
    print(f"💾 Writing to {args.output}...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "phrase",
            "frequency",
            "evidence_count",
            "evidence_samples",
            "confidence",
            "lifecycle_stage",
            "polarity",
            "source",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)
    
    print(f"✅ Done! Top 10 candidates:")
    for i, c in enumerate(candidates[:10], 1):
        print(f"   {i}. {c['phrase']} (freq={c['frequency']}, conf={c['confidence']:.2f})")


if __name__ == "__main__":
    main()

