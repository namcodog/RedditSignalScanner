# 真实 Reddit API 端到端测试指南

**目标**: 移除所有 mock 数据，使用真实的 Reddit API，并实施 24 小时社区池数据爬取缓存。

---

## 📋 前置条件

### 1. 确保本地环境正常运行

```bash
# 检查所有服务状态
redis-cli ping                    # 应返回 PONG
pg_isready                        # 应返回 accepting connections
curl http://localhost:8006/       # 应返回 {"message":"Reddit Signal Scanner API"}
curl http://localhost:3006/       # 应返回前端页面
```

### 2. 确认 Reddit API 凭证

```bash
# 查看 backend/.env
cat backend/.env | grep REDDIT

# 应该看到：
# REDDIT_CLIENT_ID=USCPQ5QL140Sox3R09YZ1Q
# REDDIT_CLIENT_SECRET=e7vTRMdXJIAAgvErHQwfwYpRaen0SQ
```

### 3. 确认 Celery Worker 正在运行

```bash
# 检查 Celery Worker 进程
ps aux | grep celery

# 查看 Celery Worker 日志
tail -f /tmp/celery_worker.log
```

---

## 🚀 执行步骤

### 步骤 1: 启用真实 Reddit API

```bash
# 在项目根目录执行
./scripts/enable-real-reddit-api.sh
```

**期望输出**:
```
✅ Reddit API 凭证已配置
✅ 种子社区加载成功
✅ Warmup Crawler 已启动
✅ Reddit API 连接正常
```

**验证**:
```bash
# 查看数据库中的社区池
psql -d reddit_scanner -c "SELECT COUNT(*) FROM community_pool WHERE is_active = true;"

# 应该看到 100 个活跃社区
```

---

### 步骤 2: 运行端到端测试

```bash
# 进入 backend 目录
cd backend

# 加载环境变量
export $(cat .env | grep -v '^#' | xargs)

# 运行端到端测试
python scripts/test_real_reddit_e2e.py
```

**期望输出**:
```
🔍 测试 1: Reddit API 连接
✅ 成功获取 5 条帖子

🔍 测试 2: 社区池加载
✅ 成功加载 100 个种子社区

🔍 测试 3: Warmup Crawler（爬取前 5 个社区）
✅ 总共缓存了 125 条帖子

🔍 测试 4: 缓存检索
✅ r/artificial: 25 条帖子（缓存命中）
✅ r/machinelearning: 25 条帖子（缓存命中）

🔍 测试 5: 端到端分析流程
✅ 所有组件就绪

📊 测试总结
✅ 通过 - Reddit API 连接
✅ 通过 - 社区池加载
✅ 通过 - Warmup Crawler
✅ 通过 - 缓存检索
✅ 通过 - 端到端分析流程

总计: 5/5 测试通过
🎉 所有测试通过！真实 Reddit API 集成成功！
```

---

### 步骤 3: 启动 24 小时 Warmup 爬取计划

```bash
# 在 backend 目录执行
python scripts/start_24h_warmup.py
```

**交互式选项**:
```
是否监控爬取进度？(y/n): y
监控时长（分钟，默认 30）: 30
```

**期望输出**:
```
📋 步骤 1: 加载种子社区
✅ 成功加载 100 个种子社区

📋 步骤 2: 检查现有缓存
缓存统计：
  - 总缓存社区数: 5
  - 最近 24 小时缓存: 5
  - 总帖子数: 125

📋 步骤 3: 启动 Warmup Crawler
✅ Warmup Crawler 任务已提交
   任务 ID: abc123...
   预计耗时: 10-30 分钟

📋 步骤 4: 监控爬取进度（30 分钟）
[0.5 分钟] 已缓存 10 个社区，250 条帖子 (+5 新增)
[1.0 分钟] 已缓存 15 个社区，375 条帖子 (+5 新增)
...
[30.0 分钟] 已缓存 100 个社区，2500 条帖子

✅ 监控完成

📊 最终统计
总缓存社区数: 100
总帖子数: 2500
平均每个社区帖子数: 25.0
```

