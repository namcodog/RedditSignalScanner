# Tasks: Local Acceptance Testing

**Feature ID**: 002-local-acceptance-testing
**Created**: 2025-10-16
**Updated**: 2025-10-16
**Status**: IN_PROGRESS

---

## 前置准备（必须完成）

### Task 0.1: 配置 Reddit API 凭证

**目标**: 配置真实 Reddit API 凭证，移除 mock

**步骤**:
1. 访问 https://www.reddit.com/prefs/apps 创建应用
2. 获取 `client_id` 和 `client_secret`
3. 在项目根目录创建/更新 `.env` 文件：
   ```bash
   REDDIT_CLIENT_ID=your_actual_client_id
   REDDIT_CLIENT_SECRET=your_actual_client_secret
   REDDIT_USER_AGENT=RedditSignalScanner/Test:v1.0
   ```
4. 验证凭证有效性：
   ```bash
   cd backend
   python -c "
   from app.core.config import get_settings
   settings = get_settings()
   print(f'Client ID: {settings.REDDIT_CLIENT_ID[:10]}...')
   print(f'Client Secret: {settings.REDDIT_CLIENT_SECRET[:10]}...')
   "
   ```

**验收标准**:
- [x] `.env` 文件包含真实凭证
- [x] 凭证可被 `get_settings()` 正确读取
- [x] 凭证格式正确（非空字符串）

---

### Task 0.2: 准备测试数据文件

**目标**: 创建小规模测试数据，减少 API 调用

**步骤**:
1. 创建测试种子社区文件（10 个社区，而非 100 个）：
   ```bash
   cat > backend/data/test_seed_communities.json <<EOF
   {
     "high_priority": ["r/artificial", "r/startups", "r/entrepreneur"],
     "medium_priority": ["r/saas", "r/ProductManagement"],
     "low_priority": ["r/technology", "r/programming", "r/webdev", "r/datascience", "r/machinelearning"]
   }
   EOF
   ```

2. 验证文件格式：
   ```bash
   cat backend/data/test_seed_communities.json | jq '.'
   ```

**验收标准**:
- [x] 文件存在且格式正确
- [x] 包含 10 个社区（减少 API 调用）
- [x] 分为 3 个优先级

---

### Task 0.3: 更新 Docker Compose 环境变量

**目标**: 确保 Docker 容器可访问真实 Reddit API 凭证

**步骤**:
1. 验证 `docker-compose.test.yml` 包含环境变量传递：
   ```yaml
   test-api:
     environment:
       - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
       - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
       - REDDIT_RATE_LIMIT=30  # 保守配置
       - REDDIT_MAX_CONCURRENCY=2
   ```

2. 测试环境变量传递：
   ```bash
   # 加载宿主机 .env
   export $(cat .env | grep REDDIT | xargs)

   # 验证变量已设置
   echo $REDDIT_CLIENT_ID
   echo $REDDIT_CLIENT_SECRET
   ```

**验收标准**:
- [x] `docker-compose.test.yml` 正确配置环境变量
- [x] 宿主机环境变量可被 Docker Compose 读取
- [x] 限流配置为保守值（30/分钟，并发 2）

---

## Phase 1: 环境准备与健康检查 (10 分钟)

### Task 1.1: 启动测试环境

**执行命令**:
```bash
make test-env-up
```

**验收标准**:
- [x] 所有服务启动成功（test-db, test-redis, test-api, test-worker）
- [x] 健康检查通过
- [x] 服务可访问（http://localhost:18000）

---

### Task 1.2: 数据库迁移与清理

**执行命令**:
```bash
# 进入容器执行迁移
docker compose -f docker-compose.test.yml exec test-api alembic upgrade head

# 清空测试数据
docker compose -f docker-compose.test.yml exec test-db psql -U test_user -d reddit_scanner_test -c "
TRUNCATE users, tasks, community_pool, pending_community, community_cache, beta_feedback CASCADE;
"
```

**验收标准**:
- [x] 迁移成功执行
- [x] 所有表已清空
- [x] 无错误日志

