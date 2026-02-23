from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


PlanKind = Literal[
    "patrol",
    "backfill_posts",
    "backfill_comments",
    "probe",
    "seed_top_year",
    "seed_top_all",
    "seed_controversial_year",
]
TargetType = Literal["subreddit", "query", "post_ids"]


class CrawlPlanWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    since: datetime | None = None
    until: datetime | None = None


class CrawlPlanLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posts_limit: int | None = None
    comments_limit: int | None = None


class CrawlPlanContract(BaseModel):
    """
    CrawlPlan 合同（v1）。

    说明：
    - 先阶段性复用 crawler_run_targets.config 存放该结构（Key 已拍板）。
    - 这里的校验是“防乱保险丝”：不同 plan_kind 用不同规则，避免跑错执行器。
    """

    model_config = ConfigDict(extra="forbid")

    version: int = 2
    plan_kind: PlanKind
    target_type: TargetType
    target_value: str
    reason: str
    window: CrawlPlanWindow | None = None
    limits: CrawlPlanLimits = Field(default_factory=CrawlPlanLimits)
    # meta 仅用于执行/排查的补充信息（不会参与身份证计算），保持宽松避免 bool 被误判成 int(0/1)
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_kind_contract(self) -> "CrawlPlanContract":
        # Target constraints (v1)
        if self.plan_kind in (
            "patrol",
            "backfill_posts",
            "seed_top_year",
            "seed_top_all",
            "seed_controversial_year",
        ) and self.target_type != "subreddit":
            raise ValueError("plan_kind requires target_type='subreddit'")

        # Probe constraints (v1)
        if self.plan_kind == "probe":
            source = str(self.meta.get("source") or "").strip().lower()
            if source not in {"search", "hot"}:
                raise ValueError("probe requires meta.source in {'search','hot'}")

            if source == "search" and self.target_type != "query":
                raise ValueError("probe(search) requires target_type='query'")
            if source == "hot" and self.target_type != "subreddit":
                raise ValueError("probe(hot) requires target_type='subreddit'")

            posts_limit = self.limits.posts_limit
            if posts_limit is None or int(posts_limit) <= 0:
                raise ValueError("probe requires limits.posts_limit > 0")

        # Window constraints (v1)
        if self.plan_kind == "backfill_posts":
            if self.window is None or self.window.since is None or self.window.until is None:
                raise ValueError("backfill_posts requires window.since and window.until")
            if self.window.since.tzinfo is None:
                self.window.since = self.window.since.replace(tzinfo=timezone.utc)
            if self.window.until.tzinfo is None:
                self.window.until = self.window.until.replace(tzinfo=timezone.utc)
            if self.window.since >= self.window.until:
                raise ValueError("backfill_posts requires window.since < window.until")

        # Comments backfill constraints (v1)
        if self.plan_kind == "backfill_comments":
            if self.target_type != "post_ids":
                raise ValueError("backfill_comments requires target_type='post_ids'")
            if not self.target_value:
                raise ValueError("backfill_comments requires non-empty target_value (post_id)")
            if self.limits.comments_limit is None or int(self.limits.comments_limit) <= 0:
                raise ValueError("backfill_comments requires limits.comments_limit > 0")
            subreddit = str(self.meta.get("subreddit") or "").strip()
            if not subreddit:
                raise ValueError("backfill_comments requires meta.subreddit")

        return self


def _dt_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def build_idempotency_payload(plan: CrawlPlanContract) -> dict[str, JsonValue]:
    """
    计划身份证口径（Key 已拍板）：
    - 必须包含：target_type + target_value + plan_kind + since + until + limits + reason
    - 不包含：priority/created_at 等会抖动的字段
    """
    return {
        "target_type": plan.target_type,
        "target_value": plan.target_value,
        "plan_kind": plan.plan_kind,
        "reason": plan.reason,
        "window": {
            "since": _dt_iso(plan.window.since) if plan.window else None,
            "until": _dt_iso(plan.window.until) if plan.window else None,
        },
        "limits": {
            "posts_limit": plan.limits.posts_limit,
            "comments_limit": plan.limits.comments_limit,
        },
    }


def compute_idempotency_key(plan: CrawlPlanContract, *, length: int = 16) -> str:
    payload = build_idempotency_payload(plan)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[: max(8, min(length, len(digest)))]


def compute_idempotency_key_human(plan: CrawlPlanContract) -> str:
    since = plan.window.since.date().isoformat() if plan.window and plan.window.since else ""
    until = plan.window.until.date().isoformat() if plan.window and plan.window.until else ""
    if since or until:
        window = f"{since}..{until}"
        return f"{plan.target_type}:{plan.target_value}|{plan.plan_kind}|{window}"
    return f"{plan.target_type}:{plan.target_value}|{plan.plan_kind}"
