# Phase 3 P0/P1 修复验收文档

## 修复概览

本次修复针对24小时运行发现的关键问题，包括：
- P0-1: posts_hot 清理任务缺失
- P0-2: Redis maxmemory 未配置
- P1-1: 去重逻辑统计不准确
- P1-2: 数据库备份机制缺失

---

## P0-1: posts_hot 清理任务

### 问题描述
- **现状**: posts_hot 表有 32,156 条记录，其中 6,412 条已过期（19.9%）
- **根因**: 无定时清理任务，导致过期数据无限累积
- **影响**: 24小时后 posts_hot 将达到 1.5GB，查询性能严重下降

### 验收标准

#### 1. 功能验收

| 验收项 | 目标值 | 验证方法 | 通过标准 |
|--------|--------|---------|---------|
| 清理任务存在 | ✅ | `celery_app.conf.beat_schedule` 包含任务 | 任务名为 `cleanup-expired-posts-hot` |
| 调度频率 | 每6小时 | 检查 `schedule` 配置 | `crontab(hour="*/6")` |
| 任务队列 | cleanup_queue | 检查 `options.queue` | 值为 `"cleanup_queue"` |
| 清理逻辑 | DELETE 过期数据 | 检查 SQL 语句 | `WHERE expires_at < NOW()` |

#### 2. 执行验收

```sql
-- 验收前: 统计过期数据
SELECT 
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE expires_at < NOW()) AS expired,
    COUNT(*) FILTER (WHERE expires_at >= NOW()) AS valid
FROM posts_hot;
-- 期望: expired > 6000

-- 执行清理任务
-- (通过 Celery 手动触发或等待定时执行)

-- 验收后: 确认过期数据已清除
SELECT COUNT(*) FROM posts_hot WHERE expires_at < NOW();
-- 期望: 0

-- 验收后: 确认有效数据保留
SELECT COUNT(*) FROM posts_hot WHERE expires_at >= NOW();
-- 期望: ~25,744（清理前的 valid 数量）
```

#### 3. 性能验收

| 验收项 | 目标值 | 验证方法 |
|--------|--------|---------|
| 执行耗时 | <10秒 | 检查任务日志 `duration` 字段 |
| 删除行数 | >6,000 | 检查任务返回值 `deleted_count` |
| 数据库锁 | 无阻塞 | 执行期间查询 `pg_stat_activity` |

#### 4. 测试用例

```bash
# 测试文件: backend/tests/tasks/test_cleanup_posts_hot.py
cd backend && pytest tests/tasks/test_cleanup_posts_hot.py -v

# 期望输出:
# test_cleanup_task_exists PASSED
# test_cleanup_removes_expired_posts PASSED
# test_cleanup_preserves_valid_posts PASSED
# test_cleanup_performance PASSED
```

---

## P0-2: Redis maxmemory 配置

### 问题描述
- **现状**: Redis 未设置 maxmemory 限制（maxmemory_human: 0B）
- **根因**: 默认配置未限制内存使用
- **影响**: 24小时后可能占用 >1GB 内存，导致系统 OOM

### 验收标准

#### 1. 配置验收

```bash
# 验收1: 检查运行时配置
redis-cli CONFIG GET maxmemory
# 期望输出:
# 1) "maxmemory"
# 2) "2147483648"  # 2GB

redis-cli CONFIG GET maxmemory-policy
# 期望输出:
# 1) "maxmemory-policy"
# 2) "allkeys-lru"

# 验收2: 检查配置文件持久化
grep -E "^maxmemory|^maxmemory-policy" /opt/homebrew/etc/redis.conf
# 期望输出:
# maxmemory 2gb
# maxmemory-policy allkeys-lru

# 验收3: 重启后配置仍生效
brew services restart redis
sleep 2
redis-cli CONFIG GET maxmemory
# 期望输出: 2147483648
```

#### 2. 内存监控验收

```bash
# 验收4: 检查当前内存使用
redis-cli INFO memory | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio"
# 期望输出:
# used_memory_human:<100M
# maxmemory_human:2.00G
# mem_fragmentation_ratio:<1.5
```

#### 3. 驱逐策略验证

```bash
# 测试场景: 写入数据直到达到 maxmemory
redis-cli << 'EOF'
FLUSHALL
CONFIG SET maxmemory 10mb
CONFIG SET maxmemory-policy allkeys-lru

# 写入大量数据
FOR i IN {1..10000}
DO
    SET test_key_$i "$(head -c 1024 /dev/urandom | base64)"
DONE

# 验证驱逐发生
INFO stats | grep evicted_keys
# 期望: evicted_keys > 0
EOF

# 恢复配置
redis-cli CONFIG SET maxmemory 2gb
```

