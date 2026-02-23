from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, hash_password
from app.main import app
from app.models.semantic_audit_log import SemanticAuditLog
from app.models.semantic_candidate import SemanticCandidate
from app.models.semantic_term import SemanticTerm
from app.models.user import User


async def _override_admin_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


@pytest.mark.asyncio
async def test_e2e_semantic_candidate_approve_and_reject_flow(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    """端到端验证：候选词列表 → 审核批准/拒绝 → DB 与审计记录一致."""

    admin_email = f"semantic-admin-{uuid.uuid4().hex}@example.com"
    overridden = await _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, admin_user_id = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 准备两个候选词：一个用于批准，一个用于拒绝
        now = datetime.now(timezone.utc)
        approve_candidate = SemanticCandidate(
            term="E2EBrandApprove",
            frequency=5,
            source="posts",
            first_seen_at=now,
            last_seen_at=now,
            status="pending",
        )
        reject_candidate = SemanticCandidate(
            term="E2EBrandReject",
            frequency=3,
            source="comments",
            first_seen_at=now,
            last_seen_at=now,
            status="pending",
        )
        db_session.add_all([approve_candidate, reject_candidate])
        await db_session.commit()
        await db_session.refresh(approve_candidate)
        await db_session.refresh(reject_candidate)

        # 1. 列表接口应能看到 pending 候选词
        list_resp = await client.get(
            "/api/admin/semantic-candidates",
            params={"status": "pending", "limit": 50},
            headers=headers,
        )
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        assert list_body["code"] == 0
        terms = {item["term"] for item in list_body["data"]["items"]}
        assert "E2EBrandApprove" in terms
        assert "E2EBrandReject" in terms

        # 2. 批准一个候选词，应创建 SemanticTerm 记录并从候选表中删除
        approve_resp = await client.post(
            f"/api/admin/semantic-candidates/{approve_candidate.id}/approve",
            headers=headers,
            json={
                "category": "brands",
                "layer": "L1",
                "aliases": ["e2ebrandapprove"],
                "weight": 1.5,
            },
        )
        assert approve_resp.status_code == 200
        approve_body = approve_resp.json()
        assert approve_body["code"] == 0
        data = approve_body["data"]
        assert data["canonical"] == "E2EBrandApprove"
        assert "e2ebrandapprove" in [a.lower() for a in data["aliases"]]

        # DB 验证：候选词被删除，正式术语被创建
        cand_row = await db_session.execute(
            select(SemanticCandidate).where(
                SemanticCandidate.id == approve_candidate.id
            )
        )
        assert cand_row.scalars().first() is None

        term_row = await db_session.execute(
            select(SemanticTerm).where(
                SemanticTerm.canonical == "E2EBrandApprove"
            )
        )
        term = term_row.scalars().first()
        assert term is not None
        assert term.layer == "L1"

        # 审计日志中存在对应的 approve 记录
        audit_row = await db_session.execute(
            select(SemanticAuditLog).where(
                SemanticAuditLog.action == "approve",
                SemanticAuditLog.entity_type == "semantic_candidate",
                SemanticAuditLog.entity_id == approve_candidate.id,
            )
        )
        audit = audit_row.scalars().first()
        assert audit is not None

        # 3. 拒绝另一个候选词，应更新状态并写审计日志
        reject_resp = await client.post(
            f"/api/admin/semantic-candidates/{reject_candidate.id}/reject",
            headers=headers,
            json={"reason": "not relevant for E2E"},
        )
        assert reject_resp.status_code == 200
        reject_body = reject_resp.json()
        assert reject_body["code"] == 0
        assert reject_body["data"]["rejected"] == reject_candidate.id

        reject_row = await db_session.execute(
            select(SemanticCandidate).where(
                SemanticCandidate.id == reject_candidate.id
            )
        )
        rejected = reject_row.scalars().first()
        assert rejected is not None
        assert rejected.status == "rejected"

        audit_reject_row = await db_session.execute(
            select(SemanticAuditLog).where(
                SemanticAuditLog.action == "reject",
                SemanticAuditLog.entity_type == "semantic_candidate",
                SemanticAuditLog.entity_id == reject_candidate.id,
            )
        )
        audit_reject = audit_reject_row.scalars().first()
        assert audit_reject is not None
    finally:
        app.dependency_overrides.pop(get_settings, None)
