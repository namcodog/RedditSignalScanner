# Spec 013 · 运维计划（Runbook）

**最后更新**：2025-11-14 22:30
**版本**：v3.0（基于社区分级策略：176个保留社区）

面向目标：基于数据驱动的社区分级策略，优先抓取高价值社区的全量数据（帖子+评论），实现"社区池→调度→抓取→存储→分析→报告"的闭环长期稳定运转，并具备断线自愈、零浪费写入与可观测性。

---

## 📊 重要更新（v3.0）

### 执行发现（2025-11-14）

**已完成的全量抓取验证**：
- ✅ 成功抓取260个社区
- ✅ 获取125,045个不重复帖子
- ✅ 多策略抓取（top + new + hot）正常工作
- ✅ 平均每社区481个帖子
- ✅ 数据完整性100%（无空标题，无重复）
- ✅ 数据已备份：`backups/reddit_signal_scanner_20251114_184935.sql.gz`（76MB）

**数据分析结论**：
- 📊 社区分布呈现明显的"二八定律"
- 📊 78个高活跃社区（1000+帖子）贡献了74.7%的数据
- 📊 47个低活跃社区（<50帖子）仅贡献1.0%的数据
- 📊 数据质量：90.5%的帖子有正分，81.5%的帖子有评论

**社区分级策略**：
1. **高价值社区（78个）**：1000+帖子，占74.7%数据 → 全量抓取（帖子+评论）
2. **次高价值社区（21个）**：500-999帖子，占12.0%数据 → 抓取最近12个月（帖子+评论）
3. **扩展语义社区（77个）**：100-499帖子，占10.2%数据 → 抓取最近12个月（仅帖子）
4. **待清理社区（47个）**：<50帖子，占1.0%数据 → 停止抓取，保留历史数据

**最终决策**：
- ✅ 保留176个社区（78+21+77），覆盖96.9%的数据
- ❌ 移除47个社区，仅损失1.0%的数据
- 🎯 性价比：用67.7%的社区，覆盖96.9%的数据

---

## 1. 目标与SLO

### 1.1 数据产出目标（基于分级策略）

**阶段1：高价值社区全量抓取（优先级最高）**：

- 目标：78个高价值社区 × 全量帖子 = 约93,463个帖子
- 策略：多策略抓取（top + new + hot），平均每社区1,200个帖子
- 评论：全量评论抓取（预计平均20条/帖子 = 约187万条评论）
- 时间：预计3-5天完成（取决于API配额和并发数）
- 更新频率：每15分钟增量更新

**阶段2：次高价值社区12个月数据抓取**：

- 目标：21个次高价值社区 × 最近12个月帖子 = 约8,000个帖子
- 策略：抓取最近12个月的帖子（time_filter=year）
- 评论：全量评论抓取（预计约16万条评论）
- 时间：预计1-2天完成
- 更新频率：每30分钟增量更新

**阶段3：扩展语义社区12个月数据抓取**：

- 目标：77个扩展语义社区 × 最近12个月帖子 = 约6,000个帖子
- 策略：仅抓取帖子，不抓取评论（节省资源）
- 时间：预计1天完成
- 更新频率：每2小时增量更新

**日常更新阶段（稳态运行）**：

- 日新增帖子：176社区 × 平均1条/天 = 约176条/天
- 热门帖子评论更新：每天更新Top 100热门帖子的新评论
- 稳态良好标准：日增150-250条新帖子 + 1000-2000条新评论

### 1.2 稳定性目标

- **Celery健康**：
  - 2个Worker进程（每个concurrency=2）+ 1个Beat进程
  - reserved backlog < 100
  - 失败率 < 5%
  
- **断线自愈**：
  - 网络/进程故障 ≤ 1分钟自动恢复
  - 水位线续跑（断点续抓）
  