---

## P1-1: 去重逻辑修复

### 问题描述
- **现状**: `_upsert_to_cold_storage` 总是返回 `(True, False)`，导致所有帖子都被标记为"新增"
- **根因**: 代码第258行硬编码返回值，未实际检查数据库操作结果
- **影响**: `new_posts` 统计虚高，24小时预估可能高估 2-3倍

### 验收标准

#### 1. 逻辑验收

| 场景 | 期望行为 | 验证方法 |
|------|---------|---------|
| 全新帖子 | `is_new=True, is_updated=False` | INSERT 成功 |
| 重复帖子（内容未变） | `is_new=False, is_updated=False` | ON CONFLICT 触发，但 score/comments 未变 |
| 重复帖子（score变化） | `is_new=False, is_updated=True` | ON CONFLICT 触发，score/comments 更新 |

#### 2. 单元测试

```python
# 测试文件: backend/tests/services/test_incremental_crawler_dedup.py

@pytest.mark.asyncio
async def test_new_post_detection():
    """测试新帖子识别"""
    crawler = IncrementalCrawler(db, reddit_client)
    result = await crawler.crawl_community_incremental("test_new", limit=10)
    
    assert result["new_posts"] == 10
    assert result["updated_posts"] == 0
    assert result["duplicates"] == 0

@pytest.mark.asyncio
async def test_duplicate_detection():
    """测试重复帖子识别"""
    crawler = IncrementalCrawler(db, reddit_client)
    
    # 第一次抓取
    result1 = await crawler.crawl_community_incremental("test_dup", limit=10)
    assert result1["new_posts"] == 10
    
    # 第二次抓取（相同数据）
    result2 = await crawler.crawl_community_incremental("test_dup", limit=10)
    assert result2["new_posts"] == 0
    assert result2["duplicates"] == 10

@pytest.mark.asyncio
async def test_update_detection():
    """测试更新检测（score/comments 变化）"""
    crawler = IncrementalCrawler(db, reddit_client)
    
    # 第一次抓取
    result1 = await crawler.crawl_community_incremental("test_update", limit=10)
    
    # 手动修改数据库中的 score（模拟帖子获得更多点赞）
    await db.execute(
        "UPDATE posts_raw SET score = score + 100 WHERE subreddit = 'test_update'"
    )
    
    # 第二次抓取（score 变化）
    result2 = await crawler.crawl_community_incremental("test_update", limit=10)
    assert result2["updated_posts"] > 0
```

#### 3. 集成测试

```bash
# 执行测试
cd backend && pytest tests/services/test_incremental_crawler_dedup.py -v

# 期望输出:
# test_new_post_detection PASSED
# test_duplicate_detection PASSED
# test_update_detection PASSED
```

#### 4. 真实数据验证

```sql
-- 验证去重效果
SELECT 
    source,
    source_post_id,
    COUNT(*) AS version_count
FROM posts_raw
GROUP BY source, source_post_id
HAVING COUNT(*) > 1
LIMIT 10;
-- 期望: 0 rows（无重复主键）

-- 验证更新检测
SELECT 
    source_post_id,
    version,
    score,
    fetched_at
FROM posts_raw
WHERE source_post_id IN (
    SELECT source_post_id 
    FROM posts_raw 
    GROUP BY source_post_id 
    HAVING COUNT(*) > 1
)
ORDER BY source_post_id, version;
-- 期望: 如果有多个版本，version 应递增
```

---

## P1-2: 数据库备份机制

### 问题描述
- **现状**: 无自动备份机制
- **根因**: 未配置备份脚本和 cron 任务
- **影响**: 数据丢失风险极高（24小时后数据库达到 2.6GB）

### 验收标准

#### 1. 备份脚本验收

```bash
# 验收1: 脚本存在且可执行
ls -lh scripts/backup_database.sh
# 期望: -rwxr-xr-x (可执行权限)

# 验收2: 手动执行备份
./scripts/backup_database.sh
# 期望输出:
# ✅ 开始备份数据库 reddit_scanner...
# ✅ 备份完成: backup/reddit_scanner_20251018.sql.gz
# ✅ 备份大小: 25.3 MB

# 验收3: 验证备份文件
ls -lh backup/reddit_scanner_*.sql.gz
# 期望: 文件大小 >10MB
```

#### 2. 备份内容验证

