import os
from pathlib import Path
import json


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_build_l1_baseline(tmp_path: Path) -> None:
    # 1) 准备轻量语料
    corpus = tmp_path / "ecommerce.jsonl"
    docs: list[dict] = []
    phrases = [
        ("SEO optimization", "Improve checkout conversion"),
        ("Chargeback prevention", "refund policy"),
        ("payment gateway", "A/B test checkout flow"),
        ("cart abandonment", "email remarketing"),
        ("shipping speed", "customer trust"),
        ("user experience", "site speed"),
        ("ad optimization", "landing page"),
        ("conversion rate", "checkout UX"),
        ("fraud detection", "chargeback dispute"),
        ("return policy", "customer support"),
        ("seo audit", "product description"),
        ("payment retry", "declined card"),
    ]
    for i, (t1, t2) in enumerate(phrases, 1):
        docs.append(
            {
                "id": f"e{i}",
                "title": f"{t1} and {t2} checkout conversion",
                "selftext": f"{t2} plus {t1} checkout conversion",
                "score": 1,
                "num_comments": 0,
                "created_utc": 1700000000.0 + i,
                "subreddit": "ecommerce",
            }
        )
    _write_jsonl(corpus, docs)

    # 2) 生成基线
    out_pkl = tmp_path / "L1_baseline_embeddings.pkl"
    from scripts.build_L1_baseline import build_baseline

    baseline = build_baseline(corpus, out_pkl, model_name="sentence-transformers/all-MiniLM-L6-v2")

    assert out_pkl.exists(), "应生成基线文件"
    assert baseline.terms and len(baseline.terms) >= 10, "应提取到足量术语"
    assert baseline.embeddings.shape[0] == len(baseline.terms)
    # 允许降级，维度可能 128（hashing）或 ST 模型默认维度
    assert baseline.embeddings.shape[1] >= 64
