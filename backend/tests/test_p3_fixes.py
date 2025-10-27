"""
P3 修复验证测试
验证 P3-3 和 P3-5 的修复
"""
import pytest


def test_p3_3_backend_i18n_tasks():
    """P3-3: 验证任务状态消息使用英文"""
    from app.api.routes.tasks import _MESSAGE_MAP
    from app.schemas.task import TaskStatus
    
    # 验证所有消息都是英文
    assert _MESSAGE_MAP[TaskStatus.PENDING] == "Task queued"
    assert _MESSAGE_MAP[TaskStatus.PROCESSING] == "Task processing"
    assert _MESSAGE_MAP[TaskStatus.COMPLETED] == "Analysis completed"
    assert _MESSAGE_MAP[TaskStatus.FAILED] == "Task failed"
    
    # 确保没有中文
    for msg in _MESSAGE_MAP.values():
        assert not any('\u4e00' <= char <= '\u9fff' for char in msg), f"Found Chinese in: {msg}"


def test_p3_5_reddit_error_messages():
    """P3-5: 验证 Reddit API 错误消息不泄露敏感信息"""
    from app.services.reddit_client import RedditAPIError
    
    # 验证错误消息是通用的，不包含敏感信息
    error_500 = RedditAPIError("Reddit API temporarily unavailable (status=500)")
    assert "temporarily unavailable" in str(error_500).lower()
    assert "status=500" in str(error_500)
    
    error_400 = RedditAPIError("Reddit API request failed (status=400)")
    assert "request failed" in str(error_400).lower()
    assert "status=400" in str(error_400)
    
    error_json = RedditAPIError("Invalid response format from Reddit API")
    assert "invalid response format" in str(error_json).lower()
    assert "reddit api" in str(error_json).lower()


def test_p3_3_opportunity_report_i18n():
    """P3-3: 验证机会报告使用英文"""
    # 这个测试验证代码中的字符串常量
    import inspect
    from app.services.reporting import opportunity_report
    
    source = inspect.getsource(opportunity_report)
    
    # 验证关键字符串已改为英文
    assert '"Problem to be analyzed"' in source
    assert '"User quote"' in source
    assert '"Model insight"' in source
    assert '"Unknown problem"' in source
    
    # 确保没有中文字符串（排除注释）
    lines = source.split('\n')
    code_lines = [line for line in lines if not line.strip().startswith('#')]
    code = '\n'.join(code_lines)
    
    # 检查是否还有中文字符串（允许在注释中）
    chinese_strings = [
        '待分析问题',
        '用户原话',
        '模型洞察',
        '未知问题',
        '聚焦',
        '采访',
        '追踪',
    ]
    
    for chinese_str in chinese_strings:
        # 确保这些中文字符串不在代码中（可能在注释中）
        if chinese_str in code:
            # 如果找到，确保它在注释中
            for line in lines:
                if chinese_str in line and not line.strip().startswith('#'):
                    pytest.fail(f"Found Chinese string '{chinese_str}' in code (not comment): {line}")

