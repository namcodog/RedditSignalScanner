from __future__ import annotations

import json
import uuid

from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app


async def _override_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


class _FailingSession:
    async def execute(self, _query):  # pragma: no cover - simple stub
        raise RuntimeError("database connection failed: password=super-secret")


async def test_runtime_diag_masks_database_error(
    client: AsyncClient,
    token_factory,
    monkeypatch,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = await _override_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    # 在 override session 之前创建 token,因为 token_factory 需要访问数据库
    token, _ = await token_factory(email=admin_email)

    original_session_override = app.dependency_overrides.get(get_session)

    async def failing_session_override():
        yield _FailingSession()

    app.dependency_overrides[get_session] = failing_session_override

    try:
        response = await client.get(
            "/api/diag/runtime",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()

        assert payload["database"]["connected"] is False
        assert payload["database"]["error"] == "unavailable"
        assert "password" not in json.dumps(payload)
    finally:
        if original_session_override is not None:
            app.dependency_overrides[get_session] = original_session_override
        else:
            app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