- **零浪费**：
  - 冷库（posts_raw）：SCD2版本控制 + 增量去重
  - 热库（posts_hot）：覆盖写入 + TTL（180天）
  - 无长时间空转

### 1.3 可观测性目标

- 每日增长快照：`make posts-growth-7d`
- Beat/Pool/Redis健康报告：`make pipeline-health`
- 任务痕迹可追溯：`make celery-meta-count`

---

## 2. 数据生产流程

### 2.1 核心流程

```
社区池（166个） 
    ↓
Celery Beat调度（T1:2h, T2:4h, T3:6h）
    ↓
抓取帖子（3分钟，166社区 × 60帖子）
    ↓
存储帖子到冷库（posts_raw，SCD2去重）
    ↓
存储帖子到热库（posts_hot，覆盖写入）
    ↓
异步抓取评论（2.8小时，9,960帖子 × 全量评论）
    ↓
存储评论（comments表，通过source_post_id关联帖子）
    ↓
数据积累（17天 → 166,000帖子 + 1,660,000评论）
    ↓
分析引擎（信号提取/聚类分层/量化）
    ↓
报告生成（controlled_summary_v2 + 质量门禁）
```

### 2.2 分离抓取架构（已确认合理）

**为什么帖子和评论分离抓取？**

✅ **这是正确的设计！** 原因：

1. **Reddit API限制**：60次请求/分钟，20秒超时，建议 ≤ 6个并发
2. **快速获得帖子数据**：帖子3分钟 vs 一次性抓取4小时
3. **容错性更好**：可单独重试，不会整个社区数据丢失
4. **资源利用更高效**：帖子CPU密集，评论IO密集，可并行处理
5. **支持增量更新**：新帖子先抓取，评论稍后补充

**是否影响算法分析？**

✅ **不影响！** 帖子和评论通过外键关联：`posts_raw.source_post_id ←→ comments.source_post_id`

唯一影响是时间差（帖子3分钟，评论2.8小时），可以通过优先级队列优化。

---

## 3. 社区池管理

### 3.1 当前社区池（2025-11-14 v3.0）

**基本信息**：

- 总数：176个保留社区（从260个抓取验证中筛选）
- 数据源：社区分级CSV文件（根目录）
- 分级依据：帖子数、活跃度、数据质量、语义价值

**分级分布**：

| 级别 | 帖子数范围 | 社区数量 | 总帖子数 | 占比 | 抓取策略 |
|------|-----------|---------|---------|------|----------|
| 高价值 | 1000+ | 78 | 93,463 | 74.7% | 全量抓取（帖子+评论），每15分钟更新 |
| 次高价值 | 500-999 | 21 | 15,016 | 12.0% | 抓取最近12个月（帖子+评论），每30分钟更新 |
| 扩展语义 | 100-499 | 77 | 12,717 | 10.2% | 抓取最近12个月（仅帖子），每2小时更新 |
| **保留总计** | - | **176** | **121,196** | **96.9%** | - |
| 待清理 | 0-49 | 47 | 1,249 | 1.0% | 停止抓取，保留历史数据 |

**数据文件**：

- `高价值社区池_78个.csv`：核心数据源，包含16个维度的详细统计
- `次高价值社区池_21个.csv`：补充数据源，细分领域洞察
- `扩展语义社区池_77个.csv`：语义多样性，长尾覆盖
- `待清理社区列表_47个.csv`：低价值社区，建议移除
- `社区分级汇总报告.csv`：汇总统计 + 抓取策略
- `社区分级价值证明报告.md`：详细的价值证明维度分析

### 3.2 社区池清理

**清理命令**（移除47个低价值社区）：

```bash
cd backend && python scripts/cleanup_low_value_communities.py
```

**验证命令**：

```bash
# 查看社区池统计
make pool-stats

# 预期：176个社区（78 高价值 + 21 次高价值 + 77 扩展语义）
```

---

## 4. 抓取策略与参数

### 4.1 Reddit API限制

