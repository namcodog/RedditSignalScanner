"""Unit tests for warmup crawler tasks."""

from __future__ import annotations

import pytest

from app.tasks.warmup_crawler import (
    warmup_crawler_batch_task,
    warmup_crawler_task,
)


def test_warmup_crawler_task_imports() -> None:
    """Test that warmup crawler task can be imported."""
    assert warmup_crawler_task is not None
    assert warmup_crawler_batch_task is not None


def test_warmup_crawler_task_signature() -> None:
    """Test warmup crawler task signature."""
    # Verify task is registered
    assert warmup_crawler_task.name == "warmup_crawler"
    assert warmup_crawler_batch_task.name == "warmup_crawler_batch"


@pytest.mark.asyncio
async def test_reddit_client_imports() -> None:
    """Test that Reddit client can be imported."""
    from app.clients.reddit_client import RedditClient

    assert RedditClient is not None


@pytest.mark.asyncio
async def test_reddit_client_initialization() -> None:
    """Test Reddit client initialization."""
    from app.clients.reddit_client import RedditClient

    # Initialize with default settings
    client = RedditClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        user_agent="TestAgent/1.0",
    )

    assert client.client_id == "test_client_id"
    assert client.client_secret == "test_client_secret"
    assert client.user_agent == "TestAgent/1.0"
    assert client.rate_limiter.max_rate == 58
    assert client.rate_limiter.time_period == 60

    await client.close()