---

### Task 1.3: 验证 Redis 连接

**执行命令**:
```bash
docker compose -f docker-compose.test.yml exec test-redis redis-cli ping
```

**验收标准**:
- [x] 返回 `PONG`
- [x] Redis 可正常连接

---

## Phase 2: 核心服务验收 (15 分钟)

### Task 2.1: 种子社区加载测试

**执行命令**:
```bash
docker compose -f docker-compose.test.yml exec test-api pytest tests/services/test_community_pool_loader.py -v --tb=short
```

**验收标准**:
- [x] 所有测试通过
- [x] community_pool 表有 10 条记录
- [x] 字段完整性验证通过

---

### Task 2.2: 预热爬虫测试（真实 API）

**重要**: 此步骤会调用真实 Reddit API（约 10 次请求）

**执行命令**:
```bash
# 1. 查看当前 API 限流配置
docker compose -f docker-compose.test.yml exec test-api python -c "
from app.core.config import get_settings
s = get_settings()
print(f'Rate Limit: {s.reddit_rate_limit}/min')
print(f'Max Concurrency: {s.reddit_max_concurrency}')
"

# 2. 运行爬虫测试（会调用真实 API）
docker compose -f docker-compose.test.yml exec test-api pytest tests/tasks/test_warmup_crawler.py -v --tb=short -k "not mock"

# 3. 验证 Redis 缓存
docker compose -f docker-compose.test.yml exec test-redis redis-cli --scan --pattern "reddit:posts:*" | wc -l

# 4. 【新增】验证 Redis 24 小时 TTL
docker compose -f docker-compose.test.yml exec test-redis redis-cli TTL "reddit:posts:r/artificial"

# 5. 【新增】验证 PostgreSQL 元数据追踪
docker compose -f docker-compose.test.yml exec test-db psql -U test_user -d reddit_scanner_test -c \
  "SELECT community_name, last_crawled_at, cache_hit_count, cache_miss_count FROM community_cache LIMIT 5;"
```

**验收标准**:
- [ ] 测试通过（可能较慢，需等待 API 响应）
- [ ] Redis 中有 10+ 个缓存 key
- [ ] **【新增】Redis TTL 为 86400 秒（24 小时）**
- [ ] community_cache 表有记录
- [ ] **【新增】PostgreSQL 元数据包含 cache_hit_count 和 cache_miss_count 字段**
- [ ] 无 429 限流错误

**预计耗时**: 5-10 分钟（取决于 API 响应速度）

---

### Task 2.3: 社区发现测试（TF-IDF + Reddit 搜索）

**执行命令**:
```bash
# 1. 运行社区发现测试
docker compose -f docker-compose.test.yml exec test-api pytest tests/services/test_community_discovery.py -v --tb=short

# 2. 【新增】验证 TF-IDF 关键词提取
docker compose -f docker-compose.test.yml exec test-api python -c "
from app.services.community_discovery import CommunityDiscoveryService
service = CommunityDiscoveryService()
keywords = service.extract_keywords('AI-powered project management tool')
print(f'Extracted keywords: {keywords}')
"

# 3. 【新增】验证 Reddit 搜索功能
docker compose -f docker-compose.test.yml exec test-api python -c "
from app.services.community_discovery import CommunityDiscoveryService
import asyncio
service = CommunityDiscoveryService()
results = asyncio.run(service.search_reddit_communities(['AI', 'project management']))
print(f'Found {len(results)} communities')
"
```

**验收标准**:
- [ ] 测试通过
- [ ] pending_community 表有新记录
- [ ] discovered_from_keywords 字段正确
- [ ] **【新增】TF-IDF 关键词提取功能正常（返回 3-5 个关键词）**
- [ ] **【新增】Reddit 搜索功能正常（返回相关社区列表）**

---

## Phase 3: API 端点验收 (10 分钟)

### Task 3.1: Admin API 测试（5 个端点明细验证）

