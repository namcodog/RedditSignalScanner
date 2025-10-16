"""创建固定的测试账号，用于本地开发和验收。

Usage:
    cd backend
    export $(cat .env | grep -v '^#' | xargs)
    python scripts/seed_test_accounts.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure the backend package is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User


# 固定的测试账号列表
TEST_ACCOUNTS = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "email": "admin@test.com",
        "password": "Admin123!",
        "role": "管理员",
        "description": "管理员账号，可以访问所有功能",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "email": "user1@test.com",
        "password": "User123!",
        "role": "普通用户",
        "description": "普通用户账号 #1",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "email": "user2@test.com",
        "password": "User123!",
        "role": "普通用户",
        "description": "普通用户账号 #2",
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "email": "demo@test.com",
        "password": "Demo123!",
        "role": "演示账号",
        "description": "演示账号，用于展示功能",
    },
    {
        "id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "email": "test@test.com",
        "password": "Test123!",
        "role": "测试账号",
        "description": "测试账号，用于自动化测试",
    },
]


async def seed_test_accounts() -> None:
    """创建固定的测试账号。"""
    settings = get_settings()
    
    print("=" * 60)
    print("🔐 Reddit Signal Scanner - 测试账号初始化")
    print("=" * 60)
    print()
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    created_count = 0
    existing_count = 0
    
    async with async_session() as session:
        for account in TEST_ACCOUNTS:
            # Check if user already exists by email
            result = await session.execute(
                select(User).where(User.email == account["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"⚠️  账号已存在: {account['email']}")
                print(f"   角色: {account['role']}")
                print(f"   说明: {account['description']}")
                print()
                existing_count += 1
                continue
            
            # Create new user
            new_user = User(
                id=account["id"],
                email=account["email"],
                password_hash=hash_password(account["password"]),
                is_active=True,
            )
            
            session.add(new_user)
            print(f"✅ 创建账号: {account['email']}")
            print(f"   密码: {account['password']}")
            print(f"   角色: {account['role']}")
            print(f"   说明: {account['description']}")
            print()
            created_count += 1
        
        await session.commit()
    
    await engine.dispose()
    
    print("=" * 60)
    print(f"✅ 测试账号初始化完成！")
    print(f"   新建账号: {created_count} 个")
    print(f"   已存在账号: {existing_count} 个")
    print("=" * 60)
    print()
    print("📋 所有测试账号列表：")
    print()
    print(f"{'邮箱':<25} {'密码':<15} {'角色':<15}")
    print("-" * 60)
    for account in TEST_ACCOUNTS:
        print(f"{account['email']:<25} {account['password']:<15} {account['role']:<15}")
    print()
    print("💡 提示：")
    print("   1. 这些账号可以直接用于登录")
    print("   2. 密码格式：大写字母 + 小写字母 + 数字 + 特殊字符")
    print("   3. admin@test.com 在 ADMIN_EMAILS 白名单中，拥有管理员权限")
    print()


async def reset_test_accounts() -> None:
    """重置所有测试账号的密码。"""
    settings = get_settings()
    
    print("=" * 60)
    print("🔄 重置测试账号密码")
    print("=" * 60)
    print()
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    reset_count = 0
    
    async with async_session() as session:
        for account in TEST_ACCOUNTS:
            result = await session.execute(
                select(User).where(User.email == account["email"])
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.password_hash = hash_password(account["password"])
                print(f"✅ 重置密码: {account['email']} -> {account['password']}")
                reset_count += 1
            else:
                print(f"⚠️  账号不存在: {account['email']}")
        
        await session.commit()
    
    await engine.dispose()
    
    print()
    print(f"✅ 成功重置 {reset_count} 个账号的密码")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="管理测试账号")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置所有测试账号的密码",
    )
    
    args = parser.parse_args()
    
    if args.reset:
        asyncio.run(reset_test_accounts())
    else:
        asyncio.run(seed_test_accounts())

