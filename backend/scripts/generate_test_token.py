"""Utility script to emit long-lived JWTs for frontend integration tests.

Usage:
    python scripts/generate_test_token.py

The script prints two tokens tied to deterministic user identifiers so the
frontend team can exercise authenticated endpoints without needing to run the
full registration/login flow during Day 5 hand-off.
"""

from __future__ import annotations

import sys
from datetime import timedelta, timezone
from pathlib import Path


# Ensure the backend package is importable when the script is invoked directly.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.security import create_access_token


def _format_line(label: str, value: str) -> str:
    return f"{label:<14}: {value}"


def generate_test_tokens() -> None:
    """Generate and print test JWTs for predefined users."""
    settings = get_settings()
    users = [
        {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "email": "frontend-test@example.com",
            "description": "前端功能调试账号",
        },
        {
            "user_id": "00000000-0000-0000-0000-000000000002",
            "email": "frontend-dev@example.com",
            "description": "联调回归账号",
        },
    ]

    expires_delta = timedelta(days=7)

    print("=" * 64)
    print("🔑  前端开发测试 Token 生成器")
    print("=" * 64)
    print()

    for entry in users:
        token, expires_at = create_access_token(
            entry["user_id"],
            email=entry["email"],
            expires_delta=expires_delta,
            settings=settings,
        )

        print(_format_line("User Email", entry["email"]))
        print(_format_line("User ID", entry["user_id"]))
        print(_format_line("说明", entry["description"]))
        print(_format_line("Expires", expires_at.astimezone(timezone.utc).isoformat()))
        print("Token:")
        print(f"  {token}")
        print()
        print("使用方式:")
        print("  Authorization: Bearer <token>")
        print("-" * 64)
        print()

    print("注意事项:")
    print("1. 以上 user_id 必须在本地数据库中存在相应用户记录。")
    print("2. Token 仅用于 Day 5 前端联调，不可投产。")
    print("3. 如需新的 token，请重新运行本脚本。")


if __name__ == "__main__":
    generate_test_tokens()

