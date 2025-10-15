"""Create test users for frontend development.

Usage:
    python scripts/create_test_users.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure the backend package is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User


async def create_test_users() -> None:
    """Create test users in the database."""
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    test_users = [
        {
            "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
            "email": "frontend-test@example.com",
            "password": "TestPass123",
        },
        {
            "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
            "email": "frontend-dev@example.com",
            "password": "TestPass123",
        },
        {
            "id": uuid.UUID("41d23e79-d8f4-4988-9ce3-2e0c5044230c"),
            "email": "integration-test@example.com",
            "password": "TestPassword123!",
        },
    ]
    
    async with async_session() as session:
        for user_data in test_users:
            # Check if user already exists
            existing_user = await session.get(User, user_data["id"])
            
            if existing_user:
                print(f"✅ User {user_data['email']} already exists")
                continue
            
            # Create new user
            new_user = User(
                id=user_data["id"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
            )
            
            session.add(new_user)
            print(f"✅ Created user {user_data['email']}")
        
        await session.commit()
    
    await engine.dispose()
    print("\n✅ All test users created successfully!")


if __name__ == "__main__":
    asyncio.run(create_test_users())