```bash
# 验收4: 验证备份可恢复
createdb reddit_scanner_test
gunzip -c backup/reddit_scanner_$(date +%Y%m%d).sql.gz | psql -U postgres reddit_scanner_test

# 验证数据完整性
psql -U postgres reddit_scanner_test << 'SQL'
SELECT 
    'posts_raw' AS table_name,
    COUNT(*) AS row_count
FROM posts_raw
UNION ALL
SELECT 'posts_hot', COUNT(*) FROM posts_hot
UNION ALL
SELECT 'community_cache', COUNT(*) FROM community_cache;
SQL
# 期望: 行数与原库一致

# 清理测试库
dropdb reddit_scanner_test
```

#### 3. Cron 配置验收

```bash
# 验收5: 验证 cron 任务配置
crontab -l | grep backup_database
# 期望输出:
# 0 2 * * * /Users/hujia/Desktop/RedditSignalScanner/scripts/backup_database.sh >> /tmp/backup.log 2>&1

# 验收6: 测试 cron 任务（手动触发）
# 修改 cron 为1分钟后执行
# */1 * * * * /path/to/backup_database.sh
# 等待1分钟后检查
ls -lt backup/ | head -5
# 期望: 看到新生成的备份文件
```

#### 4. 备份保留策略

```bash
# 验收7: 验证旧备份清理（保留7天）
# 创建模拟旧备份
touch -t 202510010000 backup/reddit_scanner_20251001.sql.gz

# 执行备份（应清理7天前的文件）
./scripts/backup_database.sh

# 验证旧文件已删除
ls backup/reddit_scanner_20251001.sql.gz
# 期望: No such file or directory
```

---

## 综合验收（24小时运行后）

### 数据量验收

```sql
-- 验收1: 24小时新增数据
SELECT 
    COUNT(*) FILTER (WHERE fetched_at > NOW() - INTERVAL '24 hours') AS new_posts_24h,
    COUNT(*) AS total_posts,
    pg_size_pretty(pg_total_relation_size('posts_raw')) AS table_size
FROM posts_raw;
-- 期望:
-- new_posts_24h: 300,000 - 600,000
-- total_posts: 330,000 - 630,000
-- table_size: 1.0GB - 2.0GB

-- 验收2: posts_hot 清理效果
SELECT 
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE expires_at < NOW()) AS expired,
    pg_size_pretty(pg_total_relation_size('posts_hot')) AS table_size
FROM posts_hot;
-- 期望:
-- total: <30,000
-- expired: 0
-- table_size: <100MB
```

### 性能验收

```sql
-- 验收3: 查询性能
EXPLAIN ANALYZE 
SELECT * FROM posts_hot 
WHERE subreddit = 'startups' 
ORDER BY created_at DESC 
LIMIT 100;
-- 期望: Execution Time < 100ms

-- 验收4: 写入性能（检查最近一次抓取）
SELECT 
    metric_date,
    metric_hour,
    total_communities,
    successful_crawls,
    valid_posts_24h,
    avg_latency_seconds
FROM crawl_metrics
ORDER BY created_at DESC
LIMIT 1;
-- 期望:
-- successful_crawls / total_communities > 0.95
-- avg_latency_seconds < 5.0
```

### 稳定性验收

```bash
# 验收5: 系统日志检查
dmesg | grep -i oom
# 期望: 无 OOM 错误

# 验收6: Celery 错误日志
grep -i "concurrent operations" /tmp/celery_worker.log
# 期望: 0 条

# 验收7: Beat 调度统计
grep "auto-crawl-incremental" /tmp/celery_beat.log | wc -l
# 期望: ~48（24小时 × 2次/小时）

# 验收8: Redis 内存使用
redis-cli INFO memory | grep used_memory_human
# 期望: <500MB
```

---

## 验收检查清单

### P0 修复（立即执行）

- [ ] posts_hot 清理任务测试通过
- [ ] 手动触发清理任务，过期数据清除
- [ ] Redis maxmemory 配置生效
- [ ] Redis 重启后配置保留

### P1 修复（24小时内）

- [ ] 去重逻辑单元测试通过
- [ ] 去重逻辑集成测试通过
- [ ] 备份脚本执行成功
- [ ] 备份文件可恢复
- [ ] Cron 任务配置正确

### 24小时后验收

- [ ] 数据量符合预期（30万-60万）
- [ ] posts_hot 无过期数据
- [ ] 查询性能 <100ms
- [ ] 无 OOM 错误
- [ ] 无并发错误
- [ ] Beat 调度正常（48次）
- [ ] Redis 内存 <500MB

---

## 验收签字

- **修复完成时间**: _______________
- **验收执行人**: _______________
- **验收结果**: [ ] 通过 [ ] 不通过
- **备注**: _______________

