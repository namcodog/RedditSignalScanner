# 系统全面状态分析报告（Serena深度分析）

**日期**: 2025-11-14 14:55  
**分析工具**: Serena MCP + PostgreSQL + 文件系统扫描  
**执行人**: 运维工程师

---

## 📊 一、数据库状态（✅ 健康）

### 1.1 数据库基本信息
- **数据库名**: `reddit_signal_scanner`
- **PostgreSQL版本**: 14.19 (Homebrew) on aarch64-apple-darwin24.4.0
- **Alembic迁移版本**: `20251114_000031` (最新)
- **测试数据库**: `reddit_signal_scanner_test` (独立)
- **已删除**: `reddit_scanner` (旧库，污染数据已清除) ✅

### 1.2 数据表统计（26张表）

| 表名 | 记录数 | 状态 | 说明 |
|------|--------|------|------|
| **community_pool** | 260 | ✅ 健康 | 260个核心社区已导入 |
| **posts_raw** | 127,924 | ✅ 健康 | 冷库，260个社区的历史数据 |
| **posts_hot** | 30 | ⚠️ 测试数据 | 热缓存，仅3个社区的测试数据 |
| **comments** | 108,333 | ✅ 健康 | 评论数据已存在 |
| **content_labels** | 134,691 | ✅ 健康 | 痛点/解决方案标签 |
| **content_entities** | 89 | ✅ 正常 | 品牌/特征/平台实体 |
| **community_cache** | 22 | ✅ 正常 | 社区元数据缓存 |
| **authors** | - | ✅ 已创建 | 作者元数据表 |
| **subreddit_snapshots** | - | ✅ 已创建 | 社区快照表 |
| **maintenance_audit** | - | ✅ 已创建 | 维护审计表 |

**其他表**: analyses, beta_feedback, cleanup_logs, community_import_history, crawl_metrics, discovered_communities, evidences, feedback_events, insight_cards, posts_archive, quality_metrics, reports, storage_metrics, tasks, users

### 1.3 Community Pool 详细分析

```sql
总社区数: 260
活跃社区: 260 (100%)
分层分布:
  - High Tier (T1): 33个 (12.7%) - 每2小时抓取
  - Medium Tier (T2): 103个 (39.6%) - 每4小时抓取
  - Low Tier (T3): 124个 (47.7%) - 每6小时抓取
```

**分层策略**:
- **T1 (High)**: post_count ≥ 1000 且 avg_score ≥ 50
- **T2 (Medium)**: post_count ≥ 500 或 avg_score ≥ 20
- **T3 (Low)**: 其他社区

### 1.4 数据资产分析

**posts_raw (冷库)**:
- 总帖子数: 127,924条
- 覆盖社区: 260个 (100%覆盖)
- 数据来源: 历史抓取数据
- 状态: ✅ 完整

**posts_hot (热缓存)**:
- 总帖子数: 30条
- 覆盖社区: 3个
- 时间范围: 2025-11-14 (今天的测试数据)
- 状态: ⚠️ 需要重新抓取

**comments (评论)**:
- 总评论数: 108,333条
- 状态: ✅ 已存在历史数据
- 表结构: 完整，包含 expires_at 字段

**content_labels (内容标签)**:
- 总标签数: 134,691条
- 类型: pain (痛点), solution (解决方案), other
- 状态: ✅ 已有大量标注数据

---

## 🔧 二、服务运行状态（✅ 正常）

### 2.1 Redis 服务
```
进程1: redis-server *:6379 (PID 82042) - 运行71小时
进程2: redis-server 127.0.0.1:6379 (PID 81874) - 运行25小时
状态: ✅ 正常运行
```

### 2.2 Celery 服务

**Celery Beat (调度器)**:
```
PID: 62690
命令: celery -A app.core.celery_app.celery_app beat --loglevel=info
运行时间: 0:13小时
状态: ✅ 正常运行
```

**Celery Workers (工作进程)**:
```
Worker 1 (PID 6290):  analysis/maintenance/cleanup/crawler/monitoring queues
Worker 2 (PID 62220): 通用worker, concurrency=2
Worker 3 (PID 16070): analysis/maintenance/cleanup/crawler/monitoring queues
Worker 4 (PID 5582):  analysis/maintenance/cleanup/crawler/monitoring queues
Worker 5 (PID 13820): analysis/maintenance/cleanup/crawler/monitoring queues
Worker 6 (PID 34914): 通用worker, concurrency=2
Worker 7 (PID 29709): 通用worker, concurrency=2
```

