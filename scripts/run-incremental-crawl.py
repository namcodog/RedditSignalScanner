#!/usr/bin/env python3
"""
运行增量抓取任务
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.tasks.crawler_task import _crawl_seeds_incremental_impl


async def main():
    # 读取配置参数
    import os
    sort_strategy = os.getenv("CRAWLER_SORT", "top")
    time_filter = os.getenv("CRAWLER_TIME_FILTER", "month")
    post_limit = os.getenv("CRAWLER_POST_LIMIT", "100")

    print("🚀 启动增量抓取任务...")
    print("=" * 60)
    print(f"📋 抓取参数:")
    print(f"   - 排序策略: {sort_strategy}")
    print(f"   - 时间窗口: {time_filter}")
    print(f"   - 帖子上限: {post_limit}")
    print("=" * 60)

    result = await _crawl_seeds_incremental_impl(force_refresh=False)

    print("\n" + "=" * 60)
    print("📊 抓取完成！")
    # 统计细分：空结果 vs 真失败
    communities = result.get('communities', []) or []
    success_count = int(result.get('succeeded', 0))
    error_count = sum(1 for c in communities if c.get('status') == 'failed' or ('error' in c))
    empty_count = max(0, len(communities) - success_count - error_count)

    print(f"状态: {result.get('status', 'unknown')}")
    print(f"✅ 成功: {success_count}")
    print(f"🟡 空结果: {empty_count}")
    print(f"🔴 真失败: {error_count}")
    print(f"📝 新增帖子: {result.get('total_new_posts', 0)}")
    print(f"🔄 更新帖子: {result.get('total_updated_posts', 0)}")
    print(f"🔍 去重帖子: {result.get('total_duplicates', 0)}")

    # 保存详细结果到文件
    import json
    import time
    ts = time.strftime("%Y%m%d-%H%M%S")
    output_path = f"reports/phase-log/T1.1-crawl-{ts}.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # 写入扩展指标到 JSON 结果
    try:
        result["empty_count"] = empty_count
        result["error_count"] = error_count
    except Exception:
        pass

    with open(output_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"📄 详细结果已保存: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())

