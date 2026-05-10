from __future__ import annotations

import os
from uuid import uuid4

import psycopg
from tests.conftest import COMMUNITY_RESET_TABLES, DEFAULT_RESET_TABLES


def _test_dsn() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test",
    ).replace("+asyncpg", "").replace("+psycopg", "")


def _truncate_community_tables() -> None:
    conn = psycopg.connect(_test_dsn())
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE "
                + ", ".join(COMMUNITY_RESET_TABLES)
                + " RESTART IDENTITY CASCADE"
            )
    finally:
        conn.close()


def _count_community_rows(name: str) -> int:
    conn = psycopg.connect(_test_dsn())
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM community_pool WHERE name = %s",
                (name,),
            )
            return int(cursor.fetchone()[0])
    finally:
        conn.close()


def test_default_pytest_cleanup_excludes_community_tables() -> None:
    assert "community_pool" not in DEFAULT_RESET_TABLES
    assert "community_cache" not in DEFAULT_RESET_TABLES
    assert "discovered_communities" not in DEFAULT_RESET_TABLES
    assert "community_pool" in COMMUNITY_RESET_TABLES
    assert "community_cache" in COMMUNITY_RESET_TABLES
    assert "discovered_communities" in COMMUNITY_RESET_TABLES


def _insert_community_row(name: str) -> None:
    conn = psycopg.connect(_test_dsn())
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO community_pool (
                    name,
                    tier,
                    categories,
                    description_keywords,
                    daily_posts,
                    avg_comment_length,
                    semantic_quality_score,
                    priority
                ) VALUES (
                    %s,
                    'medium',
                    %s::jsonb,
                    %s::jsonb,
                    3,
                    20,
                    0.70,
                    'medium'
                )
                """,
                (name, '{"topic": ["policy"]}', '{"policy": 1}'),
            )
    finally:
        conn.close()


def test_explicit_community_reset_path_clears_seeded_rows() -> None:
    community_name = f"r/resetpolicy{uuid4().hex[:8]}"
    _truncate_community_tables()
    _insert_community_row(community_name)
    assert _count_community_rows(community_name) == 1

    _truncate_community_tables()
    assert _count_community_rows(community_name) == 0
