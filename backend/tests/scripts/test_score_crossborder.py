from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, List

import pytest
import json
import importlib

try:
    # Import internal helpers from the scoring script
    from backend.scripts.score_crossborder import (
        Theme,
        _load_completed_names,
        _load_lexicon,
        _load_names,
        _normalise_name,
        _score_A,
        _score_B,
        _score_C,
        _weighted_score,
    )
except (ImportError, ModuleNotFoundError) as exc:
    pytest.skip(str(exc), allow_module_level=True)


def _mk_post(title: str, selftext: str = "", *, comments: int = 0, created_utc: float = 1.0, author: str = "u1") -> dict[str, Any]:
    return {
        "title": title,
        "selftext": selftext,
        "num_comments": comments,
        "created_utc": created_utc,
        "author": author,
    }


def test_weighted_score_bounds_and_scaling() -> None:
    # full scores with equal weights → 100
    w = {"A": 1.0, "B": 1.0, "C": 1.0}
    assert _weighted_score(30.0, 15.0, 10.0, w) == 100.0
    # zero components → 0
    assert _weighted_score(0.0, 0.0, 0.0, w) == 0.0
    # clamp upper bound
    assert _weighted_score(60.0, 30.0, 20.0, w) == 100.0


def test_score_A_increases_with_subscribers_and_activity() -> None:
    # No posts → only subscriber score
    assert _score_A(100_000, []) > _score_A(500, [])

    # With posts across 2 days and comments → activity boosts score
    posts = [
        _mk_post("p1", comments=50, created_utc=100000.0),
        _mk_post("p2", comments=10, created_utc=200000.0),
    ]
    a_low = _score_A(1_000, [])
    a_high = _score_A(1_000, posts)
    assert a_high > a_low


def test_score_B_relevance_and_spam_ratio() -> None:
    theme = Theme(
        name="what_to_sell",
        include=["product", "niche"],
        aliases=["winning product"],
        exclude=["meme"],
        stopwords=["what is"],
    )
    posts = [
        _mk_post("Great product niche", ""),
        _mk_post("This is a meme", ""),  # excluded
        _mk_post("Learn what is AI", ""),  # stopword → ignored
        _mk_post("Totally unrelated", "click here now"),  # spam
    ]
    B, rel, spam = _score_B(posts, theme, spam_keywords=["click here"])  # type: ignore[arg-type]
    # At least one relevant among checked
    assert rel > 0.0
    # Spam detected
    assert spam >= 0.25
    # B should be within 0..15 scale
    assert 0.0 <= B <= 15.0


def test_score_C_author_concentration_reasonable() -> None:
    posts: List[dict[str, Any]] = []
    # 10 posts by 5 authors → some concentration
    for i in range(10):
        posts.append(_mk_post(f"t{i}", author=f"u{i%5}"))
    c = _score_C(posts)
    assert 0.0 <= c <= 10.0


def test_normalise_name() -> None:
    assert _normalise_name("r/python") == "r/python"
    assert _normalise_name("python") == "r/python"


def test_load_names_from_json_and_csv(tmp_path: Path) -> None:
    j = tmp_path / "subs.json"
    j.write_text(json.dumps({"communities": [{"name": "python"}, {"name": "golang"}]}), encoding="utf-8")
    names_j = _load_names(j)
    assert names_j == ["r/python", "r/golang"]

    c = tmp_path / "subs.csv"
    with c.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["name"]) 
        w.writeheader()
        w.writerow({"name": "python"})
        w.writerow({"name": "rust"})
    names_c = _load_names(c)
    assert names_c == ["r/python", "r/rust"]


def test_load_lexicon_from_dir(tmp_path: Path) -> None:
    d = tmp_path / "cross_border"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "what_to_sell.yml"
    f.write_text(
        """
theme: what_to_sell
include_keywords:
  - product research
aliases:
  - winning product
exclude:
  - meme
stopwords:
  - what is
        """.strip(),
        encoding="utf-8",
    )
    t = _load_lexicon(d, "what_to_sell")
    assert t.name == "what_to_sell"
    assert "product research" in t.include
    assert "winning product" in t.aliases
    assert "meme" in t.exclude
    assert "what is" in t.stopwords


def test_load_completed_names(tmp_path: Path) -> None:
    p = tmp_path / "scored.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["name", "A", "C", "weighted_score_what_to_sell"],
        )
        w.writeheader()
        w.writerow({"name": "r/python"})
        w.writerow({"name": "r/golang"})
    done = _load_completed_names(p)
    assert done == {"r/python", "r/golang"}
