# 端口配置说明

> **项目**: Reddit Signal Scanner
> **更新日期**: 2025-10-10 Day 5

---

## 📌 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| **前端开发服务器** | `3006` | Vite Dev Server |
| **后端 API 服务器** | `8006` | FastAPI + Uvicorn |
| **PostgreSQL 数据库** | `5432` | 默认端口 |
| **Redis** | `6379` | 默认端口 |

---

## 🔧 配置文件

### 前端配置

#### 1. `frontend/.env.development`
```bash
VITE_API_BASE_URL=http://localhost:8006
```

#### 2. `frontend/vite.config.ts`
```typescript
export default defineConfig({
  server: {
    port: 3006,
    proxy: {
      '/api': {
        target: 'http://localhost:8006',
        changeOrigin: true,
      },
    },
  },
});
```

#### 3. `frontend/package.json`
```json
{
  "scripts": {
    "dev": "vite --port 3006",
    "preview": "vite preview --port 3006"
  }
}
```

---

### 后端配置

#### 启动命令
```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload
```

#### 环境变量（如需配置）
```bash
# backend/.env
PORT=8006
```

---

## 🚀 启动服务

### 1. 启动后端
```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload
```

**验证后端运行**:
```bash
curl http://localhost:8006/api/healthz
# 应返回: {"status":"ok"}
```

---

### 2. 启动前端
```bash
cd frontend
npm run dev
```

**访问前端**:
- 开发服务器: http://localhost:3006
- API 代理: http://localhost:3006/api/*

---

## 🔍 端口冲突排查

### 检查端口占用

```bash
# 检查 3006 端口
lsof -i :3006

# 检查 8006 端口
lsof -i :8006
```

### 释放端口

```bash
# 杀死占用 3006 端口的进程
lsof -ti :3006 | xargs kill -9

# 杀死占用 8006 端口的进程
lsof -ti :8006 | xargs kill -9
```

---

## 📝 注意事项

### 为什么使用 3006 和 8006？

- **避免冲突**: 3000/8000 和 3008/8008 已被其他项目使用
- **统一规范**: 前端 30XX，后端 80XX
- **易于记忆**: 使用相同的尾数 06

### CORS 配置

后端已配置 CORS 允许前端访问：

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3006"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🧪 测试端口配置

### 1. 测试后端 API
```bash
# 健康检查
curl http://localhost:8006/api/healthz

# 注册用户
curl -X POST http://localhost:8006/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123"}'
```

### 2. 测试前端访问
```bash
# 启动前端后访问
open http://localhost:3006
```

### 3. 测试前端调用后端
```bash
# 在浏览器控制台
fetch('http://localhost:8006/api/healthz')
  .then(r => r.json())
  .then(console.log)
```

---

## 🔄 更新历史

| 日期 | 变更 | 原因 |
|------|------|------|
| 2025-10-10 | 前端: 3000→3006, 后端: 8000→8006 | 避免与其他项目端口冲突 |

---

## 📚 相关文档

- `frontend/.env.development` - 前端环境变量
- `frontend/vite.config.ts` - Vite 配置
- `frontend/package.json` - NPM 脚本
- `backend/app/main.py` - FastAPI 应用配置

---

**最后更新**: 2025-10-10 21:30
**维护者**: Frontend Agent

