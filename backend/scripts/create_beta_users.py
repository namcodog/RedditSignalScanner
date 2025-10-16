"""Create beta tester users.

Usage:
    python scripts/create_beta_users.py --emails "user1@example.com,user2@example.com" [--reset]

Notes:
- The current User model doesn't include a role field; this script creates users and prints their role as 'beta_tester'.
- Use --reset to reset password for existing users.
"""
from __future__ import annotations

import argparse
import asyncio
import secrets
import string
import sys
from pathlib import Path

# Ensure the backend package is importable when executed directly
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # type: ignore[import-untyped]
from sqlalchemy.orm import sessionmaker  # type: ignore[import-untyped]

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User


def _generate_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _create_or_update_user(session: AsyncSession, email: str, reset: bool = False) -> tuple[str, bool]:
    # Try to find by unique email via simple query
    result = await session.execute(
        # Textual SQL could be used; here we use ORM identity by unique column
        User.__table__.select().where(User.email == email)  # type: ignore[attr-defined]
    )
    row = result.first()

    password = _generate_password()
    password_hash = hash_password(password)

    if row is not None:
        # Update existing user password when --reset specified
        if reset:
            await session.execute(
                User.__table__.update().where(User.email == email).values(password_hash=password_hash)  # type: ignore[attr-defined]
            )
            created = False
        else:
            # keep existing; return a placeholder password (not changed)
            password = "<unchanged>"
            created = False
    else:
        user = User(email=email, password_hash=password_hash)
        session.add(user)
        created = True

    return password, created


async def main(emails: list[str], reset: bool = False) -> int:
    if not emails:
        print("No emails provided.")
        return 2

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    updated = 0
    rows: list[tuple[str, str, str]] = []  # (email, role, password)

    async with async_session() as session:
        for email in emails:
            password, is_created = await _create_or_update_user(session, email.strip(), reset)
            if is_created:
                created += 1
            else:
                updated += 1
            rows.append((email.strip(), "beta_tester", password))
        await session.commit()

    # Output summary in a simple CSV-like format
    print("email,role,password")
    for email, role, password in rows:
        print(f"{email},{role},{password}")
    print(f"\n✅ Done. created={created}, updated={updated} (reset={reset})")

    await engine.dispose()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create beta tester users")
    parser.add_argument("--emails", required=True, help="Comma-separated email list")
    parser.add_argument("--reset", action="store_true", help="Reset password for existing users")
    args = parser.parse_args()

    emails = [e.strip() for e in args.emails.split(",") if e.strip()]
    raise SystemExit(asyncio.run(main(emails, reset=args.reset)))

