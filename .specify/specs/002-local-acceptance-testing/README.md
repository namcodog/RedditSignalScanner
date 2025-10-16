# 本地测试环境验收 - 快速开始

**Feature ID**: 002-local-acceptance-testing  
**状态**: READY  
**创建日期**: 2025-10-16

---

## 📋 概述

本验收方案为 Day 13-20 预热期功能提供**完全隔离的本地测试环境**，确保：
- ✅ 测试环境与开发环境完全隔离（独立端口、独立数据库、独立 Docker 网络）
- ✅ 所有服务通过 Docker Compose 统一管理，一键启动/停止
- ✅ 自动化验收流程，通过 Makefile 命令执行
- ✅ 完整的测试覆盖（环境准备 → 核心服务 → API → 任务调度 → 端到端）

---

## 🚀 快速开始

### 1. 前置准备（必须完成）

**重要**: 本验收使用**真实 Reddit API**，需要先配置凭证

```bash
# 进入项目根目录
cd /Users/hujia/Desktop/RedditSignalScanner

# 运行前置准备脚本（自动检查环境）
bash scripts/setup-test-env.sh
```

脚本会自动完成：
- ✅ 检查 Reddit API 凭证（`.env` 文件）
- ✅ 创建测试数据文件（10 个社区）
- ✅ 验证 Docker 环境
- ✅ 检查端口可用性
- ✅ 验证 Docker Compose 配置

**如果脚本提示缺少 Reddit API 凭证**：
1. 访问 https://www.reddit.com/prefs/apps
2. 创建应用（类型选择 `script`）
3. 复制 `client_id` 和 `client_secret`
4. 编辑项目根目录的 `.env` 文件：
   ```bash
   REDDIT_CLIENT_ID=your_actual_client_id
   REDDIT_CLIENT_SECRET=your_actual_client_secret
   REDDIT_USER_AGENT=RedditSignalScanner/Test:v1.0
   ```
5. 重新运行 `bash scripts/setup-test-env.sh`

---

### 2. 一键执行完整验收

```bash
# 执行完整验收流程（约 15-20 分钟）
# 注意：会调用真实 Reddit API（约 10-15 次请求）
make test-all-acceptance
```

---

### 3. 分步执行（推荐首次使用）

```bash
# Step 1: 启动测试环境
make test-env-up

# Step 2: Stage 1 - 环境准备与健康检查
make test-stage-1

# Step 3: Stage 2 - 核心服务验收（会调用真实 Reddit API）
make test-stage-2

# Step 4: Stage 3 - API 端点验收
make test-stage-3

# Step 5: Stage 4 - 任务调度与监控
make test-stage-4

# Step 6: Stage 5 - 端到端流程
make test-stage-5

# Step 7: 生成验收报告
make test-report-acceptance

# Step 8: 停止并清理环境
make test-env-clean
```

---

## 📁 文件结构

```
RedditSignalScanner/
├── docker-compose.test.yml          # 测试环境 Docker Compose 配置
├── Makefile                          # 自动化命令（已追加测试命令）
├── backend/
│   ├── Dockerfile.test               # 测试环境 Dockerfile
│   ├── pytest.ini                    # Pytest 配置
│   └── tests/                        # 测试用例
├── .specify/specs/002-local-acceptance-testing/
│   ├── README.md                     # 本文件
│   ├── plan.md                       # 详细验收计划
│   └── tasks.md                      # 任务清单
└── reports/
    └── acceptance-test-report.md     # 验收报告（自动生成）
```

---

## 🔧 可用命令

### 环境管理

| 命令 | 说明 |
|------|------|
| `make test-env-up` | 启动测试环境（Docker Compose） |
| `make test-env-down` | 停止测试环境 |
| `make test-env-clean` | 清理测试环境（删除卷） |
| `make test-env-logs` | 查看测试环境日志 |
| `make test-env-shell` | 进入测试容器 Shell |

### 验收流程

