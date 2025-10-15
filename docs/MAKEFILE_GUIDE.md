# Makefile 使用指南

> **创建日期**: 2025-10-10  
> **用途**: Reddit Signal Scanner 项目的统一启动与管理脚本  
> **位置**: 项目根目录 `Makefile`  

---

## 📋 目录

1. [快速开始](#快速开始)
2. [开发服务器](#开发服务器)
3. [测试命令](#测试命令)
4. [Celery 任务系统](#celery-任务系统)
5. [数据库迁移](#数据库迁移)
6. [清理命令](#清理命令)
7. [依赖管理](#依赖管理)
8. [常见场景](#常见场景)

---

## 🚀 快速开始

### 查看所有可用命令

```bash
make help
```

输出示例：
```
Reddit Signal Scanner - 可用命令：

  help                 显示所有可用命令
  dev-backend          启动后端开发服务器 (FastAPI + Uvicorn, 端口 8006)
  dev-frontend         启动前端开发服务器 (Vite, 端口 3006)
  test-backend         运行后端所有测试
  celery-start         启动 Celery Worker
  ...
```

### 查看快速启动指南

```bash
make quickstart
```

---

## 🖥️ 开发服务器

### 启动后端服务器

```bash
make dev-backend
```

**效果**:
- 启动 FastAPI + Uvicorn 开发服务器
- 端口: `8006`
- 自动重载: ✅ 代码修改后自动重启
- 访问地址:
  - API 根路径: http://localhost:8006
  - Swagger UI: http://localhost:8006/docs
  - OpenAPI JSON: http://localhost:8006/openapi.json

**日志输出**:
```
==> Starting backend development server on http://localhost:8006 ...
    API Docs: http://localhost:8006/docs
    OpenAPI JSON: http://localhost:8006/openapi.json
INFO:     Uvicorn running on http://0.0.0.0:8006 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 启动前端服务器

```bash
make dev-frontend
```

**效果**:
- 启动 Vite 开发服务器
- 端口: `3006`
- 热更新: ✅ 代码修改后自动刷新
- 访问地址: http://localhost:3006

**日志输出**:
```
==> Starting frontend development server on http://localhost:3006 ...
  VITE v5.0.0  ready in 500 ms

  ➜  Local:   http://localhost:3006/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### 同时启动前后端

**方式 1: 两个终端**

```bash
# 终端 1
make dev-backend

# 终端 2
make dev-frontend
```

**方式 2: 使用 tmux**

```bash
# 创建新 session
tmux new -s reddit-scanner

# 分割窗口
Ctrl+B %

# 左侧窗口
make dev-backend

# 切换到右侧窗口
Ctrl+B →

# 右侧窗口
make dev-frontend
```

---

## 🧪 测试命令

### 运行后端测试

```bash
make test-backend
```

**效果**:
- 运行所有后端测试
- 使用 pytest
- 详细输出 (`-v`)
- 短格式错误信息 (`--tb=short`)

**输出示例**:
```
==> Running backend tests ...
============================= test session starts ==============================
platform darwin -- Python 3.11.13, pytest-8.4.2
collected 33 items

tests/api/test_analyze.py::test_create_analysis_task PASSED              [  3%]
tests/api/test_auth.py::test_register_user_creates_account PASSED        [  9%]
...
=================== 32 passed, 1 skipped, 1 warning in 0.91s ===================
```

### 运行前端测试

```bash
make test-frontend
```

### 运行所有测试

```bash
make test-all
```

**效果**: 依次运行后端和前端测试

### 快捷方式

```bash
make test
```

**效果**: 等同于 `make test-backend`

---

## ⚙️ Celery 任务系统

### 启动 Celery Worker

```bash
make celery-start
```

**效果**:
- 启动 Celery Worker
- 队列: `analysis_queue`
- 自动重载: ✅

**自定义并发数**:

```bash
make celery-start ARGS="--concurrency 4"
```

### 验证 Celery 配置

```bash
make celery-verify
```

**效果**:
- 检查 Redis 连接
- 检查 Result Backend
- 验证任务注册

### 创建测试任务

```bash
# 使用默认参数
make celery-seed

# 使用唯一邮箱（避免冲突）
make celery-seed-unique

# 自定义参数
make celery-seed ARGS="--email test@example.com --description 'AI note-taking app'"
```

### 清理测试数据

```bash
make celery-purge
```

**效果**: 删除所有由脚本生成的测试任务和用户

### 运行 Celery 测试

```bash
make celery-test
```

**效果**: 运行 `test_task_system.py` 和 `test_celery_basic.py`

### 类型检查

```bash
make celery-mypy
```

**效果**: 对任务系统核心文件运行 `mypy --strict`

---

## 🗄️ 数据库迁移

### 创建新迁移

```bash
make db-migrate MESSAGE="添加用户头像字段"
```

**效果**:
- 使用 Alembic 自动生成迁移脚本
- 迁移文件位置: `backend/alembic/versions/`

### 升级数据库

```bash
make db-upgrade
```

**效果**: 将数据库升级到最新版本

### 降级数据库

```bash
make db-downgrade
```

**效果**: 降级数据库一个版本

### 重置数据库（危险！）

```bash
make db-reset
```

**效果**:
- 降级到 base（删除所有表）
- 重新升级到 head（重建所有表）
- **警告**: 会删除所有数据！

**交互式确认**:
```
==> WARNING: This will drop all tables and recreate them!
Are you sure? [y/N]
```

---

## 🧹 清理命令

### 清理所有生成文件

```bash
make clean
```

**效果**: 清理 Python 缓存和测试缓存

### 清理 Python 缓存

```bash
make clean-pyc
```

**效果**:
- 删除 `*.pyc` 文件
- 删除 `__pycache__` 目录
- 删除 `*.egg-info` 目录

### 清理测试缓存

```bash
make clean-test
```

**效果**:
- 删除 `.pytest_cache` 目录
- 删除 `.mypy_cache` 目录
- 删除 `.coverage` 文件

---

## 📦 依赖管理

### 安装后端依赖

```bash
make install-backend
```

**效果**:
- 安装 `requirements.txt` 中的依赖（如果存在）
- 安装测试依赖: `pytest`, `pytest-asyncio`, `fakeredis`, `httpx`

### 安装前端依赖

```bash
make install-frontend
```

**效果**: 运行 `npm install`

### 安装所有依赖

```bash
make install
```

**效果**: 依次安装后端和前端依赖

---

## 💡 常见场景

### 场景 1: 首次启动项目

```bash
# 1. 安装依赖
make install

# 2. 升级数据库
make db-upgrade

# 3. 启动后端（终端 1）
make dev-backend

# 4. 启动前端（终端 2）
make dev-frontend

# 5. 访问应用
# 前端: http://localhost:3006
# 后端: http://localhost:8006/docs
```

### 场景 2: 日常开发

```bash
# 启动后端
make dev-backend

# 运行测试（新终端）
make test-backend

# 清理缓存
make clean
```

### 场景 3: 测试 Celery 任务

```bash
# 1. 启动 Celery Worker（终端 1）
make celery-start

# 2. 验证配置（终端 2）
make celery-verify

# 3. 创建测试任务
make celery-seed-unique

# 4. 运行测试
make celery-test
```

### 场景 4: 数据库迁移

```bash
# 1. 修改模型代码
# 编辑 backend/app/models/*.py

# 2. 创建迁移
make db-migrate MESSAGE="添加新字段"

# 3. 检查迁移文件
# 查看 backend/alembic/versions/

# 4. 应用迁移
make db-upgrade

# 5. 验证
make dev-backend
# 检查数据库表结构
```

### 场景 5: 清理与重置

```bash
# 清理缓存
make clean

# 重置数据库（危险！）
make db-reset

# 重新安装依赖
make install
```

---

## 🔧 自定义与扩展

### 修改默认端口

编辑 `Makefile`:

```makefile
dev-backend:
	@cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 添加新命令

```makefile
my-command: ## 我的自定义命令
	@echo "==> Running my command ..."
	@cd $(BACKEND_DIR) && python my_script.py
```

### 传递参数

```bash
# 定义支持参数的命令
my-command:
	@cd $(BACKEND_DIR) && python my_script.py $(ARGS)

# 使用
make my-command ARGS="--verbose --output report.txt"
```

---

## 📚 参考资料

- [GNU Make 文档](https://www.gnu.org/software/make/manual/)
- [Makefile 最佳实践](https://makefiletutorial.com/)
- [项目 README](../README.md)
- [环境配置指南](./2025-10-10-环境配置完全指南.md)

---

**文档版本**: v1.0  
**最后更新**: 2025-10-10  
**维护人**: Backend Agent A