- **速率限制**：60次请求/分钟（实际配置58次，留2次buffer）
- **单次请求**：最多100个帖子
- **历史数据上限**：1000个帖子/社区（Reddit硬限制）
- **超时时间**：20秒/请求
- **并发限制**：建议 ≤ 6个并发

### 4.2 抓取参数配置

**帖子抓取参数**：
```yaml
# backend/config/crawler.yml
tiers:
  - name: T1
    match_tiers: ["high"]
    re_crawl_frequency: "2h"
    time_filter: "all"  # 全量历史数据
    post_limit: 60      # 每次抓取60个帖子
    
  - name: T2
    match_tiers: ["medium"]
    re_crawl_frequency: "4h"
    time_filter: "all"
    post_limit: 60
    
  - name: T3
    match_tiers: ["low"]
    re_crawl_frequency: "6h"
    time_filter: "all"
    post_limit: 60
```

**评论抓取参数**：
```bash
# backend/.env
CRAWLER_POST_LIMIT=60           # 每次抓取60个帖子
ENABLE_COMMENTS_SYNC=true       # 开启评论同步
COMMENTS_TOPN_LIMIT=999999      # 全量评论（不限制）
```

### 4.3 抓取时间线

**Day 1-17（历史数据抓取）**：
- 每天抓取：166社区 × 60帖子 = 9,960帖子
- 17天完成：166社区 × 1000帖子 = 166,000帖子
- 评论抓取：每个帖子全量评论（预计1,660,000条）

**Day 18+（日常更新）**：
- 每天抓取新帖子：166社区 × 平均1条 = 166条
- 更新热门帖子评论：Top 100帖子的新评论

---

## 5. 环境与固定入口

### 5.1 启动与守护

```bash
# 启动Redis
make redis-start

# 启动Celery（Beat + Worker）
make dev-celery-beat

# 启动自愈守护（可选）
make autoheal-start
```

### 5.2 健康快照/增长观测

```bash
# Beat/Pool/Redis/7天增长一键报告
make pipeline-health

# 最近7天posts_hot日增CSV
make posts-growth-7d

# Redis celery-task-meta-* 计数
make celery-meta-count
```

### 5.3 社区池管理

```bash
# 导入166个跨境电商社区
cd backend && PYTHONPATH=. python scripts/import_166_crossborder_communities.py

# 查看社区池统计
make pool-stats
```

---

## 6. 首次上线（Day 0）

### 6.1 启动基础服务

```bash
# 1. 启动Redis
make redis-start

# 2. 确认环境变量
cat backend/.env | grep REDDIT_CLIENT_ID
cat backend/.env | grep REDDIT_CLIENT_SECRET

# 3. 启动Celery
make dev-celery-beat

# 4. 启动自愈守护（可选）
make autoheal-start
```

### 6.2 导入社区池

```bash
# 导入166个社区
cd backend && PYTHONPATH=. python scripts/import_166_crossborder_communities.py

# 验证导入结果
make pool-stats
# 预期：165个社区（15 High + 53 Medium + 97 Low）
```

### 6.3 基线快照

```bash
# 记录Beat/Pool/Redis/7天增长
make pipeline-health
```

---

## 7. 日常运行（Day 1-17）

### 7.1 每日巡检

```bash
# 1. 查看日增长
make posts-growth-7d

# 2. 查看任务痕迹
make celery-meta-count

# 3. 生成健康报告（必要时）
make pipeline-health
```

### 7.2 数据产出验证

**Day 1预期**：
- 帖子：9,960条（166社区 × 60帖子）
- 评论：约996,000条（9,960帖子 × 平均100条评论）

**Day 17预期**：
- 帖子：166,000条（166社区 × 1000帖子）
- 评论：约16,600,000条（166,000帖子 × 平均100条评论）

### 7.3 异常处理

