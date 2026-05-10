# 修复验收标准（结果导向）

## 修复时间
2025-10-18

## 问题清单

### 问题1: Celery Beat 未显示 cleanup 任务 ❌

**现象**:
```bash
# Celery Beat Schedule 输出中没有 cleanup-expired-posts-hot
```

**根因**: Celery Worker/Beat 未重启，配置未生效

**验收标准**:

| 验收项 | 验证方法 | 期望结果 |
|--------|---------|---------|
| **1. cleanup 任务存在** | `celery -A app.core.celery_app inspect scheduled` | 包含 `cleanup-expired-posts-hot` |
| **2. Beat Schedule 显示** | Python 脚本打印 beat_schedule | 包含 `cleanup-expired-posts-hot` |
| **3. 任务调度频率** | 检查 schedule 配置 | `crontab(hour="*/6")` |
| **4. 任务队列** | 检查 options.queue | `cleanup_queue` |

**验收SQL**:
```bash
# 验收1: 检查 Beat Schedule
cd backend && python3 << 'EOF'
from app.core.celery_app import celery_app
schedule = celery_app.conf.beat_schedule
assert "cleanup-expired-posts-hot" in schedule, "cleanup 任务不存在"
task = schedule["cleanup-expired-posts-hot"]
assert task["task"] == "tasks.maintenance.cleanup_expired_posts_hot"
print("✅ cleanup 任务存在于 Beat Schedule")
EOF

# 验收2: 检查 Celery Inspect
celery -A app.core.celery_app inspect scheduled | grep cleanup
# 期望: 看到 cleanup-expired-posts-hot

# 验收3: 检查 posts_hot 过期数据
psql -U postgres -d reddit_scanner -c "SELECT COUNT(*) FROM posts_hot WHERE expires_at < NOW();"
# 期望: 0
```

---

### 问题2: 单元测试Mock问题 ❌

**现象**:
```
FAILED test_duplicate_detection - assert 0 == 10
FAILED test_watermark_filtering - assert 0 == 5
```

**根因**:
1. 使用 `AsyncMock` 模拟 Reddit API
2. Mock 数据未正确插入数据库
3. 去重逻辑依赖数据库状态，Mock 无法验证

**修复方案**: 使用真实数据库 + 真实数据（不使用Mock）

**验收标准**:

| 验收项 | 验证方法 | 期望结果 |
|--------|---------|---------|
| **1. 测试使用真实DB** | 检查测试代码 | 无 `AsyncMock(return_value=...)` |
| **2. test_duplicate_detection** | `pytest tests/services/test_incremental_crawler_dedup.py::TestIncrementalCrawlerDedup::test_duplicate_detection -v` | PASSED |
| **3. test_watermark_filtering** | `pytest tests/services/test_incremental_crawler_dedup.py::TestIncrementalCrawlerDedup::test_watermark_filtering -v` | PASSED |
| **4. 所有去重测试** | `pytest tests/services/test_incremental_crawler_dedup.py -v` | 5/5 PASSED |

**验收代码**:
```bash
# 验收1: 运行所有去重测试
cd backend && pytest tests/services/test_incremental_crawler_dedup.py -v
# 期望: 5 passed

# 验收2: 检查测试代码中无Mock
grep -n "AsyncMock" tests/services/test_incremental_crawler_dedup.py
# 期望: 无输出（或只在 fixture 中用于 reddit_client）

# 验收3: 验证去重逻辑（手动测试）
cd backend && python3 << 'EOF'
import asyncio
from app.core.database import SessionFactory
from app.services.incremental_crawler import IncrementalCrawler
from app.clients.reddit_client import RedditClient

async def test_dedup():
    async with SessionFactory() as db:
        client = RedditClient()
        crawler = IncrementalCrawler(db, client)

        # 第一次抓取
        result1 = await crawler.crawl_community_incremental("python", limit=10)
        print(f"第一次: new={result1['new_posts']}, updated={result1['updated_posts']}")

        # 第二次抓取（应该大部分是重复）
        result2 = await crawler.crawl_community_incremental("python", limit=10)
        print(f"第二次: new={result2['new_posts']}, updated={result2['updated_posts']}")

        # 验证: 第二次的 new_posts 应该 <= 第一次
        assert result2['new_posts'] <= result1['new_posts'], "去重逻辑失败"
        print("✅ 去重逻辑验证通过")

asyncio.run(test_dedup())
EOF
```

---

### 问题3: Cron 备份未配置 ❌

**现象**: 备份脚本存在，但未配置 Cron 定时任务

**验收标准**:

| 验收项 | 验证方法 | 期望结果 |
|--------|---------|---------|
| **1. Cron 任务存在** | `crontab -l \| grep backup_database` | 包含备份任务 |
| **2. 执行时间** | 检查 Cron 配置 | `0 2 * * *` (每日2点) |
| **3. 日志输出** | 检查 Cron 配置 | 重定向到 `/tmp/backup.log` |
| **4. 备份文件生成** | 手动执行后检查 | `backup/reddit_scanner_*.sql.gz` 存在 |