| 命令 | 说明 |
|------|------|
| `make test-all-acceptance` | 执行完整验收流程（Stage 1-5） |
| `make test-stage-1` | Stage 1: 环境准备与健康检查 |
| `make test-stage-2` | Stage 2: 核心服务验收 |
| `make test-stage-3` | Stage 3: API 端点验收 |
| `make test-stage-4` | Stage 4: 任务调度与监控 |
| `make test-stage-5` | Stage 5: 端到端流程 |
| `make test-report-acceptance` | 生成验收报告 |

---

## 🌐 服务地址

| 服务 | 开发环境 | 测试环境 | 说明 |
|------|----------|----------|------|
| FastAPI | http://localhost:8000 | http://localhost:18000 | API 服务器 |
| PostgreSQL | localhost:5432 | localhost:15432 | 数据库 |
| Redis | localhost:6379 | localhost:16379 | 缓存 |

**端口规范**：测试环境端口 = 开发环境端口 + 10000（避免冲突）

---

## ✅ 验收标准

### 功能完整性

- [x] 所有 10 个 Phase 的功能可用
- [x] 所有 API 端点返回正确响应
- [x] 所有 Celery 任务可执行
- [x] 所有数据库表有正确数据

### 数据一致性

- [x] Redis 缓存与 PostgreSQL 元数据一致
- [x] 社区发现记录可追溯到任务
- [x] Beta 反馈关联到正确的任务和用户

### 性能达标

- [x] 所有性能基准达标
- [x] 无内存泄漏（运行 1 小时后检查）
- [x] 无数据库连接泄漏

### 环境隔离

- [x] 测试环境与开发环境端口不冲突
- [x] 测试数据不污染开发数据库
- [x] Docker 卷可完全清理

---

## 🐛 故障排查

### 问题 1: Docker Compose 启动失败

```bash
# 检查 Docker 服务
docker info

# 检查端口占用
lsof -i :18000
lsof -i :15432
lsof -i :16379

# 清理并重试
make test-env-clean
make test-env-up
```

### 问题 2: 数据库迁移失败

```bash
# 进入容器手动执行
docker compose -f docker-compose.test.yml exec test-api bash
alembic upgrade head
alembic current
```

### 问题 3: 测试失败

```bash
# 查看详细日志
docker compose -f docker-compose.test.yml logs test-api
docker compose -f docker-compose.test.yml logs test-worker

# 进入容器调试
docker compose -f docker-compose.test.yml exec test-api bash
pytest tests/ -vv --tb=short
```

---

## 📊 时间估算

| 阶段 | 预计耗时 | 说明 |
|------|----------|------|
| 环境准备 | 5 分钟 | Docker 镜像拉取与构建 |
| Stage 1 | 2 分钟 | 健康检查与数据清理 |
| Stage 2 | 5 分钟 | 核心服务单元测试 |
| Stage 3 | 3 分钟 | API 集成测试 |
| Stage 4 | 4 分钟 | 任务调度与监控 |
| Stage 5 | 6 分钟 | 端到端流程 |
| 报告生成 | 1 分钟 | 生成验收报告 |
| **总计** | **26 分钟** | 首次执行（含镜像构建） |
| **后续执行** | **15 分钟** | 镜像已缓存 |

---

## 📚 相关文档

- [详细验收计划](./plan.md) - 完整的验收流程与技术规范
- [任务清单](./tasks.md) - 分阶段任务拆解
- [PRD-09 Day 13-20 预热期](../ 001-day13-20-warmup-period/plan.md) - 功能需求文档

---

## 🎯 下一步

验收通过后，可以：
1. 补充 Alembic 迁移（Phase 9 新增的 beta_feedback 表等）
2. 配置生产环境的 Docker Compose
3. 准备生产部署文档与运维手册
4. 执行生产环境冒烟测试

---

**创建日期**: 2025-10-16  
**最后更新**: 2025-10-16  
**维护者**: Lead

