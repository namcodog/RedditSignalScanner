from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.analysis import Analysis
from app.models.task import Task, TaskStatus

router = APIRouter(prefix="/report", tags=["analysis"])


@router.options("/{task_id}")
async def options_analysis_report(task_id: str) -> Response:
    # CORS 预检请求在路由层直接放行，避免触发认证依赖
    return Response(status_code=204)


@router.get("/{task_id}", summary="Fetch completed analysis report")
async def get_analysis_report(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    task = await db.get(
        Task,
        task_id,
        options=[joinedload(Task.analysis).joinedload(Analysis.report)],
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    if str(task.user_id) != payload.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to access this task",
        )

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Task has not completed yet"
        )

    if task.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )

    if task.analysis.report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
        )

    analysis = task.analysis
    insights = analysis.insights or {}
    sources = analysis.sources or {}
    pain_points = insights.get("pain_points") or []
    competitors = insights.get("competitors") or []
    opportunities = insights.get("opportunities") or []
    communities = sources.get("communities") or []
    communities_detail = sources.get("communities_detail") or []

    total_insights = len(pain_points) + len(competitors) + len(opportunities)
    top_opportunity = ""
    if opportunities:
        top_opportunity = opportunities[0].get("description") or ""

    generated_at = analysis.report.generated_at
    analysis_duration = sources.get("analysis_duration_seconds")
    if not analysis_duration and generated_at and analysis.created_at:
        analysis_duration = max(
            0,
            int((generated_at - analysis.created_at).total_seconds()),
        )

    posts_analyzed = int(sources.get("posts_analyzed") or 0)
    metadata = {
        "analysis_version": analysis.analysis_version,
        "confidence_score": float(analysis.confidence_score or 0.0),
        "processing_time_seconds": float(analysis_duration or 0),
        "cache_hit_rate": float(sources.get("cache_hit_rate") or 0.0),
        "total_mentions": posts_analyzed,
    }
    if sources.get("recovery_strategy"):
        metadata["recovery_applied"] = sources.get("recovery_strategy")
    if sources.get("fallback_quality"):
        metadata["fallback_quality"] = sources.get("fallback_quality")

    competitor_sentiment_counts: Dict[str, int] = {
        "positive": 0,
        "negative": 0,
        "mixed": 0,
    }
    for competitor in competitors:
        label = competitor.get("sentiment")
        mentions = int(competitor.get("mentions") or 0)
        if label in competitor_sentiment_counts:
            competitor_sentiment_counts[label] += mentions

    pain_positive = sum(
        item.get("frequency", 0)
        for item in pain_points
        if item.get("sentiment_score", 0.0) > 0.05
    )
    pain_negative = sum(
        item.get("frequency", 0)
        for item in pain_points
        if item.get("sentiment_score", 0.0) < -0.05
    )
    pain_neutral = (
        sum(item.get("frequency", 0) for item in pain_points)
        - pain_positive
        - pain_negative
    )
    total_mentions = posts_analyzed or (
        competitor_sentiment_counts["positive"]
        + competitor_sentiment_counts["negative"]
        + competitor_sentiment_counts["mixed"]
        + pain_positive
        + pain_negative
        + max(pain_neutral, 0)
    )
    total_mentions = max(total_mentions, 1)

    positive_mentions = competitor_sentiment_counts["positive"] + pain_positive
    negative_mentions = competitor_sentiment_counts["negative"] + pain_negative
    neutral_mentions = competitor_sentiment_counts["mixed"] + max(pain_neutral, 0)

    def percentage(value: int) -> int:
        return int(round((value / total_mentions) * 100))

    # 社区成员数（静态映射，名称小写匹配）。若未知则回退到10万。
    COMMUNITY_MEMBERS: Dict[str, int] = {
        "r/startups": 1_200_000,
        "r/entrepreneur": 980_000,
        "r/saas": 450_000,
        "r/productmanagement": 320_000,
        "r/technology": 1_000_000,
        "r/artificial": 500_000,
        "r/userexperience": 260_000,
        "r/growthhacking": 180_000,
        "r/smallbusiness": 210_000,
        "r/marketing": 750_000,
    }

    overview = {
        "sentiment": {
            "positive": percentage(positive_mentions),
            "negative": percentage(negative_mentions),
            "neutral": percentage(neutral_mentions),
        },
        "top_communities": [
            {
                "name": detail.get("name"),
                "mentions": detail.get("mentions"),
                "relevance": int(round(float(detail.get("cache_hit_rate", 0)) * 100)),
                "members": COMMUNITY_MEMBERS.get(
                    str(detail.get("name", "")).lower(), 100_000
                ),
                "category": (detail.get("categories") or [""])[0],
                "daily_posts": detail.get("daily_posts"),
                "avg_comment_length": detail.get("avg_comment_length"),
                "from_cache": detail.get("from_cache", False),
            }
            for detail in sorted(
                communities_detail,
                key=lambda item: item.get("mentions", 0),
                reverse=True,
            )[:5]
        ],
    }

    report_payload = {
        "task_id": str(task.id),
        "status": task.status.value,
        "generated_at": generated_at,
        "product_description": task.product_description,
        "report": {
            "executive_summary": {
                "total_communities": len(communities),
                "key_insights": total_insights,
                "top_opportunity": top_opportunity,
            },
            "pain_points": pain_points,
            "competitors": competitors,
            "opportunities": opportunities,
        },
        "metadata": metadata,
        "overview": overview,
        "stats": {
            "total_mentions": total_mentions,
            "positive_mentions": positive_mentions,
            "negative_mentions": negative_mentions,
            "neutral_mentions": neutral_mentions,
        },
    }

    return report_payload


__all__ = ["router"]
