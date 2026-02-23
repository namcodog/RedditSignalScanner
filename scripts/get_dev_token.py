import asyncio
import sys
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import SessionFactory
from app.models.user import User, MembershipLevel
from sqlalchemy import select

async def main():
    async with SessionFactory() as session:
        # 1. Try to find the test user
        email = "test@example.com"
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        # 2. Create if not exists
        if not user:
            print(f"User {email} not found, creating...")
            user = User(
                email=email,
                password_hash=hash_password("test123456"),
                is_active=True,
                # is_superuser=True, # Removed as it's not in model definition currently
                membership_level=MembershipLevel.PRO # Ensure PRO for report access
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Ensure membership level is PRO for testing reports
            if user.membership_level != MembershipLevel.PRO:
                user.membership_level = MembershipLevel.PRO
                session.add(user)
                await session.commit()
                print(f"Upgraded {email} to PRO membership")

        # 3. Generate Token directly (Bypassing HTTP Auth)
        access_token, _ = create_access_token(user.id, email=user.email)
        
        # 4. Output only the token to stdout so it can be captured
        print(access_token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
