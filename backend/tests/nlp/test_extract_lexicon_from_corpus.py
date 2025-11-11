import json
from pathlib import Path


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_extract_lexicon_four_layers(tmp_path: Path) -> None:
    # 1) 造两层轻量语料（L1/L2），其余为空也应正常运行
    p_ecom = tmp_path / "ecommerce.jsonl"
    ecom_docs = []
    for i in range(12):
        ecom_docs.append(
            {
                "id": f"e{i}",
                "title": "SEO and checkout conversion",
                "selftext": "Reduce chargeback and refund",
                "score": 10,
                "num_comments": 2,
                "created_utc": 1700000000.0 + i,
                "subreddit": "ecommerce",
            }
        )
    _write_jsonl(p_ecom, ecom_docs)

    p_amz = tmp_path / "AmazonSeller.jsonl"
    amz_docs = []
    for i in range(10):
        amz_docs.append(
            {
                "id": f"a{i}",
                "title": "Amazon FBA policy and suspension risk",
                "selftext": "Buy Box and seller central tips",
                "score": 9,
                "num_comments": 1,
                "created_utc": 1700000500.0 + i,
                "subreddit": "AmazonSeller",
            }
        )
    _write_jsonl(p_amz, amz_docs)

    # L3: dropship（执行语义）
    p_ds = tmp_path / "dropship.jsonl"
    ds_docs = []
    for i in range(8):
        ds_docs.append(
            {
                "id": f"d{i}",
                "title": "Klaviyo flow and ad automation",
                "selftext": "SMS automation and ROI strategy",
                "score": 5,
                "num_comments": 1,
                "created_utc": 1700000600.0 + i,
                "subreddit": "dropship",
            }
        )
    _write_jsonl(p_ds, ds_docs)

    # L4: dropshipping（情绪/痛点）
    p_dsp = tmp_path / "dropshipping.jsonl"
    dsp_docs = []
    for i in range(8):
        dsp_docs.append(
            {
                "id": f"p{i}",
                "title": "refund issue and scam risk",
                "selftext": "account suspension problem and loss",
                "score": 5,
                "num_comments": 1,
                "created_utc": 1700000700.0 + i,
                "subreddit": "dropshipping",
            }
        )
    _write_jsonl(p_dsp, dsp_docs)

    # 2) 基线
    from scripts.build_L1_baseline import build_baseline

    baseline_pkl = tmp_path / "L1_baseline_embeddings.pkl"
    build_baseline(p_ecom, baseline_pkl, model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 3) 提取（小目标数，易断言）
    from scripts.extract_lexicon_from_corpus import extract_lexicon

    lexicon, mapping = extract_lexicon(
        [p_ecom, p_amz, p_ds, p_dsp], baseline_pkl, target_total=100, min_freq=2, sim_threshold=0.1
    )

    # 结构断言
    assert set(lexicon.keys()) == {"L1", "L2", "L3", "L4"}
    for layer in ["L1", "L2", "L3", "L4"]:
        obj = lexicon[layer]
        assert set(obj.keys()) == {"brands", "features", "pain_points"}

    # 计数与字段断言（允许不足 20，因为 L3/L4 无样本）
    total = sum(len(v) for layer in lexicon.values() for v in layer.values())
    assert total >= 20
    # 各层至少有产出
    for L in ("L1", "L2", "L3", "L4"):
        assert sum(len(v) for v in lexicon[L].values()) > 0

    # L4 痛点应为负向
    if lexicon["L4"]["pain_points"]:
        assert all(item["polarity"] == "negative" for item in lexicon["L4"]["pain_points"])
    # 任意项应包含所需字段
    any_list = next(iter(lexicon["L1"].values()))
    if any_list:
        item = any_list[0]
        assert set(item.keys()) == {"canonical", "aliases", "precision_tag", "weight", "polarity"}