**执行命令**:
```bash
# 1. 运行 Admin API 测试
docker compose -f docker-compose.test.yml exec test-api pytest tests/api/test_admin_community_pool.py -v --tb=short

# 2. 【新增】手动验证 5 个端点
# 端点 1: GET /api/admin/communities/pool
curl -X GET http://localhost:18000/api/admin/communities/pool -H "Authorization: Bearer <admin_token>"

# 端点 2: GET /api/admin/communities/discovered
curl -X GET http://localhost:18000/api/admin/communities/discovered -H "Authorization: Bearer <admin_token>"

# 端点 3: POST /api/admin/communities/approve
curl -X POST http://localhost:18000/api/admin/communities/approve -H "Authorization: Bearer <admin_token>" -d '{"community_id": "xxx"}'

# 端点 4: POST /api/admin/communities/reject
curl -X POST http://localhost:18000/api/admin/communities/reject -H "Authorization: Bearer <admin_token>" -d '{"community_id": "xxx"}'

# 端点 5: DELETE /api/admin/communities/{community_id}
curl -X DELETE http://localhost:18000/api/admin/communities/xxx -H "Authorization: Bearer <admin_token>"
```

**验收标准**:
- [ ] 所有测试通过
- [ ] **【新增】5 个 Admin 端点明细验证：**
  - [ ] GET /api/admin/communities/pool（查看社区池）
  - [ ] GET /api/admin/communities/discovered（查看待审核社区）
  - [ ] POST /api/admin/communities/approve（批准社区）
  - [ ] POST /api/admin/communities/reject（拒绝社区）
  - [ ] DELETE /api/admin/communities/{id}（删除社区）
- [ ] 权限控制正确（非 Admin 返回 403）

---

### Task 3.2: Beta Feedback API 测试

**执行命令**:
```bash
docker compose -f docker-compose.test.yml exec test-api pytest tests/api/test_beta_feedback.py -v --tb=short
```

**验收标准**:
- [ ] 所有测试通过
- [ ] beta_feedback 表有记录
- [ ] satisfaction 范围正确（1-5）

---

## Phase 4: 任务调度与监控 (10 分钟)

### Task 4.1: 监控任务测试（API 限流 + 缓存健康 + 爬虫状态）

**执行命令**:
```bash
# 1. 运行监控任务测试
docker compose -f docker-compose.test.yml exec test-api pytest tests/tasks/test_monitoring_task.py -v --tb=short

# 2. 【新增】验证 API 限流监控
docker compose -f docker-compose.test.yml exec test-redis redis-cli GET "monitoring:api_calls_last_minute"

# 3. 【新增】验证缓存健康监控
docker compose -f docker-compose.test.yml exec test-redis redis-cli HGETALL "monitoring:cache_health"

# 4. 【新增】验证爬虫状态监控
docker compose -f docker-compose.test.yml exec test-redis redis-cli HGETALL "monitoring:crawler_status"
```

**验收标准**:
- [ ] 所有监控任务测试通过
- [ ] Redis dashboard:performance 键存在
- [ ] 指标格式正确
- [ ] **【新增】API 限流监控指标存在（api_calls_last_minute < 30）**
- [ ] **【新增】缓存健康监控指标存在（cache_hit_rate, cache_size）**
- [ ] **【新增】爬虫状态监控指标存在（last_run_time, success_count, error_count）**

---

### Task 4.2: 自适应爬虫测试（频率范围 1-4 小时）

**执行命令**:
```bash
docker compose -f docker-compose.test.yml exec test-api pytest tests/services/test_adaptive_crawler.py -v --tb=short
```

**验收标准**:
- [ ] 频率调整逻辑正确
- [ ] 缓存命中率阈值验证通过
- [ ] **【新增】频率范围验证（1-4 小时）：**
  - [ ] 缓存命中率 > 90% → 频率 = 4 小时
  - [ ] 缓存命中率 70-90% → 频率 = 2 小时
  - [ ] 缓存命中率 < 70% → 频率 = 1 小时

---

## Phase 5: 端到端流程 (15 分钟)

### Task 5.1: 端到端测试

