# API 测试指南

> **Day 5 前端开发必读**
> 本指南说明如何测试后端 API 并获取认证 Token

---

## 🚀 快速开始

### 1. 确保后端服务运行

```bash
# 检查后端是否运行
curl http://localhost:8006/api/healthz

# 应该返回:
# {"status":"healthy"}
```

如果后端未运行，启动后端：

```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload
```

---

### 2. 获取测试 Token

#### 方法 1: 使用 Python 脚本（推荐）

```bash
python3 frontend/scripts/setup-test-user.py
```

这将：
1. 注册测试用户 `frontend-test@example.com`
2. 返回有效的 JWT Token
3. 显示使用方法

#### 方法 2: 手动注册

```bash
curl -X POST http://localhost:8006/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "YourPass123"
  }'
```

保存返回的 `access_token`。

---

### 3. 运行 API 集成测试

```bash
# 设置 Token 环境变量
export TEST_TOKEN='your-token-here'

# 运行测试脚本
./frontend/scripts/test-api.sh
```

---

## 📋 测试所有 API 端点

### 1. POST /api/analyze - 创建分析任务

```bash
curl -X POST http://localhost:8006/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -d '{
    "product_description": "AI笔记应用，帮助研究者和创作者自动组织和连接想法"
  }'
```

**期望响应**:
```json
{
  "task_id": "uuid",
  "status": "pending",
  "created_at": "2025-10-10T...",
  "estimated_completion": "2025-10-10T...",
  "sse_endpoint": "/api/analyze/stream/{task_id}"
}
```

---

### 2. GET /api/status/{task_id} - 查询任务状态

```bash
# 替换 {task_id} 为实际的任务 ID
curl http://localhost:8006/api/status/{task_id} \
  -H "Authorization: Bearer ${TEST_TOKEN}"
```

**期望响应**:
```json
{
  "task_id": "uuid",
  "status": "pending|processing|completed|failed",
  "progress": 0-100,
  "message": "状态消息",
  "error": null
}
```

---

### 3. GET /api/analyze/stream/{task_id} - SSE 实时推送

```bash
# 使用 -N 参数禁用缓冲
curl -N http://localhost:8006/api/analyze/stream/{task_id} \
  -H "Authorization: Bearer ${TEST_TOKEN}"
```

**期望响应** (Server-Sent Events):
```
data: {"event": "connected", "task_id": "..."}

data: {"event": "progress", "percentage": 25, "message": "..."}

data: {"event": "completed", "task_id": "..."}
```

---

### 4. GET /api/report/{task_id} - 获取分析报告

```bash
curl http://localhost:8006/api/report/{task_id} \
  -H "Authorization: Bearer ${TEST_TOKEN}"
```

**期望响应** (任务完成后):
```json
{
  "task_id": "uuid",
  "insights": {
    "pain_points": [...],
    "competitors": [...],
    "opportunities": [...]
  }
}
```

**期望响应** (任务未完成):
```json
{
  "detail": "Task has not completed yet"
}
```

---

## 🔐 认证相关

### 注册新用户

```bash
curl -X POST http://localhost:8006/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "new-user@example.com",
    "password": "SecurePass123"
  }'
```

### 登录已有用户

```bash
curl -X POST http://localhost:8006/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "existing-user@example.com",
    "password": "SecurePass123"
  }'
```

---

## 🧪 前端开发测试流程

### 步骤 1: 获取 Token

```bash
# 运行设置脚本
python3 frontend/scripts/setup-test-user.py

# 复制输出的 Token
export TEST_TOKEN='eyJhbGci...'
```

### 步骤 2: 在前端代码中使用

```typescript
// 保存 Token 到 localStorage
localStorage.setItem('auth_token', 'eyJhbGci...');

// API 客户端会自动添加到请求头
import { createAnalyzeTask } from '@/api';

const response = await createAnalyzeTask({
  product_description: 'Test product'
});
```

### 步骤 3: 测试 SSE 连接

```typescript
const eventSource = new EventSource(
  `http://localhost:8006/api/analyze/stream/${taskId}`
);

eventSource.onmessage = (event) => {
  console.log('SSE Event:', JSON.parse(event.data));
};
```

---

## 🛠️ 故障排查

### 问题 1: 401 Unauthorized

**原因**: Token 无效或过期

**解决**:
```bash
# 重新获取 Token
python3 frontend/scripts/setup-test-user.py
```

---

### 问题 2: 404 Not Found

**原因**: 后端服务未运行或端口错误

**解决**:
```bash
# 检查后端是否在 8008 端口运行
lsof -i :8008

# 如果没有，启动后端
cd backend && uvicorn app.main:app --port 8008 --reload
```

---

### 问题 3: CORS 错误

**原因**: 前端域名未在 CORS 白名单中

**解决**:
```bash
# 检查后端 CORS 配置
# backend/app/core/config.py
# cors_origins_raw: str = "http://localhost:3006,http://localhost:5173"
```

---

### 问题 4: SSE 连接失败

**原因**: 浏览器不支持或网络问题

**解决**:
```typescript
// 添加错误处理
eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  // 降级到轮询
  pollTaskStatus(taskId);
};
```

---

## 📝 测试清单

在开始前端开发前，确保以下测试通过：

- [ ] ✅ 后端服务在 8008 端口运行
- [ ] ✅ 可以注册新用户
- [ ] ✅ 可以获取有效 Token
- [ ] ✅ POST /api/analyze 返回 task_id
- [ ] ✅ GET /api/status/{task_id} 返回状态
- [ ] ✅ SSE 连接可以建立
- [ ] ✅ GET /api/report/{task_id} 正确处理未完成任务

---

## 🎯 下一步

API 测试通过后，可以开始：

1. **输入页面开发** - 调用 POST /api/analyze
2. **等待页面开发** - 使用 SSE 实时更新进度
3. **报告页面开发** - 展示 GET /api/report 返回的数据

---

**最后更新**: 2025-10-10 Day 5
**维护者**: Frontend Agent

