#!/usr/bin/env python3
from __future__ import annotations

"""
Create a deterministic test user and task, then trigger analysis.

This script avoids fragile one-line Python in Makefile and provides
clear logs. It dispatches to Celery if available; otherwise, for
development it falls back to inline execution.
"""

import argparse
import asyncio
import os
import sys
import uuid
from typing import Optional

from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel, User


TEST_USER_ID = uuid.UUID("248ddd5c-f071-43f4-8513-5324cd54bfad")
TEST_EMAIL = "prd-test@example.com"


async def _create_records() -> uuid.UUID:
    task_id = uuid.uuid4()
    async with SessionFactory() as session:
        user = await session.get(User, TEST_USER_ID)
        if not user:
            user = User(
                id=TEST_USER_ID,
                email=TEST_EMAIL,
                password_hash=hash_password("TestPassword123"),  # 使用真实的密码哈希
                is_active=True,
                membership_level=MembershipLevel.PRO,
            )
            session.add(user)
            await session.flush()
        else:
            if user.membership_level != MembershipLevel.PRO:
                user.membership_level = MembershipLevel.PRO
                session.add(user)
                await session.flush()

        task = Task(
            id=task_id,
            user_id=TEST_USER_ID,
            product_description=(
                "一款专为自由职业者设计的时间追踪和发票管理工具，"
                "自动记录工作时间，生成专业发票，并集成主流支付平台。"
            ),
            status=TaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        print(f"✅ Created task: {task_id}")
        print(f"   User: {user.email}")
        print(f"   Status: {task.status}")
        return task_id


def _trigger_analysis(task_id: uuid.UUID) -> Optional[str]:
    try:
        # Celery task (preferred)
        from app.tasks.analysis_task import run_analysis_task  # type: ignore

        result = run_analysis_task.delay(str(task_id), str(TEST_USER_ID))
        print("🚀 Triggering analysis via Celery queue...")
        print(f"✅ Task submitted to Celery: {result.id}")
        return result.id
    except Exception as exc:  # pragma: no cover - depends on runtime environment
        print(f"⚠️  Celery dispatch failed: {exc}")
        print("↩️  Falling back to inline execution (development mode)...")
        try:
            from app.tasks.analysis_task import execute_analysis_pipeline  # type: ignore

            asyncio.run(execute_analysis_pipeline(task_id))
            print("✅ Inline analysis completed")
        except Exception as inner:
            print(f"❌ Inline analysis failed: {inner}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed test user and task, then trigger analysis")
    parser.add_argument("--frontend-port", type=int, default=int(os.getenv("FRONTEND_PORT", "3006")))
    args = parser.parse_args()

    try:
        task_id = asyncio.run(_create_records())
    except Exception as exc:
        print(f"❌ Failed creating records: {exc}")
        sys.exit(1)

    _trigger_analysis(task_id)
    print("")
    print(f"🔗 Visit: http://localhost:{args.frontend_port}/report/{task_id}")


if __name__ == "__main__":
    main()
