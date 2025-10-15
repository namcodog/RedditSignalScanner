"""最小测试用例，用于隔离 pytest-asyncio 问题"""
import pytest


def test_sync_simple():
    """同步测试 - 应该立即通过"""
    assert 1 + 1 == 2


@pytest.mark.asyncio
async def test_async_simple():
    """异步测试 - 测试 pytest-asyncio 是否正常工作"""
    assert 1 + 1 == 2


@pytest.mark.asyncio
async def test_async_with_import():
    """异步测试 + 导入 app - 测试导入是否导致卡住"""
    from app.main import app
    
    assert app is not None

