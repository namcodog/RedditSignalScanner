from __future__ import annotations

from app.services.text_classifier import classify_category_aspect
from app.models.comment import Category, Aspect


def test_classify_subscription_pain() -> None:
    c = classify_category_aspect("This subscription fee is a trap!")
    assert c.category == Category.PAIN
    assert c.aspect == Aspect.SUBSCRIPTION


def test_classify_solution_recommendation() -> None:
    c = classify_category_aspect("I recommend trying this workaround")
    assert c.category == Category.SOLUTION
    assert c.aspect in {Aspect.OTHER, Aspect.CONTENT}

