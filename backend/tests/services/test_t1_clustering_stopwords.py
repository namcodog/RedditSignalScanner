from app.services.t1_clustering import _tokenize


def test_tokenize_filters_commercial_stopwords() -> None:
    text = "You really would like a refund, not just a delay fee."
    tokens = _tokenize(text)
    assert "you" not in tokens
    assert "not" not in tokens
    assert "just" not in tokens
    # 保留有价值的信号词
    assert "refund" in tokens
    assert "delay" in tokens
    assert "fee" in tokens
