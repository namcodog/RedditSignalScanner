from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.community_pool import CommunityPool
from app.models.tier_audit_log import TierAuditLog
from app.models.tier_suggestion import TierSuggestion


def _override_admin_settings(admin_email: str) -> Settings:
  base = get_settings()
  return base.model_copy(update={"admin_emails_raw": admin_email})


@pytest.mark.asyncio
async def test_list_tier_suggestions_basic_flow(
  client: AsyncClient,
  token_factory: Any,
  db_session: AsyncSession,
) -> None:
  admin_email = f"admin-{uuid.uuid4().hex}@example.com"
  overridden = _override_admin_settings(admin_email)
  app.dependency_overrides[get_settings] = lambda: overridden

  try:
    admin_token, _ = await token_factory(email=admin_email)
    headers = {"Authorization": f"Bearer {admin_token}"}

    now = datetime.now(timezone.utc)
    # Seed a few suggestions
    s1 = TierSuggestion(
      community_name="r/example",
      current_tier="T3",
      suggested_tier="T2",
      confidence=0.9,
      reasons=["high activity"],
      metrics={"posts_per_day": 10.0},
      status="pending",
      priority_score=20,
      generated_at=now,
      expires_at=now + timedelta(days=7),
    )
    s2 = TierSuggestion(
      community_name="r/example",
      current_tier="T2",
      suggested_tier="T1",
      confidence=0.5,
      reasons=["ok activity"],
      metrics={"posts_per_day": 5.0},
      status="applied",
      priority_score=10,
      generated_at=now,
      expires_at=now + timedelta(days=7),
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    resp = await client.get(
      "/api/admin/communities/tier-suggestions",
      headers=headers,
      params={"community_name": "r/example", "min_confidence": 0.8},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["community_name"] == "r/example"
    assert item["suggested_tier"] == "T2"
    assert item["confidence"] == pytest.approx(0.9)
  finally:
    app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_list_tier_audit_logs_and_batch_update_auto_tier_enabled(
  client: AsyncClient,
  token_factory: Any,
  db_session: AsyncSession,
) -> None:
  admin_email = f"admin-{uuid.uuid4().hex}@example.com"
  overridden = _override_admin_settings(admin_email)
  app.dependency_overrides[get_settings] = lambda: overridden

  try:
    admin_token, _ = await token_factory(email=admin_email)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 准备一个社区和一条审计日志
    pool = CommunityPool(
      name="r/audit_example",
      tier="T3",
      categories={"source": "test"},
      description_keywords={"keywords": ["k1"]},
      daily_posts=0,
      avg_comment_length=0,
      quality_score=0.5,
      priority="low",
      user_feedback_count=0,
      discovered_count=0,
      is_active=True,
      auto_tier_enabled=False,
    )
    db_session.add(pool)
    await db_session.commit()

    log = TierAuditLog(
      community_name="r/audit_example",
      action="tier_change",
      field_changed="tier",
      from_value="T3",
      to_value="T2",
      changed_by=admin_email,
      change_source="manual",
      reason="initial test",
      snapshot_before={"tier": "T3"},
      snapshot_after={"tier": "T2"},
    )
    db_session.add(log)
    await db_session.commit()

    # 调用批量更新接口，开启 auto_tier_enabled
    resp_batch = await client.patch(
      "/api/admin/communities/batch",
      headers=headers,
      json={
        "communities": ["r/audit_example"],
        "updates": {"auto_tier_enabled": True},
        "reason": "enable auto tier",
      },
    )
    assert resp_batch.status_code == 200
    body_batch = resp_batch.json()
    assert body_batch["code"] == 0
    assert body_batch["data"]["updated_count"] == 1

    db_session.expire_all()
    stored_pool = (
      await db_session.execute(
        select(CommunityPool).where(CommunityPool.name == "r/audit_example")
      )
    ).scalar_one()
    assert stored_pool.auto_tier_enabled is True

    # 调用审计日志列表接口
    resp_logs = await client.get(
      "/api/admin/communities/r/audit_example/tier-audit-logs",
      headers=headers,
    )
    assert resp_logs.status_code == 200
    body_logs = resp_logs.json()
    assert body_logs["code"] == 0
    data_logs = body_logs["data"]
    assert data_logs["total"] >= 1
    assert any(
      item["community_name"] == "r/audit_example" for item in data_logs["items"]
    )
  finally:
    app.dependency_overrides.pop(get_settings, None)


