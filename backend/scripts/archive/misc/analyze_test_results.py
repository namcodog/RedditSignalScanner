#!/usr/bin/env python3
"""分析测试结果"""

import re
from datetime import datetime

# 读取日志文件
with open("/tmp/backfill_test_amazonvine.log", "r") as f:
    lines = f.readlines()

# 提取开始和结束时间（从日志内容推断）
# 由于日志没有时间戳，我们从文件修改时间和处理量来估算

# 从最后一行提取结果
last_line = lines[-1].strip()
match = re.search(r"'processed_posts': (\d+), 'processed_comments': (\d+)", last_line)
if match:
    processed_posts = int(match.group(1))
    processed_comments = int(match.group(2))
    print("=" * 60)
    print("测试结果分析")
    print("=" * 60)
    print(f"处理帖子数: {processed_posts}")
    print(f"处理评论数: {processed_comments}")
    print(f"平均每帖评论数: {processed_comments / processed_posts:.1f}")
    print("=" * 60)
    
    # 从数据库查询验证
    import subprocess
    result = subprocess.run(
        ["psql", "-U", "postgres", "-d", "reddit_signal_scanner_dev", "-t", "-c",
         "SELECT COUNT(*) FROM comments WHERE created_at > NOW() - INTERVAL '10 minutes';"],
        capture_output=True,
        text=True
    )
    new_comments = int(result.stdout.strip())
    print(f"数据库新增评论数（最近10分钟）: {new_comments}")
    
    # 估算运行时间（基于批次数和每批平均时间）
    # 16 个批次，每批 5 个帖子（除了最后一批 3 个）
    # 假设每批平均 10-15 秒
    batches = 16
    estimated_time_per_batch = 12  # 秒
    estimated_total_time = batches * estimated_time_per_batch / 60  # 分钟
    
    print("=" * 60)
    print(f"估算运行时间: {estimated_total_time:.1f} 分钟")
    print(f"估算速率: {processed_comments / estimated_total_time:.1f} 条/分钟")
    print("=" * 60)
    
    # 数据库连接状态
    result = subprocess.run(
        ["psql", "-U", "postgres", "-d", "reddit_signal_scanner_dev", "-t", "-c",
         "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'reddit_signal_scanner_dev' AND state = 'idle in transaction';"],
        capture_output=True,
        text=True
    )
    zombie_connections = int(result.stdout.strip())
    print(f"僵尸连接数: {zombie_connections}")
    
    if zombie_connections > 0:
        print("⚠️  警告：仍有僵尸连接！")
    else:
        print("✅ 无僵尸连接")
    
    print("=" * 60)
