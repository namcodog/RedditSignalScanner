# Phase 2 快速启动指南（保护现有配置）

> **安全第一**：本指南不会覆盖您现有的 `backend/.env` 配置（如 Reddit API keys）

---

## 🚀 30秒快速启动

### 步骤 1：检查现有配置

```bash
# 检查 Phase 2 所需配置是否齐全
bash .specify/specs/016-unified-semantic-report-loop/phase2-env-check.sh
```

**如果检查通过**，直接跳到 [步骤 3](#步骤-3启动后端)

**如果提示缺少配置**，继续步骤 2

---

### 步骤 2：智能合并配置（保留现有配置）

```bash
# 自动添加缺失的 Phase 2 配置（不覆盖现有配置）
bash .specify/specs/016-unified-semantic-report-loop/merge-env.sh
```

**这个脚本会**：
- ✅ 备份现有 `.env` 文件（带时间戳）
- ✅ 只添加缺失的配置项
- ✅ **不会覆盖**任何现有配置（如 Reddit API keys）
- ✅ 显示合并结果

---

### 步骤 3：启动后端

```bash
# 启动 Redis（如果未运行）
make redis-start

# 启动后端（inline 模式，方便调试）
make dev-backend
```

---

### 步骤 4：创建测试用户并获取 Token

```bash
# 创建测试用户
python backend/scripts/create_test_users.py

# 生成 Bearer Token
python - <<'PY'
import sys
sys.path.insert(0, "backend")
from app.core.security import create_access_token
token = create_access_token({"sub": "00000000-0000-0000-0000-000000000001"})
print(f"\nexport PHASE2_TOKEN=\"{token}\"\n")
PY

# 保存 Token（复制上面输出的命令）
export PHASE2_TOKEN="<上面的 token>"
```

---

### 步骤 5：验证环境

```bash
# 健康检查
curl http://localhost:8006/health

# 认证测试
curl -H "Authorization: Bearer $PHASE2_TOKEN" \
     http://localhost:8006/api/users/me

# 创建测试任务
curl -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $PHASE2_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_description": "跨境电商支付解决方案"}'
```

✅ **如果以上都成功，Phase 2 环境已就绪！**

---

## 🛡️ 配置安全说明

### 您的配置会被保护

以下脚本**不会覆盖**您现有的配置：

1. **`phase2-env-check.sh`** - 只检查，不修改
2. **`merge-env.sh`** - 只添加缺失项，不覆盖现有配置

### 手动添加配置（最安全）

如果您不信任自动化脚本，可以手动添加以下配置到 `backend/.env`：

```bash
# Phase 2 必需配置（如果缺失，请手动添加）
REPORT_QUALITY_LEVEL=standard
ENABLE_CELERY_DISPATCH=0
DEFAULT_MEMBERSHIP_LEVEL=pro
```

---

## 📋 Phase 2 关键配置说明

### 必需配置（Phase 2.1-2.3）

| 配置项 | 值 | 说明 |
|--------|---|------|
| `REPORT_QUALITY_LEVEL` | `standard` | 使用语义库+模板（不需要 LLM） |
| `ENABLE_CELERY_DISPATCH` | `0` | inline 执行（方便调试） |
| `DEFAULT_MEMBERSHIP_LEVEL` | `pro` | 跳过会员限制 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | 真实数据库连接 |
| `REDIS_URL` | `redis://localhost:6379/5` | 真实 Redis 连接 |
| `JWT_SECRET` | `phase2-dev-secret` | JWT 密钥 |

### 可选配置（Phase 2.4）

| 配置项 | 值 | 说明 |
|--------|---|------|
| `OPENAI_API_KEY` | `sk-proj-...` | Phase 2.4 premium 模式需要 |

---

## 🔧 配置工具脚本

### 1. 配置检查（推荐首先运行）

```bash
bash .specify/specs/016-unified-semantic-report-loop/phase2-env-check.sh
```

**作用**：
- 检查所有必需配置是否存在
- **不会修改**任何文件
- 提示缺失的配置

---

### 2. 智能合并（安全添加缺失配置）

```bash
bash .specify/specs/016-unified-semantic-report-loop/merge-env.sh
```

**作用**：
- 备份现有 `.env`（带时间戳）
- 只添加缺失的 Phase 2 配置
- **保留**所有现有配置（Reddit keys、OpenAI keys 等）
- 显示合并结果

**示例输出**：
```
✅ 已备份到：backend/.env.backup_20251124-153045
✅ 已添加：REPORT_QUALITY_LEVEL=standard
⏭️  跳过（已存在）：REDDIT_CLIENT_ID
⏭️  跳过（已存在）：DATABASE_URL
```

---

## 📚 完整文档

- 详细启动指南：[phase2-startup-guide.md](./phase2-startup-guide.md)
- 执行计划：[plan.md](./plan.md)
- 任务清单：[tasks.md](./tasks.md)

---

## ❓ 常见问题

### Q1: 我的 Reddit API keys 会被覆盖吗？

**不会**。`merge-env.sh` 只添加缺失的配置，不会覆盖现有配置。

### Q2: 如何恢复配置？

```bash
# 查看备份文件
ls -lt backend/.env.backup_*

# 恢复最新备份
cp backend/.env.backup_<timestamp> backend/.env
```

### Q3: 如何查看当前配置？

```bash
# 查看所有配置
cat backend/.env

# 只查看 Phase 2 相关配置
grep -E "REPORT_QUALITY_LEVEL|ENABLE_CELERY_DISPATCH|DEFAULT_MEMBERSHIP_LEVEL" backend/.env
```

### Q4: 完全手动配置怎么做？

编辑 `backend/.env`，确保包含以下配置：

```bash
# Phase 2 必需
REPORT_QUALITY_LEVEL=standard
ENABLE_CELERY_DISPATCH=0
DEFAULT_MEMBERSHIP_LEVEL=pro

# 基础设施（如果缺失）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner
REDIS_URL=redis://localhost:6379/5
JWT_SECRET=phase2-dev-secret
```

---

**现在可以安全地启动 Phase 2 开发了！** 🚀
