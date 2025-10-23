#!/usr/bin/env python3
"""
API 契约测试脚本

使用 schemathesis 进行 property-based 测试，验证 API 响应是否符合 OpenAPI schema。

用法:
    python scripts/test_contract.py
    python scripts/test_contract.py --workers 4  # 并行测试
    python scripts/test_contract.py --hypothesis-max-examples 50  # 增加测试用例数
"""
import sys
from pathlib import Path

import schemathesis
from hypothesis import settings

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import create_application
from app.core.config import get_settings


def main():
    """运行 API 契约测试"""
    print("=" * 80)
    print("🔍 API 契约测试 - 使用 Schemathesis")
    print("=" * 80)
    print()

    # 创建 FastAPI 应用
    app = create_application(get_settings())
    
    # 从 FastAPI 应用创建 schema
    schema = schemathesis.from_asgi("/api/openapi.json", app)
    
    # 配置 Hypothesis 设置
    settings.register_profile(
        "contract_testing",
        max_examples=100,  # 每个端点生成 100 个测试用例
        deadline=5000,     # 每个测试用例最多 5 秒
        suppress_health_check=[],
    )
    settings.load_profile("contract_testing")
    
    # 统计信息
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    print(f"📊 测试配置:")
    print(f"   - 每个端点生成 100 个测试用例")
    print(f"   - 超时时间: 5 秒")
    print(f"   - Schema 路径: /api/openapi.json")
    print()
    
    # 运行测试
    print("🚀 开始测试...")
    print()
    
    # 定义要跳过的端点（需要认证或特殊设置）
    skip_endpoints = [
        "/api/stream/{task_id}",  # SSE 端点，需要特殊处理
        "/api/admin/",            # Admin 端点，需要认证
    ]
    
    @schema.parametrize()
    @settings(max_examples=100, deadline=5000)
    def test_api(case):
        """测试 API 端点是否符合 schema"""
        nonlocal total_tests, passed_tests, failed_tests, skipped_tests
        
        total_tests += 1
        
        # 跳过需要认证的端点
        if any(skip in case.path for skip in skip_endpoints):
            skipped_tests += 1
            return
        
        try:
            # 发送请求
            response = case.call_asgi()
            
            # 验证响应是否符合 schema
            case.validate_response(response)
            
            passed_tests += 1
            print(f"✅ {case.method} {case.path} - PASSED")
            
        except Exception as e:
            failed_tests += 1
            print(f"❌ {case.method} {case.path} - FAILED")
            print(f"   错误: {str(e)[:100]}")
    
    # 执行测试
    try:
        test_api()
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        return 1
    
    # 打印结果
    print()
    print("=" * 80)
    print("📊 测试结果")
    print("=" * 80)
    print(f"总计: {total_tests} 个测试")
    print(f"✅ 通过: {passed_tests}")
    print(f"❌ 失败: {failed_tests}")
    print(f"⏭️  跳过: {skipped_tests}")
    print()
    
    if failed_tests > 0:
        print("❌ 契约测试失败！")
        return 1
    else:
        print("✅ 所有契约测试通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())