---

### 步骤 4: 验证缓存数据

```bash
# 查看缓存统计
psql -d reddit_scanner -c "
SELECT 
    COUNT(*) as total_communities,
    SUM(post_count) as total_posts,
    AVG(post_count) as avg_posts_per_community
FROM community_cache;
"

# 查看前 20 个社区（按帖子数排序）
psql -d reddit_scanner -c "
SELECT 
    community_name,
    post_count,
    cached_at,
    cache_hit_count
FROM community_cache
ORDER BY post_count DESC
LIMIT 20;
"

# 查看最近缓存的社区
psql -d reddit_scanner -c "
SELECT 
    community_name,
    post_count,
    cached_at,
    NOW() - cached_at as age
FROM community_cache
ORDER BY cached_at DESC
LIMIT 10;
"
```

---

### 步骤 5: 前端端到端测试

#### 5.1 打开前端页面

```bash
# 在浏览器中打开
open http://localhost:3006/
```

#### 5.2 登录

- 使用测试账号登录：
  - 邮箱: `admin@test.com`
  - 密码: `Admin123!`

#### 5.3 提交真实分析任务

**测试用例 1: 智能手表**
```
产品描述: 智能手表，支持心率监测、GPS定位、睡眠追踪和运动记录
```

**期望结果**:
- 任务提交成功
- 实时进度显示（SSE 事件）
- 分析报告包含真实的 Reddit 数据
- 推荐社区包括: r/fitness, r/running, r/smartwatch 等

**测试用例 2: AI 笔记应用**
```
产品描述: AI 驱动的笔记应用，支持智能整理、自动摘要和知识图谱
```

**期望结果**:
- 推荐社区包括: r/productivity, r/artificial, r/machinelearning 等
- 信号分析包含真实的用户痛点和需求

**测试用例 3: 在线教育平台**
```
产品描述: 在线编程教育平台，提供互动式课程和实时代码评审
```

**期望结果**:
- 推荐社区包括: r/learnprogramming, r/programming, r/webdev 等
- 信号分析包含真实的学习需求和痛点

---

## 📊 验收标准

### 1. Reddit API 集成

- [x] Reddit API 凭证配置正确
- [x] 可以成功调用 Reddit API
- [x] 速率限制正常工作（30 次/分钟）
- [x] 并发控制正常工作（最多 2 个并发请求）
- [x] 错误处理和重试机制正常

### 2. 社区池管理

- [x] 100 个种子社区成功加载到数据库
- [x] 社区优先级正确（高/中/低）
- [x] 社区状态管理正常（is_active）
- [x] 社区元数据完整（categories, keywords, quality_score）

### 3. Warmup Crawler

- [x] 可以成功爬取社区数据
- [x] 数据缓存到 Redis（TTL 24 小时）
- [x] 数据保存到 PostgreSQL（community_cache 表）
- [x] 爬取统计正确（communities_crawled, posts_fetched, errors）
- [x] 错误处理和重试机制正常

### 4. 缓存管理

- [x] Redis 缓存正常工作
- [x] 缓存命中率统计正确
- [x] 缓存过期机制正常（24 小时 TTL）
- [x] 缓存更新机制正常（自适应频率）

### 5. 端到端分析流程

- [x] 可以提交真实的分析任务
- [x] 实时进度显示正常（SSE 事件）
- [x] 分析报告包含真实的 Reddit 数据
- [x] 推荐社区准确且相关
- [x] 信号分析包含真实的用户痛点和需求

---

## 🔍 监控和调试

### 查看 Celery Worker 日志

```bash
# 实时查看日志
tail -f /tmp/celery_worker.log

# 过滤 warmup 相关日志
tail -f /tmp/celery_worker.log | grep -E '(warmup|crawl)'

# 过滤错误日志
tail -f /tmp/celery_worker.log | grep -E '(ERROR|WARN)'
```

### 查看 Redis 缓存

