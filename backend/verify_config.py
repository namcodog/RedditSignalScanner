#!/usr/bin/env python3
"""验证当前配置是否生效"""

from app.core.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    print("=" * 60)
    print("当前 Reddit API 配置：")
    print("=" * 60)
    print(f"timeout                = {s.reddit_request_timeout_seconds}s")
    print(f"rate_limit             = {s.reddit_rate_limit} 次")
    print(f"rate_limit_window      = {s.reddit_rate_limit_window_seconds}s")
    print(f"max_concurrency        = {s.reddit_max_concurrency}")
    print("=" * 60)
    print()
    print("预期值：")
    print("  - timeout = 10.0")
    print("  - rate_limit = 600")
    print("  - rate_limit_window = 600.0")
    print("=" * 60)