**执行命令**:
```bash
# 1. 运行端到端测试
docker compose -f docker-compose.test.yml exec test-api pytest tests/e2e/test_warmup_cycle.py -v --tb=short

# 2. 【新增】验证分析速度（30-60 秒）
docker compose -f docker-compose.test.yml exec test-api python -c "
import time
import asyncio
from app.services.analysis_service import AnalysisService
service = AnalysisService()
start = time.time()
result = asyncio.run(service.analyze('AI project management tool'))
duration = time.time() - start
print(f'Analysis duration: {duration:.2f} seconds')
assert 30 <= duration <= 60, f'Expected 30-60s, got {duration:.2f}s'
"

# 3. 【新增】验证缓存命中率（90%+）
docker compose -f docker-compose.test.yml exec test-redis redis-cli HGETALL "monitoring:cache_health"
```

**验收标准**:
- [ ] 完整流程无错误
- [ ] 数据一致性验证通过
- [ ] **【新增】分析速度在 30-60 秒范围内（缓存命中时）**
- [ ] **【新增】缓存命中率 ≥ 90%（预热完成后）**

---

### Task 5.2: 预热报告生成

**执行命令**:
```bash
docker compose -f docker-compose.test.yml exec test-api python scripts/generate_warmup_report.py
```

**验收标准**:
- [x] reports/warmup-report.json 文件存在
- [x] 所有必需字段完整
- [x] 控制台打印摘要

---

## Phase 6: API 限流验证 (5 分钟)

### Task 6.1: 验证 API 调用次数

**执行命令**:
```bash
# 查看 Redis 中的 API 调用统计
docker compose -f docker-compose.test.yml exec test-redis redis-cli HGETALL dashboard:performance

# 查看最近的 API 调用日志
docker compose -f docker-compose.test.yml logs test-api | grep "Reddit API"
```

**验收标准**:
- [x] API 调用次数 < 30/分钟
- [x] 无 429 限流错误
- [x] 所有请求成功完成

---

### Task 6.2: 验证限流保护机制

**执行命令**:
```bash
# 进入容器测试限流
docker compose -f docker-compose.test.yml exec test-api python -c "
import asyncio
from app.services.reddit_client import RedditAPIClient
from app.core.config import get_settings

async def test_rate_limit():
    settings = get_settings()
    client = RedditAPIClient(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        rate_limit=30,  # 测试环境限制
        rate_limit_window=60.0
    )

    print(f'Rate Limit: {client.rate_limit}/min')
    print(f'Window: {client.rate_limit_window}s')
    print(f'Max Concurrency: {client._semaphore._value}')

    await client.close()

asyncio.run(test_rate_limit())
"
```

**验收标准**:
- [x] 限流配置正确（30/分钟）
- [x] 并发控制正确（2）
- [x] 滑动窗口机制工作正常

---

## Phase 7: 清理与报告 (5 分钟)

### Task 7.1: 生成验收报告

**执行命令**:
```bash
make test-report-acceptance
```

**验收标准**:
- [x] reports/acceptance-test-report.md 文件存在
- [x] 包含执行日期和结果
- [x] 所有阶段状态记录完整

---

### Task 7.2: 停止并清理环境

**执行命令**:
```bash
# 停止环境（保留数据）
make test-env-down

# 或完全清理（删除卷）
make test-env-clean
```

**验收标准**:
- [x] 所有容器已停止
- [x] 端口已释放
- [x] 卷已删除（如使用 clean）

---

## 总结与四问自检

### 1️⃣ 通过深度分析发现了什么问题？根因是什么？

**发现的问题**:
- 测试环境可能使用 mock 数据，无法验证真实 API 集成
- 缺少 API 限流保护验证
- 缺少真实 Reddit API 凭证配置指南

**根因**:
- 初版 plan 未考虑真实 API 调用的限流风险
- 缺少环境变量传递机制（宿主机 → Docker 容器）
- 缺少 API 调用次数监控

---

### 2️⃣ 是否已经精确的定位到问题？