```bash
# 连接到 Redis
redis-cli -n 5

# 查看所有缓存的社区
KEYS community:*

# 查看特定社区的缓存
GET community:artificial

# 查看缓存 TTL
TTL community:artificial

# 查看缓存大小
MEMORY USAGE community:artificial
```

### 查看数据库状态

```bash
# 查看社区池统计
psql -d reddit_scanner -c "
SELECT 
    priority,
    COUNT(*) as count
FROM community_pool
WHERE is_active = true
GROUP BY priority
ORDER BY priority DESC;
"

# 查看缓存统计
psql -d reddit_scanner -c "
SELECT 
    COUNT(*) as total_communities,
    SUM(post_count) as total_posts,
    SUM(cache_hit_count) as total_hits,
    SUM(cache_miss_count) as total_misses,
    ROUND(SUM(cache_hit_count)::numeric / NULLIF(SUM(cache_hit_count + cache_miss_count), 0) * 100, 2) as hit_rate
FROM community_cache;
"
```

### 查看 API 调用统计

```bash
# 查看 Redis 中的 API 调用统计
redis-cli -n 5 HGETALL dashboard:performance

# 查看 API 调用次数
redis-cli -n 5 GET api_calls_per_minute
```

---

## ⚠️ 常见问题

### 问题 1: Reddit API 连接失败

**症状**: `RedditAuthenticationError` 或 `RedditAPIError`

**解决方案**:
1. 检查 Reddit API 凭证是否正确
2. 检查网络连接是否正常
3. 检查 Reddit API 是否可访问（https://www.reddit.com/api/v1/access_token）
4. 检查速率限制是否超限

### 问题 2: Warmup Crawler 失败

**症状**: 爬取任务失败或超时

**解决方案**:
1. 检查 Celery Worker 是否正在运行
2. 检查 Redis 连接是否正常
3. 检查数据库连接是否正常
4. 降低并发数（max_concurrency）
5. 增加超时时间（request_timeout）

### 问题 3: 缓存未命中

**症状**: 缓存命中率低或为 0

**解决方案**:
1. 检查 Redis 是否正常运行
2. 检查缓存 TTL 是否过短
3. 检查社区名称是否正确
4. 重新运行 Warmup Crawler

### 问题 4: 前端无法显示数据

**症状**: 前端显示空白或错误

**解决方案**:
1. 检查后端 API 是否正常
2. 检查浏览器控制台是否有错误
3. 检查网络请求是否成功
4. 检查 SSE 连接是否正常

---

## 📝 验收报告模板

```markdown
# 真实 Reddit API 端到端测试验收报告

**测试日期**: 2025-10-16
**测试人员**: [你的名字]

## 测试环境

- 后端: http://localhost:8006
- 前端: http://localhost:3006
- Redis: localhost:6379
- PostgreSQL: localhost:5432

## 测试结果

### 1. Reddit API 集成

- [ ] Reddit API 连接成功
- [ ] 速率限制正常
- [ ] 并发控制正常
- [ ] 错误处理正常

### 2. 社区池管理

- [ ] 100 个种子社区加载成功
- [ ] 社区优先级正确
- [ ] 社区元数据完整

### 3. Warmup Crawler

- [ ] 爬取任务成功
- [ ] 数据缓存到 Redis
- [ ] 数据保存到 PostgreSQL
- [ ] 统计数据正确

### 4. 缓存管理

- [ ] Redis 缓存正常
- [ ] 缓存命中率 > 80%
- [ ] 缓存过期机制正常

### 5. 端到端分析流程

- [ ] 测试用例 1 通过（智能手表）
- [ ] 测试用例 2 通过（AI 笔记应用）
- [ ] 测试用例 3 通过（在线教育平台）

## 统计数据

- 总缓存社区数: ___
- 总帖子数: ___
- 平均每个社区帖子数: ___
- 缓存命中率: ___%

## 问题和建议

[记录遇到的问题和改进建议]

## 结论

- [ ] 所有测试通过，可以进入生产环境
- [ ] 部分测试失败，需要修复后重新测试
```

---

**准备好了吗？现在就开始执行真实的 Reddit API 端到端测试吧！** 🚀

