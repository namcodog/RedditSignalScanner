import inspect
import pytest

from app.services.text_classifier import TextClassifier, classify_category_aspect
from app.services.semantic.robust_loader import RobustSemanticLoader
from app.interfaces.semantic_provider import SemanticLoadStrategy


def test_text_classifier_init_signature():
    sig = inspect.signature(TextClassifier.__init__)
    assert "semantic_provider" in sig.parameters


@pytest.mark.asyncio
async def test_text_classifier_with_provider():
    provider = RobustSemanticLoader(strategy=SemanticLoadStrategy.YAML_ONLY)
    clf = TextClassifier(semantic_provider=provider)
    result = await clf.classify("price is too high")
    assert result.category.name.lower() in {"pain", "solution", "other"}


def test_classify_category_aspect_rules():
    res = classify_category_aspect("subscription fee too high")
    assert res.category == res.category.PAIN or res.category == res.category.SOLUTION
