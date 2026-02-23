# Phase 2 开发环境启动指南（纯真实环境）

> 本指南提供 Phase 2 "主线集成三层大脑+语义库" 开发所需的**纯真实环境配置（零 Mock）**。

---

## 🎯 Phase 2 核心目标

1. **修复 report_service.py**：启用 REPORT_QUALITY_LEVEL 路由（basic/standard/premium）
2. **重构 AnalysisEngine**：改用 content_labels 批量查询（替代关键词匹配）
3. **集成 LLM**：premium 模式接入真实 OpenAI API（含降级）
4. **端到端测试**：验证报告结构对齐 `reports/t1价值的报告.md`

---

## ⚡ 一键启动（推荐）

**最快方式**：使用自动化脚本一键配置纯真实环境

```bash
# 执行自动化启动脚本
bash .specify/specs/016-unified-semantic-report-loop/phase2-real-env-setup.sh
```

**脚本会自动完成**（100% 真实，零 Mock）：
- ✅ 检查依赖（PostgreSQL、Redis、Python）
- ✅ 创建 `backend/.env`（纯真实配置）
- ✅ 启动 PostgreSQL + Redis
- ✅ 运行数据库迁移
- ✅ 创建测试用户（真实数据库存储）
- ✅ 生成 Bearer Token（真实 JWT）
- ✅ 启动后端服务
- ✅ 运行健康检查