**总计**: 1个Beat + 7个Workers  
**状态**: ✅ 正常运行（可能有冗余进程）

---

## ⚙️ 三、配置分析（✅ 正确）

### 3.1 数据库配置

**backend/.env**:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner
```

**backend/alembic.ini**:
```ini
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner
```

**backend/app/core/config.py**:
```python
name = os.getenv("POSTGRES_DB", "reddit_signal_scanner")
```

✅ **结论**: 所有配置一致，指向正确的数据库

### 3.2 Reddit API 配置

```bash
REDDIT_CLIENT_ID=USCPQ5QL140Sox3R09YZ1Q
REDDIT_CLIENT_SECRET=e7vTRMdXJIAAgvErHQwfwYpRaen0SQ
ENABLE_REDDIT_SEARCH=true
```

**速率限制** (backend/.env 第30-61行):
```bash
REDDIT_RATE_LIMIT=58                    # 每分钟58个请求
REDDIT_RATE_LIMIT_WINDOW_SECONDS=60.0   # 60秒窗口
REDDIT_MAX_CONCURRENCY=6                # 最大并发6
REDDIT_REQUEST_TIMEOUT_SECONDS=20       # 请求超时20秒
CRAWLER_POST_LIMIT=50                   # 每次抓取50个帖子
ENABLE_COMMENTS_SYNC=true               # 启用评论同步
COMMENTS_TOPN_LIMIT=20                  # 每个帖子抓取Top 20评论
```

✅ **结论**: 速率配置合理，符合Reddit API限制

### 3.3 抓取策略配置 (backend/config/crawler.yml)

**全局配置**:
```yaml
concurrency: 4                    # 全局最大并发
scheduler_batch_size: 12          # 每批12个社区
hot_cache_ttl_hours: 48           # 热缓存48小时
watermark_enabled: false          # 🔥 临时禁用水位线，抓取所有历史数据
```

**分层策略**:
```yaml
T1 (High):
  - 频率: 每2小时
  - 时间过滤: all (所有历史数据)
  - 排序混合: top 40%, new 40%, hot 20%
  - 帖子限制: 100条
  - 热缓存TTL: 24小时

T2 (Medium):
  - 频率: 每4小时
  - 时间过滤: all (所有历史数据)
  - 排序混合: top 50%, new 30%, hot 20%
  - 帖子限制: 100条
  - 热缓存TTL: 48小时

T3 (Low):
  - 频率: 每6小时
  - 时间过滤: all (所有历史数据)
  - 排序混合: top 60%, new 20%, hot 20%
  - 帖子限制: 100条
  - 热缓存TTL: 72小时