**Celery进程异常**：
```bash
# 查看进程状态
ps aux | grep celery

# 重启Celery
pkill -f "celery.*app.core.celery_app"
make dev-celery-beat
```

**抓取速度慢**：
```bash
# 检查Redis连接
redis-cli ping

# 检查Reddit API配额
# 查看日志：backend/tmp/celery_worker*.log
```

---

## 8. 数据库架构

### 8.1 数据库信息

- **数据库名**：`reddit_signal_scanner`
- **PostgreSQL版本**：14.19
- **Alembic版本**：`20251114_000031`（最新）
- **表数量**：26张

### 8.2 核心表结构

**帖子表（冷热分离）**：
```sql
-- 冷库（历史数据，SCD2版本控制）
posts_raw (
  id bigint PRIMARY KEY,
  source_post_id varchar(100),  -- Reddit帖子ID（例如：t3_abc123）
  subreddit varchar(100),
  title text,
  body text,
  score int,
  num_comments int,
  created_utc timestamp,
  version int,                  -- SCD2版本号
  valid_from timestamp,         -- SCD2生效时间
  valid_to timestamp,           -- SCD2失效时间
  is_current boolean,           -- SCD2当前版本标记
  ...
)

-- 热库（缓存，TTL 180天）
posts_hot (
  id bigint PRIMARY KEY,
  source_post_id varchar(100),
  subreddit varchar(100),
  title text,
  body text,
  score int,
  num_comments int,
  created_utc timestamp,
  cached_at timestamp,
  expires_at timestamp,         -- TTL过期时间（默认180天）
  ...
)
```

**评论表**：
```sql
comments (
  id bigint PRIMARY KEY,
  reddit_comment_id varchar(32) UNIQUE,
  source_post_id varchar(100),  -- 外键，关联到帖子的source_post_id
  subreddit varchar(100),
  parent_id varchar(32),
  depth int,
  body text,
  author_name varchar(100),
  score int,
  created_utc timestamp,
  captured_at timestamp,
  ...
)
```

**社区池**：
```sql
community_pool (
  id bigint PRIMARY KEY,
  name varchar(100) UNIQUE,     -- 格式：r/xxx
  tier varchar(20),              -- high, medium, low
  priority varchar(20),
  categories jsonb,              -- 维度标签数组
  quality_score float,
  daily_posts int,
  is_active boolean,
  ...
)
```

### 8.3 数据关联

```sql
-- 查询某个帖子的所有评论
SELECT * FROM comments WHERE source_post_id = 't3_abc123';

-- 查询某个社区的帖子和评论统计
SELECT 
    p.title,
    p.score,
    COUNT(c.id) as comment_count
FROM posts_raw p
LEFT JOIN comments c ON p.source_post_id = c.source_post_id
WHERE p.subreddit = 'r/ecommerce'
GROUP BY p.id;
```

---

## 9. 持续抓取详细说明

### 9.1 抓取流程

**阶段1：抓取帖子（3分钟）**
```
Celery Beat触发 → 
遍历166个社区 → 
每个社区抓取60个帖子（time_filter=all, sort=top） →
存储到posts_raw（SCD2去重） →
存储到posts_hot（覆盖写入）
```

**阶段2：抓取评论（2.8小时，异步）**
```
从posts_hot获取新帖子列表 →
遍历每个帖子 →
抓取全量评论（mode=full） →
存储到comments表（通过source_post_id关联）
```

### 9.2 水位线机制（断点续抓）

```python
# 每个社区维护一个水位线（最后抓取的帖子ID）
watermark = {
    "r/ecommerce": "t3_abc123",
    "r/Etsy": "t3_def456",
    ...
}

# 下次抓取时，从水位线之后开始
# 避免重复抓取，节省API配额
```

### 9.3 429限流处理

```python
# 遇到429错误时：
# 1. 优先使用Retry-After头（Reddit返回的等待时间）
# 2. 否则使用指数退避（1s → 2s → 4s → 8s → ...）
# 3. 最多重试5次，超过则跳过该社区
```