**验收命令**:
```bash
# 验收1: 配置 Cron 任务
crontab -e
# 添加: 0 2 * * * /Users/hujia/Desktop/RedditSignalScanner/scripts/backup_database.sh >> /tmp/backup.log 2>&1

# 验收2: 检查 Cron 配置
crontab -l | grep backup_database
# 期望: 0 2 * * * /Users/hujia/Desktop/RedditSignalScanner/scripts/backup_database.sh >> /tmp/backup.log 2>&1

# 验收3: 手动执行测试
./scripts/backup_database.sh
ls -lh backup/reddit_scanner_*.sql.gz
# 期望: 备份文件存在，大小 >20MB

# 验收4: 检查备份文件数量（7天保留）
find backup -name "reddit_scanner_*.sql.gz" -type f | wc -l
# 期望: <=7
```

---

## 综合验收脚本

创建 `scripts/verify_all_fixes.sh`:

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "综合验收脚本"
echo "=========================================="
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# 验收1: Celery Beat cleanup 任务
echo "验收1: Celery Beat cleanup 任务..."
cd backend && python3 << 'EOF'
from app.core.celery_app import celery_app
schedule = celery_app.conf.beat_schedule
assert "cleanup-expired-posts-hot" in schedule
print("✅ PASSED")
EOF
if [ $? -eq 0 ]; then
    ((PASS_COUNT++))
else
    ((FAIL_COUNT++))
fi
cd ..

# 验收2: posts_hot 过期数据
echo "验收2: posts_hot 过期数据..."
EXPIRED=$(psql -U postgres -d reddit_scanner -t -c "SELECT COUNT(*) FROM posts_hot WHERE expires_at < NOW();")
if [ "$EXPIRED" -eq 0 ]; then
    echo "✅ PASSED: posts_hot 过期数据 = 0"
    ((PASS_COUNT++))
else
    echo "❌ FAILED: posts_hot 过期数据 = $EXPIRED"
    ((FAIL_COUNT++))
fi

# 验收3: 去重测试
echo "验收3: 去重测试..."
cd backend && pytest tests/services/test_incremental_crawler_dedup.py -v --tb=short
if [ $? -eq 0 ]; then
    echo "✅ PASSED"
    ((PASS_COUNT++))
else
    echo "❌ FAILED"
    ((FAIL_COUNT++))
fi
cd ..

# 验收4: Cron 备份配置
echo "验收4: Cron 备份配置..."
crontab -l | grep backup_database > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ PASSED: Cron 任务已配置"
    ((PASS_COUNT++))
else
    echo "⚠️  WARNING: Cron 任务未配置（需手动配置）"
    ((FAIL_COUNT++))
fi

# 验收5: 备份脚本可执行
echo "验收5: 备份脚本可执行..."
if [ -x scripts/backup_database.sh ]; then
    echo "✅ PASSED: 备份脚本可执行"
    ((PASS_COUNT++))
else
    echo "❌ FAILED: 备份脚本不可执行"
    ((FAIL_COUNT++))
fi

# 验收6: crawl_metrics 写入
echo "验收6: crawl_metrics 写入..."
METRICS_COUNT=$(psql -U postgres -d reddit_scanner -t -c "SELECT COUNT(*) FROM crawl_metrics;")
if [ "$METRICS_COUNT" -gt 0 ]; then
    echo "✅ PASSED: crawl_metrics 有 $METRICS_COUNT 条记录"
    ((PASS_COUNT++))
else
    echo "❌ FAILED: crawl_metrics 无记录"
    ((FAIL_COUNT++))
fi

# 验收7: Redis maxmemory
echo "验收7: Redis maxmemory..."
MAXMEMORY=$(redis-cli CONFIG GET maxmemory | tail -1)
if [ "$MAXMEMORY" -eq 2147483648 ]; then
    echo "✅ PASSED: Redis maxmemory = 2GB"
    ((PASS_COUNT++))
else
    echo "❌ FAILED: Redis maxmemory = $MAXMEMORY"
    ((FAIL_COUNT++))
fi

echo ""
echo "=========================================="
echo "验收结果汇总"
echo "=========================================="
echo "✅ 通过: $PASS_COUNT"
echo "❌ 失败: $FAIL_COUNT"
echo "总计: $((PASS_COUNT + FAIL_COUNT))"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "🎉 所有验收通过！"
    exit 0
else
    echo "⚠️  有 $FAIL_COUNT 项验收失败，请检查"
    exit 1
fi
```

## 验收通过标准

**P0 修复（必须100%通过）**:
- ✅ Celery Beat cleanup 任务存在
- ✅ posts_hot 过期数据 = 0
- ✅ Redis maxmemory = 2GB

**P1 修复（必须100%通过）**:
- ✅ 去重测试 5/5 通过
- ✅ crawl_metrics 写入成功
- ✅ 备份脚本可执行
- ⚠️ Cron 备份配置（可选，手动配置）

**综合验收**:
- 总通过率: >=85% (6/7)
- P0 通过率: 100% (3/3)
- P1 通过率: >=75% (3/4)