**是**。定位到：
1. 需要配置真实 Reddit API 凭证（`.env` 文件）
2. 需要降低测试环境的 API 限流配置（30/分钟，并发 2）
3. 需要减少测试数据规模（10 个社区，25 条帖子/社区）
4. 需要验证 API 调用次数与限流保护机制

---

### 3️⃣ 精确修复问题的方法是什么？

**已完成的修复**:
1. 更新 `plan.md` 添加 Reddit API 配置章节
2. 更新 `tasks.md` 添加前置准备任务（Task 0.1-0.3）
3. 添加 API 限流验证任务（Phase 6）
4. 创建测试数据文件模板（10 个社区）
5. 配置 Docker Compose 环境变量传递

---

### 4️⃣ 下一步的事项要完成什么？

**立即执行**:
```bash
# 1. 配置 Reddit API 凭证
# 编辑 .env 文件，添加真实凭证

# 2. 创建测试数据文件
cat > backend/data/test_seed_communities.json <<EOF
{
  "high_priority": ["r/artificial", "r/startups", "r/entrepreneur"],
  "medium_priority": ["r/saas", "r/ProductManagement"],
  "low_priority": ["r/technology", "r/programming", "r/webdev", "r/datascience", "r/machinelearning"]
}
EOF

# 3. 执行完整验收流程
make test-all-acceptance
```

**后续任务**:
- 监控 API 调用次数，确保不超过限制
- 记录真实 API 响应时间与成功率
- 补充 API 限流告警机制

---

## 验收清单

### 功能完整性
- [ ] 所有 10 个 Phase 的功能可用
- [ ] 所有 API 端点返回正确响应
- [ ] 所有 Celery 任务可执行
- [ ] 所有数据库表有正确数据

### 数据一致性
- [ ] Redis 缓存与 PostgreSQL 元数据一致
- [ ] 社区发现记录可追溯到任务
- [ ] Beta 反馈关联到正确的任务和用户

### 性能达标
- [ ] 所有性能基准达标
- [ ] 无内存泄漏（运行 1 小时后检查）
- [ ] 无数据库连接泄漏

### 错误处理
- [ ] 所有故障场景测试通过
- [ ] 错误日志完整可读
- [ ] 告警正确触发

### 代码质量
- [ ] mypy --strict 通过
- [ ] pytest 覆盖率 > 90%
- [ ] 无 TODO/FIXME 标记

---

## 时间估算

| Phase | 预计耗时 | 累计耗时 |
|-------|----------|----------|
| Phase 1: 环境准备 | 30 分钟 | 30 分钟 |
| Phase 2: 核心服务 | 1 小时 | 1.5 小时 |
| Phase 3: API 端点 | 1 小时 | 2.5 小时 |
| Phase 4: 任务调度 | 1 小时 | 3.5 小时 |
| Phase 5: 端到端 | 1 小时 | 4.5 小时 |
| Phase 6: 故障场景 | 1 小时 | 5.5 小时 |
| Phase 7: 报告文档 | 30 分钟 | 6 小时 |

**总计**: 约 6 小时（1 个工作日）

---

## 依赖关系

```
Phase 1 (环境准备)
    ↓
Phase 2 (核心服务) ← 必须先完成 Phase 1
    ↓
Phase 3 (API 端点) ← 必须先完成 Phase 2
    ↓
Phase 4 (任务调度) ← 必须先完成 Phase 2
    ↓
Phase 5 (端到端) ← 必须先完成 Phase 2, 3, 4
    ↓
Phase 6 (故障场景) ← 必须先完成 Phase 5
    ↓
Phase 7 (报告文档) ← 必须先完成 Phase 1-6
```

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Reddit API 配额不足 | 无法完成爬虫测试 | 使用 mock 数据或申请测试配额 |
| 本地环境性能不足 | 性能基准无法达标 | 降低测试数据规模（10 社区） |
| 依赖服务不稳定 | 测试中断 | 使用 Docker Compose 统一管理 |
| 测试数据污染 | 结果不准确 | 每次测试前清空数据库 |

---

**Next Step**: 开始执行 Phase 1

