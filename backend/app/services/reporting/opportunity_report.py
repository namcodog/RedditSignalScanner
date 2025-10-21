"""
Opportunity report generation logic for Phase 3 action items.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class EvidenceItem:
    title: str
    url: str | None
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "url": self.url, "note": self.note}


@dataclass
class OpportunityReport:
    problem_definition: str
    evidence_chain: List[EvidenceItem]
    suggested_actions: List[str]
    confidence: float
    urgency: float
    product_fit: float
    priority: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_definition": self.problem_definition,
            "evidence_chain": [item.to_dict() for item in self.evidence_chain],
            "suggested_actions": self.suggested_actions,
            "confidence": self.confidence,
            "urgency": self.urgency,
            "product_fit": self.product_fit,
            "priority": self.priority,
        }


def _severity_to_urgency(severity: str) -> float:
    mapping = {"high": 0.9, "medium": 0.75, "low": 0.6}
    return mapping.get(severity, 0.7)


def _score_product_fit(potential_users: str) -> float:
    digits = "".join(ch for ch in potential_users if ch.isdigit())
    if not digits:
        return 0.65
    try:
        value = int(digits)
    except ValueError:
        return 0.65
    if value >= 500:
        return 0.9
    if value >= 200:
        return 0.8
    return 0.7


def _select_evidence(posts: Iterable[Dict[str, Any]], limit: int = 2) -> List[EvidenceItem]:
    evidence: List[EvidenceItem] = []
    for post in posts:
        title = str(post.get("content") or post.get("title") or "").strip()
        if not title:
            continue
        note_parts = []
        community = post.get("community")
        if community:
            note_parts.append(f"社区: {community}")
        upvotes = post.get("upvotes")
        if upvotes:
            note_parts.append(f"赞数 {upvotes}")
        evidence.append(
            EvidenceItem(
                title=title[:120],
                url=post.get("url") or post.get("permalink"),
                note=" | ".join(note_parts) if note_parts else "社区反馈",
            )
        )
        if len(evidence) >= limit:
            break
    return evidence


def build_opportunity_reports(
    insights: Dict[str, Any],
    *,
    max_items: int = 3,
) -> List[OpportunityReport]:
    """Construct structured opportunity reports from raw insights."""
    pain_points: List[Dict[str, Any]] = insights.get("pain_points", []) or []
    opportunities: List[Dict[str, Any]] = insights.get("opportunities", []) or []

    if not opportunities:
        return []

    reports: List[OpportunityReport] = []

    for index, opportunity in enumerate(opportunities[:max_items]):
        pain = pain_points[index] if index < len(pain_points) else (
            pain_points[0] if pain_points else None
        )

        problem_definition = opportunity.get("description") or (
            pain.get("description") if pain else "待分析问题"
        )

        evidence_items = _select_evidence(opportunity.get("source_examples", []))
        if pain:
            evidence_items.extend(_select_evidence(pain.get("example_posts", [])))
        if not evidence_items and pain:
            for quote in pain.get("user_examples", [])[:2]:
                evidence_items.append(
                    EvidenceItem(title=quote[:120], url=None, note="用户原话")
                )

        if not evidence_items:
            for insight in opportunity.get("key_insights", [])[:2]:
                evidence_items.append(
                    EvidenceItem(title=insight[:120], url=None, note="模型洞察")
                )

        confidence = float(opportunity.get("relevance_score", 0.6))
        confidence = max(0.4, min(confidence + 0.1, 0.95))
        severity: str = str(pain.get("severity")) if pain and pain.get("severity") else "medium"
        urgency = _severity_to_urgency(severity)
        product_fit = _score_product_fit(
            opportunity.get("potential_users", "约0个潜在团队")
        )
        priority = round(confidence * urgency * product_fit, 4)

        action_suggestions = [
            f"聚焦 `{problem_definition}`，采访核心用户验证需求优先级。",
            f"参考机会点 `{opportunity.get('description', '机会')}` 制定下一步产品实验。",
        ]
        if pain:
            action_suggestions.append(
                f"追踪社区 `{pain['example_posts'][0]['community']}` 的后续讨论，评估迭代反馈。"
                if pain.get("example_posts")
                else "继续监控相关社区话题走势。"
            )

        problem_def_str: str = str(problem_definition) if problem_definition else "未知问题"
        reports.append(
            OpportunityReport(
                problem_definition=problem_def_str,
                evidence_chain=evidence_items[:3],
                suggested_actions=action_suggestions[:3],
                confidence=round(confidence, 3),
                urgency=round(urgency, 3),
                product_fit=round(product_fit, 3),
                priority=priority,
            )
        )

    reports.sort(key=lambda item: item.priority, reverse=True)
    return reports


__all__ = ["OpportunityReport", "EvidenceItem", "build_opportunity_reports"]