```

✅ **结论**: 配置符合Spec 013要求，临时禁用水位线以抓取历史数据

---

## 📁 四、文件系统分析

### 4.1 脚本文件统计

**backend/scripts/** (120个脚本):
- 导入脚本: `import_*.py` (10+个)
- 抓取脚本: `crawl_*.py` (15+个)
- 分析脚本: `semantic_*.py`, `score_*.py` (20+个)
- 维护脚本: `pool_*.py`, `admin_*.py` (10+个)
- 测试脚本: `test_*.py` (15+个)

**scripts/** (60+个脚本):
- MCP包装器: `mcp-wrapper-*.sh` (5个)
- 测试脚本: `test-*.sh`, `*_test.sh` (15+个)
- 运维脚本: `start-*.sh`, `check-*.sh` (10+个)
- 验收脚本: `day*_acceptance.sh` (5+个)

### 4.2 数据文件统计

**backend/data/**:
- CSV文件: 15+个 (top1000, top5000, crossborder_candidates等)
- JSON文件: 10+个 (seed_communities, community_expansion等)
- 备份文件: 1个 (crossborder_candidates_scored.csv.backup_20251112_220654)
- 子目录: archive/, snapshots/, annotations/, reddit_corpus/

**项目根目录**:
- `community_list_clean.csv` (旧版)
- `community_list_clean_260.csv` (260个核心社区) ✅

### 4.3 冗余文件识别

**可能冗余的导入脚本**:
1. `backend/scripts/import_top1000_to_pool.py` - 导入Top 1000社区
2. `backend/scripts/import_hybrid_scores_to_pool.py` - 导入混合评分社区
3. `backend/scripts/import_toplists_to_pool.py` - 导入Top列表
4. `scripts/import_community_expansion.py` - 导入社区扩展
5. `backend/scripts/import_clean_260_communities.py` - ✅ 当前使用的脚本

**可能冗余的数据文件**:
1. `community_list_clean.csv` - 旧版清理列表
2. `backend/data/crossborder_candidates_scored.csv.backup_20251112_220654` - 备份文件
3. `backend/data/top1000_*.csv/json` - Top 1000数据（已被260核心社区替代）
4. `backend/data/top5000_*.csv/json` - Top 5000数据（已被260核心社区替代）
5. `backend/data/community_expansion_*.json` - 社区扩展数据（已被260核心社区替代）

---

## 🚨 五、发现的问题

### 5.1 posts_hot 数据不足 ⚠️
- **现状**: 只有30条测试数据，覆盖3个社区
- **期望**: 应该有260个社区的热缓存数据
- **原因**: 旧数据库删除后，热缓存被清空
- **影响**: 前端报告页面可能显示空数据
- **解决**: 需要重新抓取260个社区的帖子

### 5.2 Celery Worker 进程冗余 ⚠️
- **现状**: 7个Worker进程同时运行
- **期望**: 通常2-3个Worker即可
- **影响**: 资源占用较高，可能导致任务重复执行
- **解决**: 清理冗余进程，保留必要的Worker

### 5.3 冗余文件较多 ⚠️
- **现状**: 大量历史导入脚本和数据文件
- **影响**: 容易混淆，可能误用旧脚本
- **解决**: 清理或归档冗余文件

---

## ✅ 六、已完成的工作

### 6.1 阶段1：导入260个核心社区 ✅
- [x] 创建导入脚本 `backend/scripts/import_clean_260_communities.py`
- [x] 从 `community_list_clean_260.csv` 导入260个社区
- [x] 分层分配: 33 High, 103 Medium, 124 Low
- [x] 设置类别: ["crossborder", "ecommerce", "core_260"]
- [x] 验证导入: `SELECT COUNT(*) FROM community_pool` = 260

### 6.2 阶段2：创建评论表及相关表 ✅
- [x] 创建 comments 表 (21个字段，包含 expires_at)
- [x] 创建 content_labels 表 (痛点/解决方案标签)
- [x] 创建 content_entities 表 (品牌/特征/平台实体)
- [x] 创建 authors 表 (作者元数据)
- [x] 创建 subreddit_snapshots 表 (社区快照)
- [x] 创建 maintenance_audit 表 (维护审计)
- [x] 创建所有必需索引
- [x] 验证表结构: `\d comments` 显示完整字段

### 6.3 阶段3：数据库污染分析 ✅
- [x] 发现双数据库问题 (reddit_scanner vs reddit_signal_scanner)
- [x] 分析旧库数据: 25,971条帖子，277个社区，全部污染
- [x] 确认新库正确: 260个核心社区，配置一致
- [x] 删除旧库: `DROP DATABASE reddit_scanner`
- [x] 生成分析报告: `reports/phase-log/database_split_analysis_2025-11-14.md`

---

## 📋 七、下一步行动计划

### 7.1 立即执行（优先级P0）

#### 1. 清理冗余Celery进程
```bash
# 停止所有Celery进程
pkill -f "celery.*app.core.celery_app"

# 重新启动（使用Makefile）
make dev-celery-worker  # 启动2个worker
make dev-celery-beat    # 启动1个beat
```

#### 2. 重新抓取posts_hot数据
```bash
# 方式1: 使用Celery任务
cd backend
python -c "from app.tasks.crawler_task import crawl_seed_communities; crawl_seed_communities.delay()"

