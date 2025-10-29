# SQLAlchemy 连接池配置说明

## 问题背景

在使用 FastAPI + Celery + SQLAlchemy (asyncpg) 的架构中，会遇到以下错误：

```
RuntimeError: Task <Task pending> got Future <Future pending> attached to a different loop
asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation
```

## 根本原因

### 事件循环冲突

1. **FastAPI (主进程)**：运行在主事件循环中
   - 使用 `uvicorn` 启动
   - 创建数据库连接池
   - 连接绑定到主事件循环

2. **Celery Worker (独立进程/线程)**：运行在独立事件循环中
   - 使用 `celery worker` 启动
   - 尝试使用同一个数据库连接池
   - 连接绑定到不同的事件循环

3. **冲突发生**：
   - Celery 任务尝试访问数据库
   - 从连接池获取连接
   - 连接绑定到主循环，但当前在 Celery 循环中
   - 抛出 `RuntimeError: attached to a different loop`

## 解决方案

### 方案 1: 禁用连接池（推荐用于开发环境）

在 `backend/.env` 中添加：

```bash
SQLALCHEMY_DISABLE_POOL=1
```

**工作原理**：
- 使用 `NullPool`（无连接池）
- 每次请求创建新连接
- 每次请求后关闭连接
- 避免连接在不同事件循环间共享

**优点**：
- ✅ 完全避免事件循环冲突
- ✅ 配置简单，一行搞定
- ✅ 适合开发环境

**缺点**：
- ❌ 性能略低（每次创建/销毁连接）
- ❌ 不适合高并发生产环境

### 方案 2: 调整连接池大小（生产环境）

在 `backend/.env` 中配置：

```bash
SQLALCHEMY_DISABLE_POOL=0
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_MAX_OVERFLOW=20
```

**注意事项**：
- 需要确保 Celery Worker 使用独立的数据库连接
- 需要在 Celery 任务中使用 `get_session_context()` 创建新 session
- 需要正确配置 `pool_pre_ping=True`

## 代码实现

### `backend/app/db/session.py`

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL")
USE_NULL_POOL = os.getenv("SQLALCHEMY_DISABLE_POOL", "0") == "1"
POOL_SIZE = int(os.getenv("SQLALCHEMY_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "10"))

def _create_engine():
    engine_kwargs = {
        "pool_pre_ping": True,
        "future": True,
        "echo": False,
    }

    if USE_NULL_POOL:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = POOL_SIZE
        engine_kwargs["max_overflow"] = MAX_OVERFLOW

    return create_async_engine(DATABASE_URL, **engine_kwargs)

engine = _create_engine()
```

## 验证配置

### 检查环境变量是否生效

```bash
# 方法 1: 查看 .env 文件
cat backend/.env | grep SQLALCHEMY_DISABLE_POOL

# 方法 2: 在 Python 中检查
cd backend
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'SQLALCHEMY_DISABLE_POOL={os.getenv(\"SQLALCHEMY_DISABLE_POOL\")}')"
```

### 检查连接池类型

```bash
cd backend
python3 << 'EOF'
from app.db.session import engine
print(f"Pool class: {engine.pool.__class__.__name__}")
# 期望输出: Pool class: NullPool (如果 SQLALCHEMY_DISABLE_POOL=1)
# 期望输出: Pool class: AsyncAdaptedQueuePool (如果 SQLALCHEMY_DISABLE_POOL=0)
EOF
```

## 重启服务以应用配置

**重要**：修改 `.env` 文件后，必须重启所有服务才能生效！

```bash
# 方法 1: 使用 Makefile（推荐）
make kill-ports
make kill-celery
make dev-golden-path

# 方法 2: 手动重启
pkill -f "celery.*worker"
pkill -f "uvicorn"
# 然后重新启动服务
```

## 常见问题

### Q1: 为什么修改 `.env` 后错误依然存在？

**A**: 旧进程还在运行，没有加载新的环境变量。

**解决方案**：
```bash
make kill-ports && make kill-celery && make dev-golden-path
```

### Q2: 生产环境应该使用哪个配置？

**A**: 生产环境建议使用连接池（`SQLALCHEMY_DISABLE_POOL=0`），但需要：
1. 确保 Celery Worker 使用独立的数据库连接
2. 调整 `POOL_SIZE` 和 `MAX_OVERFLOW` 以适应负载
3. 监控连接池使用情况

### Q3: 如何判断是否遇到了事件循环冲突？

**A**: 查看错误日志，如果出现以下关键词，就是事件循环冲突：
- `RuntimeError: Task got Future attached to a different loop`
- `asyncpg.exceptions.ConnectionDoesNotExistError`
- `greenlet_spawn has not been called`

## 参考资料

- [SQLAlchemy AsyncIO Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [FastAPI + Celery Best Practices](https://fastapi.tiangolo.com/advanced/async-sql-databases/)
- [asyncpg Connection Pooling](https://magicstack.github.io/asyncpg/current/usage.html#connection-pools)

## 更新日志

- **2025-10-28**: 初始版本，记录 Spec 007 验收过程中发现的问题和解决方案