---

## 10. 监控与告警

### 10.1 关键指标

**数据产出指标**：
- 日增帖子数：`SELECT COUNT(*) FROM posts_hot WHERE cached_at > NOW() - INTERVAL '1 day'`
- 日增评论数：`SELECT COUNT(*) FROM comments WHERE captured_at > NOW() - INTERVAL '1 day'`

**服务健康指标**：
- Celery Worker数量：`ps aux | grep "celery.*worker" | wc -l`
- Redis连接状态：`redis-cli ping`
- 数据库连接数：`SELECT count(*) FROM pg_stat_activity`

**API配额指标**：
- 每分钟请求数：从日志统计
- 429错误率：从日志统计

### 10.2 告警阈值

- 日增帖子数 < 5000：⚠️ 警告（可能是抓取速度慢）
- 日增帖子数 < 1000：🚨 严重（抓取可能停止）
- Celery Worker数量 < 2：🚨 严重（服务异常）
- 429错误率 > 10%：⚠️ 警告（API配额不足）

---

## 11. 执行计划（v3.0）

### 11.1 立即执行（2025-11-14 22:30）

**任务1：清理社区池**

```bash
# 1. 生成清理脚本
cd backend && python scripts/cleanup_low_value_communities.py

# 2. 验证清理结果
make pool-stats
# 预期：176个社区（78+21+77）

# 3. 备份数据库
pg_dump -U postgres reddit_signal_scanner | gzip > backups/before_cleanup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**任务2：更新抓取配置**

```bash
# 1. 更新crawler.yml配置
# 高价值社区：每15分钟更新
# 次高价值社区：每30分钟更新
# 扩展语义社区：每2小时更新

# 2. 重启Celery服务
pkill -f "celery.*app.core.celery_app"
make dev-celery-beat
```

**任务3：启动高价值社区全量抓取**

```bash
# 1. 确认环境变量
cat backend/.env | grep ENABLE_COMMENTS_SYNC
# 确保：ENABLE_COMMENTS_SYNC=true

# 2. 手动触发高价值社区抓取
cd backend && python -c "
from app.core.celery_app import celery_app
result = celery_app.send_task('tasks.crawler.crawl_high_value_communities')
print(f'✅ 已触发高价值社区抓取任务，Task ID: {result.id}')
"

# 3. 监控抓取进度
tail -f backend/tmp/celery_worker.log | grep -E "📊|开始爬取|缓存.*个帖子"
```

### 11.2 预期结果

**阶段1：高价值社区全量抓取（3-5天）**

- 抓取78个社区，约93,463个帖子
- 抓取约187万条评论
- 数据存储到posts_raw和posts_hot
- 评论存储到comments表

**阶段2：次高价值社区12个月数据抓取（1-2天）**

- 抓取21个社区，约8,000个帖子
- 抓取约16万条评论

**阶段3：扩展语义社区12个月数据抓取（1天）**

- 抓取77个社区，约6,000个帖子
- 不抓取评论（节省资源）

**总计**：

- 帖子：约107,463个（93,463 + 8,000 + 6,000）
- 评论：约203万条（187万 + 16万）
- 时间：5-8天完成全部抓取

### 11.3 监控指标

**每日巡检**：

```bash
# 1. 查看日增长
make posts-growth-7d

# 2. 查看任务痕迹
make celery-meta-count

# 3. 生成健康报告
make pipeline-health
```

**关键指标**：

- 日增帖子数：预计5,000-10,000个（阶段1）
- 日增评论数：预计50,000-100,000条（阶段1）
- Celery Worker数量：≥2个
- 429错误率：<5%

---

**最后更新**：2025-11-14 22:30
**执行人**：运维工程师
**版本**：v3.0
**状态**：社区分级完成，等待清理社区池并启动高价值社区全量抓取

