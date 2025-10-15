#!/usr/bin/env python
"""
Celery 验证辅助脚本（PRD/PRD-04-任务系统.md 支撑）
- 创建最小可用 User + Task 记录
- 支持指定 Task ID 与产品描述
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionFactory  # noqa: E402
from app.models.task import Task, TaskStatus  # noqa: E402
from app.models.user import User  # noqa: E402

DEFAULT_EMAIL_PREFIX = "celery.verification"
DEFAULT_EMAIL_DOMAIN = "example.com"
DEFAULT_EMAIL_PATTERN = f"{DEFAULT_EMAIL_PREFIX}%@%"


async def _ensure_user(email: str, password_hash: str) -> User:
    async with SessionFactory() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing:
            return existing

        user = User(id=uuid.uuid4(), email=email, password_hash=password_hash, is_active=True)
        session.add(user)
        await session.commit()
        return user


async def _create_task(task_id: uuid.UUID, user: User, description: str) -> Task:
    async with SessionFactory() as session:
        # Re-fetch user inside this session to satisfy relationship context.
        db_user = await session.get(User, user.id)
        if db_user is None:
            raise RuntimeError(f"User {user.id} disappeared before task creation.")

        task = Task(
            id=task_id,
            user=db_user,
            product_description=description,
            status=TaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def _cleanup_seeded_accounts(target_email: str | None) -> tuple[int, int]:
    async with SessionFactory() as session:
        if target_email:
            user_stmt = select(User).where(User.email == target_email)
        else:
            user_stmt = select(User).where(User.email.like(DEFAULT_EMAIL_PATTERN))

        users = list(await session.scalars(user_stmt))
        task_count = 0
        user_count = 0

        for user in users:
            tasks = list(await session.scalars(select(Task).where(Task.user_id == user.id)))
            for task in tasks:
                await session.delete(task)
            task_count += len(tasks)
            await session.flush()

            remaining = await session.scalar(select(Task.id).where(Task.user_id == user.id))
            if remaining is None:
                await session.delete(user)
                user_count += 1

        await session.commit()
        return task_count, user_count


def _build_default_email(unique: bool) -> str:
    suffix = f"+{uuid.uuid4().hex[:8]}" if unique else ""
    return f"{DEFAULT_EMAIL_PREFIX}{suffix}@{DEFAULT_EMAIL_DOMAIN}"


async def _main(email: str, password_hash: str, description: str, task_id: uuid.UUID | None) -> None:
    user = await _ensure_user(email, password_hash)
    task_uuid = task_id or uuid.uuid4()
    task = await _create_task(task_uuid, user, description)
    print("✅ Seeded task:")
    print(f"   task_id = {task.id}")
    print(f"   user_id = {task.user_id}")
    print(f"   email = {email}")
    print(f"   product_description = {task.product_description}")


def main() -> int:
    parser = argparse.ArgumentParser(description="创建 Celery 测试任务记录。")
    parser.add_argument(
        "--email",
        default=None,
        help="用于测试的用户邮箱，默认使用 celery.verification@example.com。",
    )
    parser.add_argument(
        "--unique-email",
        action="store_true",
        help="在默认邮箱后添加随机后缀，避免与现有数据冲突。",
    )
    parser.add_argument(
        "--password-hash",
        default="test-hash",
        help="测试用户密码哈希，默认 test-hash。",
    )
    parser.add_argument(
        "--description",
        default="Automated verification product description for Celery worker.",
        help="任务的产品描述，默认提供一段合规文案。",
    )
    parser.add_argument(
        "--task-id",
        type=uuid.UUID,
        default=None,
        help="可选的任务 ID，若不指定则自动生成。",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="清理由脚本生成的测试数据（默认匹配 celery.verification*@）。",
    )
    parser.add_argument(
        "--purge-email",
        default=None,
        help="与 --purge 联用，只清理指定邮箱的数据。",
    )

    args = parser.parse_args()

    if args.purge:
        removed_tasks, removed_users = asyncio.run(_cleanup_seeded_accounts(args.purge_email))
        print(f"✅ Purge complete: deleted {removed_tasks} task(s), {removed_users} user(s).")
        return 0

    email = args.email or _build_default_email(args.unique_email)
    asyncio.run(_main(email, args.password_hash, args.description, args.task_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
