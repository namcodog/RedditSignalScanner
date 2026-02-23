from __future__ import annotations

import os
from pathlib import Path

import pytest


def _write_env(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_dotenv_precedence_shell_over_backend_over_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    规则（大白话）：
    - 你手动 export 的（shell 里写死的）最优先，.env 不能盖掉它。
    - backend/.env 可以覆盖根目录 .env 的占位值。
    """
    root_env = tmp_path / "root.env"
    backend_env = tmp_path / "backend.env"

    _write_env(root_env, "RSS_TEST_KEY=from_root\nRSS_TEST_ROOT_ONLY=root_only\n")
    _write_env(backend_env, "RSS_TEST_KEY=from_backend\nRSS_TEST_BACKEND_ONLY=backend_only\n")

    monkeypatch.setenv("RSS_TEST_KEY", "from_shell")
    monkeypatch.delenv("RSS_TEST_ROOT_ONLY", raising=False)
    monkeypatch.delenv("RSS_TEST_BACKEND_ONLY", raising=False)

    from app.core.config import _load_dotenv_with_precedence

    _load_dotenv_with_precedence(root_env=root_env, backend_env=backend_env)

    assert os.getenv("RSS_TEST_KEY") == "from_shell"
    assert os.getenv("RSS_TEST_ROOT_ONLY") == "root_only"
    assert os.getenv("RSS_TEST_BACKEND_ONLY") == "backend_only"


def test_dotenv_precedence_backend_overrides_root_when_shell_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root_env = tmp_path / "root.env"
    backend_env = tmp_path / "backend.env"

    _write_env(root_env, "RSS_TEST_KEY2=from_root\n")
    _write_env(backend_env, "RSS_TEST_KEY2=from_backend\n")

    monkeypatch.delenv("RSS_TEST_KEY2", raising=False)

    from app.core.config import _load_dotenv_with_precedence

    _load_dotenv_with_precedence(root_env=root_env, backend_env=backend_env)

    assert os.getenv("RSS_TEST_KEY2") == "from_backend"