执行完成后，跳到 [环境验收](#-环境验收) 章节。

---

## 🔧 手动配置（详细步骤）

如果您想了解每一步的细节，或自动化脚本失败，可以手动配置。

### 1. 环境依赖检查

```bash
# 检查 PostgreSQL
psql --version
# 预期输出：psql (PostgreSQL) 14.x

# 检查 Redis
redis-cli --version
# 预期输出：redis-cli 7.x

# 检查 Python
python --version
# 预期输出：Python 3.11.x
```

**如果缺少依赖**：

```bash
# macOS
brew install postgresql@14 redis python@3.11

# Ubuntu/Debian
sudo apt install postgresql redis-server python3.11
```

---

### 2. 配置环境变量（纯真实配置）

```bash
# 创建 backend/.env 文件
cat > backend/.env << 'EOF'
# ============================================
# Phase 2 纯真实环境配置（零 Mock）
# ============================================

# 数据库（真实 PostgreSQL）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner

# Redis（真实 Redis）
REDIS_URL=redis://localhost:6379/5
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
TASK_STATUS_REDIS_URL=redis://localhost:6379/3

# JWT（真实 JWT，开发环境密钥）
JWT_SECRET=phase2-dev-secret-20251124
JWT_ALGORITHM=HS256

# 开发环境
APP_ENV=development
DEFAULT_MEMBERSHIP_LEVEL=pro

# 报告质量等级
# Phase 2.1-2.3: standard（语义库+模板，不需要LLM）
# Phase 2.4: premium（语义库+LLM，需要真实 OpenAI API）
REPORT_QUALITY_LEVEL=standard

# Celery（推荐 inline 执行，方便调试）
ENABLE_CELERY_DISPATCH=0

# Admin 权限
ADMIN_EMAILS=dev@example.com

# CORS
CORS_ALLOW_ORIGINS=http://localhost:3006,http://localhost:3000

# Reddit API（可选，Phase 2 暂不需要）
# REDDIT_CLIENT_ID=
# REDDIT_CLIENT_SECRET=

# OpenAI API（Phase 2.4 时填写，现在留空）
# OPENAI_API_KEY=

# 报告缓存
REPORT_CACHE_TTL_SECONDS=3600
REPORT_RATE_LIMIT_PER_MINUTE=30

EOF

echo "✅ backend/.env 已创建（纯真实配置）"
```

---

### 3. 启动基础设施（真实服务）

```bash
# 3.1 启动 PostgreSQL
# macOS
brew services start postgresql@14

# Linux
sudo systemctl start postgresql

# 验证
psql -l  # 列出所有数据库

# 3.2 创建数据库（如果不存在）
createdb reddit_signal_scanner

# 3.3 启动 Redis
make redis-start
# 或手动启动：
# macOS: brew services start redis
# Linux: sudo systemctl start redis

# 验证
redis-cli ping  # 应返回 PONG
```

---

### 4. 运行数据库迁移（真实数据库）

```bash
# 进入后端目录
cd backend

# 运行 Alembic 迁移
alembic upgrade head

# 验证表已创建
psql $DATABASE_URL -c "\dt"
# 应看到：users, analysis_tasks, community_pool, content_labels, etc.

cd ..
```

---

### 5. 创建测试用户（真实数据库存储）

```bash
# 创建测试用户（密码：TestPass123）
python backend/scripts/create_test_users.py

# 输出示例：
# ✅ Created user frontend-test@example.com
# ✅ Created user frontend-dev@example.com
# ✅ Created user integration-test@example.com

# 验证用户已创建
psql $DATABASE_URL -c "SELECT id, email FROM users LIMIT 5;"
```

---

### 6. 生成 Bearer Token（真实 JWT）

```bash
# 生成 Token（有效期 30 天）
python - <<'PY'
import sys
sys.path.insert(0, "backend")
from app.core.security import create_access_token

# 使用 frontend-test@example.com 的 ID
user_id = "00000000-0000-0000-0000-000000000001"
token = create_access_token({"sub": user_id})

print("\n" + "="*60)
print("📋 Bearer Token（复制下面的命令）:")
print("="*60)
print(f"\nexport PHASE2_TOKEN=\"{token}\"\n")
print("或在 curl 中使用:")
print(f"Authorization: Bearer {token}\n")
print("="*60 + "\n")
PY

# 保存到环境变量（复制上面输出的 export 命令）
export PHASE2_TOKEN="<上面生成的 token>"

# 或保存到文件（方便后续使用）
echo "export PHASE2_TOKEN=\"<token>\"" > /tmp/phase2_token.sh
source /tmp/phase2_token.sh
```

---

### 7. 启动后端服务

#### 方式 A：前台启动（推荐开发时使用）

```bash
# 启动后端（可以看到实时日志）
make dev-backend

# 输出示例：
# ==> Starting backend development server on http://localhost:8006 ...
#     API Docs: http://localhost:8006/docs
#     ENABLE_CELERY_DISPATCH=0
# INFO:     Uvicorn running on http://0.0.0.0:8006
```

#### 方式 B：后台启动

```bash
# 后台启动（日志写入文件）
cd backend
nohup uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload \
  > /tmp/phase2_backend.log 2>&1 &

# 记录 PID
echo $! > /tmp/phase2_backend.pid

cd ..

# 查看日志
tail -f /tmp/phase2_backend.log

# 停止后端
kill $(cat /tmp/phase2_backend.pid)
```

---

## ✅ 环境验收

完成配置后，运行以下测试验证环境是否正常。

### 1. 基础健康检查

```bash
# 1.1 后端健康检查
curl http://localhost:8006/health
# 期望：{"status":"ok"}

# 1.2 API 文档可访问
open http://localhost:8006/docs
# 应看到 Swagger UI
```

### 2. 认证测试（真实 JWT）

```bash
# 加载 Token
source /tmp/phase2_token.sh

# 测试认证
curl -H "Authorization: Bearer $PHASE2_TOKEN" \
     http://localhost:8006/api/users/me

# 期望输出：
# {
#   "id": "00000000-0000-0000-0000-000000000001",
#   "email": "frontend-test@example.com",
#   "membership_level": "pro"
# }
```

### 3. 创建分析任务（standard 模式，不需要 LLM）

```bash
# 创建分析任务
TASK_RESPONSE=$(curl -s -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $PHASE2_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "跨境电商支付解决方案"
  }')

echo "$TASK_RESPONSE" | jq .

# 期望输出：
# {
#   "task_id": "xxx-xxx-xxx",
#   "status": "pending",
#   "sse_endpoint": "/api/analyze/stream/xxx-xxx-xxx"
# }

# 提取 task_id
TASK_ID=$(echo "$TASK_RESPONSE" | jq -r .task_id)
echo "Task ID: $TASK_ID"
```

### 4. 等待任务完成并获取报告

```bash
# 等待 30-60 秒（inline 模式会同步执行）
# 查看后端日志观察进度：
# tail -f /tmp/phase2_backend.log

# 轮询任务状态
for i in {1..30}; do
  STATUS=$(curl -s http://localhost:8006/api/tasks/$TASK_ID/status \
    -H "Authorization: Bearer $PHASE2_TOKEN" | jq -r .status)
  echo "[$i] Task status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    echo "✅ 任务完成"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "❌ 任务失败"
    exit 1
  fi

  sleep 2
done

# 获取报告
curl http://localhost:8006/api/report/$TASK_ID \
  -H "Authorization: Bearer $PHASE2_TOKEN" \
  | jq . > /tmp/phase2_report.json

# 检查报告结构
jq 'keys' /tmp/phase2_report.json

# 期望包含：
# [
#   "task_id",
#   "report_html",
#   "insights",
#   "overview",
#   "stats",
#   "metadata"
# ]
```

### 5. 验收通过标志

```bash
# 运行完整验收脚本
cat > /tmp/phase2_acceptance.sh << 'EOF'
#!/bin/bash
echo "🧪 Phase 2 环境验收测试"
echo ""

# 1. 健康检查
echo "1️⃣ 健康检查..."
if curl -s http://localhost:8006/health | grep -q "ok"; then
  echo "   ✅ 后端健康"
else
  echo "   ❌ 后端不健康"
  exit 1
fi

# 2. 认证检查
echo "2️⃣ 认证检查..."
source /tmp/phase2_token.sh
if curl -s -H "Authorization: Bearer $PHASE2_TOKEN" \
   http://localhost:8006/api/users/me | grep -q "email"; then
  echo "   ✅ 认证通过"
else
  echo "   ❌ 认证失败"
  exit 1
fi

# 3. 数据库连接
echo "3️⃣ 数据库检查..."
if psql $DATABASE_URL -c "SELECT 1" > /dev/null 2>&1; then
  echo "   ✅ 数据库连接正常"
else
  echo "   ❌ 数据库连接失败"
  exit 1
fi

# 4. Redis 连接
echo "4️⃣ Redis 检查..."
if redis-cli ping > /dev/null 2>&1; then
  echo "   ✅ Redis 连接正常"
else
  echo "   ❌ Redis 连接失败"
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Phase 2 环境验收通过（纯真实环境）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
EOF

chmod +x /tmp/phase2_acceptance.sh
/tmp/phase2_acceptance.sh
```

---

## 📋 Phase 2 开发配置说明

### Phase 2.1-2.3（推荐先做，5天）

**配置**：
```bash
# backend/.env
REPORT_QUALITY_LEVEL=standard
```

**特点**：
- ✅ 使用语义库 + 模板生成报告
- ✅ **不需要 LLM**，不需要 OpenAI API
- ✅ 100% 真实环境，零 Mock
- ✅ 无 API 成本

**验收标准**：
1. report_service.py 支持 3 种模式路由（basic/standard/premium）
2. AnalysisEngine 改用 content_labels 批量查询
3. PainCluster 基于 DB 聚合（按 aspect）
4. 报告结构完整，包含痛点/竞品/机会

**开发重点**：
- 修改 `backend/app/services/report_service.py`
- 修改 `backend/app/services/analysis_engine.py`
- 修改 `backend/app/services/analysis/pain_cluster.py`

---

### Phase 2.4（后做，2天）

**配置**：
```bash
# backend/.env
REPORT_QUALITY_LEVEL=premium
OPENAI_API_KEY=sk-proj-...   # 需要您的真实 API Key
```

**特点**：
- ✅ 使用语义库 + 真实 LLM 生成报告
- ✅ 100% 真实环境，零 Mock
- ⚠️ 需要真实 OpenAI API Key
- 💰 成本约 $0.15-0.50 / 次测试（使用 gpt-4o-mini）

**验收标准**：
1. premium 模式调用真实 OpenAI API
2. 3 个 Prompt 模板可用（战场画像/用户之声/机会卡）
3. LLM 失败时降级到 standard 模式
4. 生成内容质量人工 review

**开发重点**：
- 修改 `backend/app/services/report/t1_market_agent.py`
- 实现 3 个 LLM 调用方法
- 实现降级逻辑

**OpenAI API 申请**：
1. 访问 https://platform.openai.com/
2. 创建 API Key
3. 充值 $5-10（够测试用）
4. 推荐模型：`gpt-4o-mini`（便宜且效果好）

---

## 🧪 Phase 2 验收清单

### 2.1 修复 report_service.py（2天）

```bash
# 验收命令
cd backend

# 1. 检查配置统一
grep "REPORT_QUALITY_LEVEL" app/services/report_service.py

# 2. 测试 basic 模式
curl -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $PHASE2_TOKEN" \
  -d '{"product_description":"跨境支付","quality_level":"basic"}' | jq .

# 3. 测试 standard 模式
curl -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $PHASE2_TOKEN" \
  -d '{"product_description":"跨境支付","quality_level":"standard"}' | jq .

# 4. 测试空指针安全
# （在代码中故意传入 None，验证不崩溃）

# 5. 测试异常降级
# （断开网络或 mock 超时，验证降级逻辑）
```

---

### 2.2 重构 AnalysisEngine（2天）

```bash
# 验收命令
cd backend

# 1. 确认不再有硬编码关键词
! grep -r "hate.*frustrated.*issue" app/services/analysis/

# 2. 确认使用 content_labels
grep "ContentLabel.*in_(post_ids)" app/services/analysis_engine.py

# 3. 确认批量查询（避免 N+1）
grep "select.*ContentLabel.*in_" app/services/analysis_engine.py

# 4. 单元测试通过
pytest tests/services/test_analysis_engine.py -v -s

# 5. 集成测试（真实数据库）
pytest tests/services/test_analysis_engine.py::test_analysis_engine_real_db -v
```

---

### 2.3 PainCluster 改造（1天）

```bash
# 验收命令
cd backend

# 1. 确认基于 DB 聚合
grep "group_by.*aspect" app/services/analysis/pain_cluster.py

# 2. 确认采样逻辑
grep "sample_top_comments.*limit" app/services/analysis/pain_cluster.py

# 3. 输出结构兼容
pytest tests/services/test_pain_cluster.py -v

# 4. 真实数据测试
python - <<'PY'
import asyncio, sys
sys.path.insert(0, ".")
from app.db.session import SessionFactory
from app.services.analysis.pain_cluster import cluster_pain_points

async def test():
    async with SessionFactory() as db:
        clusters = await cluster_pain_points(
            db,
            subreddit_keys=["ecommerce", "shopify"],
            lookback_days=90
        )
        print(f"Found {len(clusters)} pain clusters")
        for c in clusters[:3]:
            print(f"  - {c.topic}: {c.size} mentions")

asyncio.run(test())
PY
```

---

### 2.4 LLM 集成（1.5天）

```bash
# 验收命令（需要真实 OpenAI API Key）
cd backend

# 1. 检查 Prompt 模板
grep -A 10 "BATTLEFIELD_PROMPT\|USER_VOICE_PROMPT\|OPPORTUNITY_CARD_PROMPT" \
  app/services/report/t1_market_agent.py

# 2. 测试真实 LLM 调用
export OPENAI_API_KEY="sk-proj-..."
export REPORT_QUALITY_LEVEL="premium"

curl -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $PHASE2_TOKEN" \
  -d '{"product_description":"跨境支付","quality_level":"premium"}' | jq .

# 3. 测试降级逻辑（模拟 API 失败）
# 在代码中临时注释掉 API 调用，验证降级到模板

# 4. 单元测试
pytest tests/services/report/test_t1_market_agent.py -v

# 5. 人工 review（生成 5 份报告，检查质量）
for i in {1..5}; do
  TASK_ID=$(curl -s -X POST http://localhost:8006/api/analyze \
    -H "Authorization: Bearer $PHASE2_TOKEN" \
    -d '{"product_description":"跨境支付 '$i'"}' | jq -r .task_id)

  sleep 60  # 等待完成

  curl http://localhost:8006/api/report/$TASK_ID \
    -H "Authorization: Bearer $PHASE2_TOKEN" \
    | jq .report_html > reports/phase2-review-$i.html
done

# 人工检查 reports/phase2-review-*.html
```

---

### 2.5 端到端测试（0.5天）

```bash
# 运行 E2E 测试
cd backend
pytest tests/e2e/test_unified_pipeline.py -v -s

# 测试覆盖：
# 1. POST /api/analyze → GET /api/report 全流程
# 2. 报告包含 4 张决策卡片
# 3. 报告包含核心章节（战场/痛点/机会）
# 4. 置信度 >= 0.7
# 5. 降级标记正确

# 手动验收（对比目标报告）
diff -u \
  reports/t1价值的报告.md \
  reports/phase2-generated-report.md
```

---

## 🔧 常见问题排查

### Q1: Backend 启动失败

```bash
# 检查数据库连接
psql $DATABASE_URL -c "SELECT 1"

# 检查 Redis 连接
redis-cli ping

# 查看详细错误
tail -f /tmp/phase2_backend.log

# 检查端口占用
lsof -i :8006
```

### Q2: JWT Token 无效

```bash
# Token 可能过期，重新生成
python - <<'PY'
import sys
sys.path.insert(0, "backend")
from app.core.security import create_access_token
token = create_access_token({"sub": "00000000-0000-0000-0000-000000000001"})
print(f"export PHASE2_TOKEN=\"{token}\"")
PY

# 更新环境变量
source /tmp/phase2_token.sh
```

### Q3: 分析任务卡住

```bash
# 检查后端日志
tail -f /tmp/phase2_backend.log

# 检查任务状态
curl http://localhost:8006/api/tasks/$TASK_ID/status \
  -H "Authorization: Bearer $PHASE2_TOKEN"

# 如果使用 Celery，检查 Worker
tail -f /tmp/celery_worker.log

# 改用 inline 模式调试
# backend/.env: ENABLE_CELERY_DISPATCH=0
```

### Q4: OpenAI API 超时（Phase 2.4）

```bash
# 检查网络
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 检查余额
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 增加超时时间
# backend/app/services/report/t1_market_agent.py:
# response = await openai_client.chat.completions.create(
#     ...,
#     timeout=60.0  # 从 30s 增加到 60s
# )
```

### Q5: content_labels 表为空

```bash
# 检查是否有标注数据
psql $DATABASE_URL -c "SELECT COUNT(*) FROM content_labels;"

# 如果为空，运行标注任务
cd backend
python scripts/label_recent_posts.py --days 7 --limit 1000

# 或者使用 Make 命令
make label-posts-recent DAYS=7 LIMIT=1000
```

---

## 🛑 停止服务

```bash
# 停止后端
kill $(cat /tmp/phase2_backend.pid)

# 停止 Redis
brew services stop redis

# 停止 PostgreSQL
brew services stop postgresql@14
```

---

## 📚 相关文档

- [Phase 2 执行计划](./plan.md#phase-2-主线集成三层大脑语义库7天)
- [Phase 2 任务清单](./tasks.md#phase-2-主线集成7天)
- [主业务线说明书](../../../docs/archive/2025-11-主业务线说明书.md)
- [报告质量等级设计](./design.md#报告质量等级)

---

## ✅ Phase 2 环境就绪检查清单

完成以下检查后，即可开始 Phase 2 开发：

- [ ] PostgreSQL 运行并可连接
- [ ] Redis 运行并可连接
- [ ] 数据库迁移完成（`alembic upgrade head`）
- [ ] 测试用户已创建（`frontend-test@example.com`）
- [ ] Bearer Token 已生成并保存
- [ ] Backend 启动成功（http://localhost:8006/health 返回 ok）
- [ ] 认证测试通过（/api/users/me 返回用户信息）
- [ ] 可创建分析任务（POST /api/analyze 返回 task_id）
- [ ] 可获取报告（GET /api/report/{task_id} 返回 ReportPayload）

**Phase 2.4 额外检查**（到时候再做）：
- [ ] OpenAI API Key 已配置
- [ ] API 余额充足（至少 $5）
- [ ] REPORT_QUALITY_LEVEL 改为 premium
- [ ] 可调用真实 LLM（测试生成战场画像）

---

## 🚀 推荐开发顺序

1. **Phase 2.1-2.3**（5天，推荐先做）
   - ✅ 使用 `REPORT_QUALITY_LEVEL=standard`
   - ✅ 不需要 LLM，不需要 OpenAI API
   - ✅ 专注主线逻辑、AnalysisEngine、PainCluster
   - ✅ 成本：免费

2. **Phase 2.4**（2天，后做）
   - ✅ 切换到 `REPORT_QUALITY_LEVEL=premium`
   - ✅ 配置真实 OpenAI API Key
   - ✅ 实现 3 个 LLM Prompt 模板
   - ✅ 实现降级逻辑
   - 💰 成本：约 $5-10（测试期间）

---

**现在可以开始 Phase 2 开发了！** 🎉

推荐使用 [一键启动脚本](#-一键启动推荐) 快速配置环境。
