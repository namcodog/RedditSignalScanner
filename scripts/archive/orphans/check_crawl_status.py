#!/usr/bin/env python3
"""检查抓取状态的诊断脚本"""
import json
import os
from pathlib import Path
from datetime import datetime

def check_status():
    print("=" * 80)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 检查测试文件
    test_jsonl = Path("backend/data/reddit_corpus/ecommerce_test.jsonl")
    test_progress = Path("backend/data/reddit_corpus/ecommerce_test.jsonl.progress.json")
    
    print("\n【测试文件状态】")
    if test_jsonl.exists():
        size = test_jsonl.stat().st_size
        with open(test_jsonl, 'r') as f:
            lines = sum(1 for _ in f)
        print(f"✓ ecommerce_test.jsonl 存在")
        print(f"  - 文件大小: {size:,} bytes ({size/1024:.2f} KB)")
        print(f"  - 行数: {lines:,}")
    else:
        print("✗ ecommerce_test.jsonl 不存在")
    
    if test_progress.exists():
        print(f"✓ 进度文件存在")
        with open(test_progress, 'r') as f:
            progress = json.load(f)
        print(f"  内容: {json.dumps(progress, indent=2, ensure_ascii=False)}")
    else:
        print("✗ 进度文件不存在")
    
    # 检查原始文件
    print("\n【原始文件状态】")
    orig_jsonl = Path("backend/data/reddit_corpus/ecommerce.jsonl")
    if orig_jsonl.exists():
        size = orig_jsonl.stat().st_size
        if size > 0:
            with open(orig_jsonl, 'r') as f:
                lines = sum(1 for _ in f)
            print(f"✓ ecommerce.jsonl 存在")
            print(f"  - 文件大小: {size:,} bytes ({size/1024:.2f} KB)")
            print(f"  - 行数: {lines:,}")
        else:
            print(f"✓ ecommerce.jsonl 存在但为空 (0 bytes)")
    else:
        print("✗ ecommerce.jsonl 不存在")
    
    # 检查备份文件
    print("\n【备份文件】")
    backup_files = list(Path("backend/data/reddit_corpus").glob("ecommerce.jsonl.backup_*"))
    if backup_files:
        for bf in sorted(backup_files):
            size = bf.stat().st_size
            print(f"  - {bf.name}: {size:,} bytes ({size/1024:.2f} KB)")
    else:
        print("  无备份文件")
    
    # 检查日志文件
    print("\n【日志文件】")
    log_files = list(Path("logs").glob("crawl-ecommerce-*.log"))
    if log_files:
        for lf in sorted(log_files)[-3:]:  # 最近3个
            size = lf.stat().st_size
            print(f"  - {lf.name}: {size:,} bytes")
            if size > 0:
                with open(lf, 'r') as f:
                    content = f.read()
                    lines = content.count('\n')
                    print(f"    行数: {lines}, 前200字符: {content[:200]}")
    else:
        print("  无日志文件")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_status()