# 方式2: 使用脚本
cd backend
python scripts/trigger_initial_crawl.py
```

**预期结果**:
- posts_hot 应该有 260个社区 × 50-100条帖子 = 13,000-26,000条
- 覆盖所有260个核心社区
- 时间范围: 最近48小时内的热门帖子

### 7.2 清理冗余文件（优先级P1）

#### 1. 归档旧的导入脚本
```bash
mkdir -p backend/scripts/archive/import_legacy
mv backend/scripts/import_top1000_to_pool.py backend/scripts/archive/import_legacy/
mv backend/scripts/import_hybrid_scores_to_pool.py backend/scripts/archive/import_legacy/
mv backend/scripts/import_toplists_to_pool.py backend/scripts/archive/import_legacy/
mv scripts/import_community_expansion.py backend/scripts/archive/import_legacy/
```

#### 2. 归档旧的数据文件
```bash
mkdir -p backend/data/archive/legacy_community_lists
mv backend/data/top1000_*.csv backend/data/archive/legacy_community_lists/
mv backend/data/top1000_*.json backend/data/archive/legacy_community_lists/
mv backend/data/top5000_*.csv backend/data/archive/legacy_community_lists/
mv backend/data/top5000_*.json backend/data/archive/legacy_community_lists/
mv backend/data/community_expansion_*.json backend/data/archive/legacy_community_lists/
mv backend/data/crossborder_candidates_scored.csv.backup_* backend/data/archive/
mv community_list_clean.csv backend/data/archive/
```

#### 3. 保留的核心文件
- ✅ `community_list_clean_260.csv` (260个核心社区)
- ✅ `backend/scripts/import_clean_260_communities.py` (当前导入脚本)
- ✅ `backend/data/seed_communities.json` (种子社区)

### 7.3 验证与监控（优先级P2）

#### 1. 验证抓取任务
```bash
# 检查Celery Beat调度
cd backend
python scripts/check_celery_health.py

# 查看抓取指标
python scripts/crawl_metrics_latest.py
```

#### 2. 监控数据增长
```bash
# 每小时检查一次posts_hot增长
watch -n 3600 'psql -d reddit_signal_scanner -c "SELECT COUNT(*), COUNT(DISTINCT subreddit) FROM posts_hot;"'
```

#### 3. 生成健康报告
```bash
# 使用运维脚本
./scripts/crawl_health_snapshot.sh
./scripts/pipeline_health_snapshot.sh
```

---

## 📊 八、系统健康度评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **数据库结构** | ✅ 10/10 | 所有表已创建，迁移版本最新 |
| **数据完整性** | ⚠️ 7/10 | posts_raw完整，posts_hot需重新抓取 |
| **配置正确性** | ✅ 10/10 | 所有配置一致，指向正确数据库 |
| **服务运行** | ⚠️ 8/10 | Redis和Celery正常，但Worker冗余 |
| **代码整洁度** | ⚠️ 6/10 | 存在大量冗余脚本和数据文件 |
| **文档完整性** | ✅ 9/10 | 运维文档完整，分析报告详细 |

**总体评分**: ⚠️ **8.3/10** (良好，需要清理和重新抓取)

---

## 🎯 九、总结

### 9.1 核心成果 ✅
1. ✅ **删除旧数据库**: `reddit_scanner` 已删除，消除污染源
2. ✅ **260个核心社区已导入**: community_pool 完整，分层合理
3. ✅ **评论表已创建**: 包含所有必需字段和索引
4. ✅ **配置一致性**: 所有配置指向正确的数据库
5. ✅ **历史数据保留**: posts_raw 有127,924条帖子，comments 有108,333条评论

### 9.2 待解决问题 ⚠️
1. ⚠️ **posts_hot 数据不足**: 需要重新抓取260个社区的热缓存
2. ⚠️ **Celery Worker 冗余**: 7个进程运行，需要清理
3. ⚠️ **冗余文件较多**: 大量历史脚本和数据文件需要归档

### 9.3 下一步重点 🎯
1. **清理Celery进程** → 保留2个Worker + 1个Beat
2. **重新抓取posts_hot** → 覆盖260个社区，13,000-26,000条帖子
3. **归档冗余文件** → 清理历史脚本和数据文件
4. **验证数据质量** → 确保抓取任务正常运行

---

**报告生成时间**: 2025-11-14 14:55  
**下次检查时间**: 2025-11-14 18:00 (重新抓取完成后)

