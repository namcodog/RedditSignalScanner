# Day 4 任务分配与验收文档

> **日期**: 2025-10-10 (Day 4)
> **文档用途**: 任务分配、进度跟踪、验收标准
> **创建时间**: 16:45
> **责任人**: Lead

---

## 📅 Day 4 总体目标

### 关键产出
- ✅ **4个核心API端点完成**（POST /analyze + GET /status + SSE stream + GET /report）
- ✅ **任务系统100%完成**（任务状态管理 + 进度推送）

### 当晚集成验证
```bash
# 验证所有API端点可用
curl -X POST http://localhost:8000/api/analyze
curl http://localhost:8000/api/status/{task_id}
curl -N http://localhost:8000/api/analyze/stream/{task_id}
curl http://localhost:8000/api/report/{task_id}
```

### Day 4 里程碑
- ✅ API层100%完成（PRD-02）
- ✅ 为 Day 5 前端启动做好准备

---

## 👨‍💻 Backend A（资深后端）任务清单

### 核心任务：完成3个API端点

#### 1️⃣ GET /api/status/{task_id}（优先级 P0）

**文件**: `backend/app/api/routes/tasks.py`（已有基础，需补充）

**功能要求**:
- [ ] 查询任务状态（从数据库）
- [ ] 多租户权限检查（JWT token验证 + user_id匹配）
- [ ] 返回任务详情：status, progress, error_message, retry_count等
- [ ] 错误处理：404（任务不存在）, 403（无权限）

**实现要点**:
```python
@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> TaskStatusResponse:
    # 1. 验证用户权限
    # 2. 查询任务状态
    # 3. 返回详细信息
```

**验收标准**:
- [ ] 端点可访问
- [ ] 权限检查正确（只能查询自己的任务）
- [ ] 响应时间 <200ms
- [ ] 测试用例通过（至少2个测试）

---

#### 2️⃣ GET /api/analyze/stream/{task_id}（优先级 P0 - 核心）

**文件**: `backend/app/api/routes/stream.py`（新建）

**功能要求**:
- [ ] 实现 SSE 端点（Server-Sent Events）
- [ ] 实现 event_generator 异步生成器
- [ ] 推送5种事件：
  - [ ] connected - 连接建立
  - [ ] progress - 进度更新（从Redis缓存读取）
  - [ ] completed - 任务完成
  - [ ] error - 任务失败
  - [ ] close - 连接关闭
- [ ] 心跳机制（每30秒发送heartbeat事件）
- [ ] 多租户权限检查

**技术要点**:
```python
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import asyncio

router = APIRouter(prefix="/analyze", tags=["analysis"])

async def event_generator(task_id: str, user_id: UUID):
    """SSE 事件生成器"""
    # 1. 发送连接建立事件
    yield {
        "event": "connected",
        "data": json.dumps({"task_id": task_id})
    }

    # 2. 循环读取任务状态
    while True:
        status = await STATUS_CACHE.get_status(task_id)

        # 3. 推送进度事件
        yield {
            "event": "progress",
            "data": json.dumps(status)
        }

        # 4. 检查任务是否完成
        if status["status"] in ["completed", "failed"]:
            yield {"event": "close"}
            break

        await asyncio.sleep(1)

@router.get("/stream/{task_id}")
async def stream_task_progress(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
):
    # 权限验证
    # 返回 EventSourceResponse
    return EventSourceResponse(
        event_generator(str(task_id), payload.user_id)
    )
```

**验收标准**:
- [ ] SSE连接成功建立
- [ ] 事件格式符合PRD-02规范
- [ ] 心跳机制工作正常（每30秒）
- [ ] 断线重连测试通过
- [ ] 权限检查正确

**依赖**:
- 需要安装: `pip install sse-starlette`
- 需要 Backend B 完成任务进度推送到Redis

---

#### 3️⃣ GET /api/report/{task_id}（优先级 P1）

**文件**: `backend/app/api/routes/reports.py`（新建）

**功能要求**:
- [ ] 查询完整分析报告
- [ ] 多租户权限检查
- [ ] 返回：痛点、竞品、机会、来源等
- [ ] 错误处理：404（报告不存在）, 409（任务未完成）

**实现要点**:
```python
@router.get("/report/{task_id}", response_model=ReportResponse)
async def get_analysis_report(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> ReportResponse:
    # 1. 权限验证
    # 2. 检查任务状态（必须completed）
    # 3. 查询 Analysis + Report
    # 4. 返回完整报告数据
```

**验收标准**:
- [ ] 端点可访问
- [ ] 返回完整报告数据
- [ ] 权限检查正确
- [ ] 错误处理完善（409: 任务未完成）

---

### 📝 测试任务

**文件**: `backend/tests/api/test_stream.py`（新建）

**测试用例**:
- [ ] `test_sse_connection_established` - SSE连接建立
- [ ] `test_sse_events_pushed` - 事件推送
- [ ] `test_sse_heartbeat_mechanism` - 心跳机制
- [ ] `test_sse_permission_check` - 权限检查

**文件**: `backend/tests/api/test_reports.py`（新建）

**测试用例**:
- [ ] `test_get_report_success` - 成功获取报告
- [ ] `test_get_report_permission_denied` - 权限拒绝
- [ ] `test_get_report_task_not_completed` - 任务未完成（409）

---

### 📊 Backend A 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | GET /api/status/{task_id} | `routes/tasks.py` | 响应<200ms, 权限检查✅ |
| 2 | GET /api/analyze/stream/{task_id} | `routes/stream.py` | SSE连接✅, 事件推送✅ |
| 3 | GET /api/report/{task_id} | `routes/reports.py` | 返回完整报告✅ |
| 4 | SSE 测试 | `tests/api/test_stream.py` | 测试通过✅ |
| 5 | 报告测试 | `tests/api/test_reports.py` | 测试通过✅ |
| 6 | mypy --strict | 全部代码 | 0 errors ✅ |
| 7 | pytest | 全部测试 | 所有测试通过✅ |

**预计完成时间**: 8小时
- GET /api/status: 2h
- GET /api/analyze/stream: 4h（最复杂）
- GET /api/report: 1h
- 测试 + 验证: 1h

---

## 🔧 Backend B（中级后端）任务清单

### 核心任务：完成任务系统集成

#### 1️⃣ 实现任务状态管理（优先级 P0）

**当前状态**: 已有 `TaskStatusCache` (Redis缓存)

**补充功能**:
- [ ] 任务状态写入逻辑（从Celery task写入Redis）
- [ ] 任务进度推送逻辑（更新Redis缓存）
- [ ] 状态同步机制（Redis → PostgreSQL）

**文件**: `backend/app/services/task_status_cache.py`（已有，需补充）

**实现要点**:
```python
class TaskStatusCache:
    async def set_status(self, payload: TaskStatusPayload) -> None:
        """写入任务状态到Redis"""
        # 1. 序列化payload
        # 2. 写入Redis (key: task:{task_id}, ttl: 1小时)
        # 3. 发布订阅通知（可选）

    async def get_status(self, task_id: str) -> Optional[TaskStatusPayload]:
        """从Redis读取任务状态"""
        # 1. 查询Redis
        # 2. 如果不存在，从数据库回退
        # 3. 返回状态
```

**验收标准**:
- [ ] 状态写入功能正常
- [ ] 状态读取功能正常
- [ ] Redis → DB 同步逻辑正确

---

#### 2️⃣ 实现任务进度推送（优先级 P0）

**功能要求**:
- [ ] 在 Celery task 中实时更新任务状态到Redis
- [ ] 推送进度事件（0% → 25% → 50% → 75% → 100%）
- [ ] 推送当前步骤信息（"社区发现" → "数据采集" → ...）

**修改文件**: `backend/app/tasks/analysis_task.py`（已有基础）

**关键代码位置**:
```python
async def _execute_success_flow(task_id: uuid.UUID, retries: int) -> None:
    summary = await _mark_processing(task_id, retries)

    # 推送进度：10% - 任务开始
    await _cache_status(
        str(task_id),
        TaskStatus.PROCESSING,
        progress=10,
        message="任务开始处理"
    )

    # 推送进度：25% - 社区发现
    await _cache_status(
        str(task_id),
        TaskStatus.PROCESSING,
        progress=25,
        message="正在发现相关社区..."
    )

    # 执行分析引擎
    result = await run_analysis(summary)

    # 推送进度：75% - 分析完成
    await _cache_status(
        str(task_id),
        TaskStatus.PROCESSING,
        progress=75,
        message="分析完成，生成报告中..."
    )

    await _store_analysis_results(task_id, result)

    # 推送进度：100% - 任务完成
    await _cache_status(
        str(task_id),
        TaskStatus.COMPLETED,
        progress=100,
        message="分析完成"
    )
```

**验收标准**:
- [ ] 进度更新实时推送到Redis
- [ ] 进度百分比正确（0-100）
- [ ] 步骤信息清晰明确

---

#### 3️⃣ 任务系统测试（优先级 P1）

**文件**: `backend/tests/test_task_system.py`（新建）

**测试用例**:
- [ ] `test_task_status_cache_integration` - Redis缓存集成
- [ ] `test_task_progress_update` - 进度更新
- [ ] `test_task_status_sync_to_db` - 状态同步到DB
- [ ] `test_celery_task_execution_flow` - Celery任务执行流程

---

#### 4️⃣ Worker 验证与文档（优先级 P2）

**任务**:
- [ ] 启动 Celery Worker 并验证任务执行
- [ ] 补充 Worker 运维文档
- [ ] 记录常见问题和解决方案

**文件**: `backend/docs/WORKER_OPS.md`（新建）

**文档内容**:
```markdown
# Celery Worker 运维文档

## 启动 Worker
python backend/scripts/start_celery_worker.py

## 验证 Worker 状态
celery -A app.core.celery_app inspect active

## 监控任务队列
celery -A app.core.celery_app inspect stats

## 常见问题
- 问题1：Worker无法连接Redis
  - 解决方案：检查CELERY_BROKER_URL环境变量

- 问题2：任务执行失败
  - 解决方案：查看Worker日志
```

**验收标准**:
- [ ] Worker可以成功启动
- [ ] 任务可以正常执行
- [ ] 文档清晰完整

---

### 📊 Backend B 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | 任务状态管理 | `services/task_status_cache.py` | 状态同步✅ |
| 2 | 任务进度推送 | `tasks/analysis_task.py` | 实时推送✅ |
| 3 | 任务系统测试 | `tests/test_task_system.py` | 测试通过✅ |
| 4 | Worker文档 | `docs/WORKER_OPS.md` | 文档完整✅ |
| 5 | mypy --strict | 全部代码 | 0 errors ✅ |
| 6 | pytest | 全部测试 | 所有测试通过✅ |

**预计完成时间**: 8小时
- 任务状态管理: 2h
- 任务进度推送: 3h
- 测试 + 文档: 2h
- Worker验证: 1h

---

## 🎨 Frontend（全栈前端）任务清单

### 核心任务：学习与准备

#### 1️⃣ 学习 SSE 客户端实现（优先级 P0）

**学习内容**:
- [ ] EventSource API 使用方法
- [ ] SSE 事件监听与处理
- [ ] SSE 断线重连机制
- [ ] SSE 降级到轮询的策略

**学习资源**:
- MDN EventSource 文档: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- 前端已实现的 `frontend/src/api/sse.client.ts` (Day 2准备工作)
- 前端已实现的 `frontend/src/hooks/useSSE.ts` (自定义Hook)

**学习产出**:
- [ ] 理解 EventSource API 的工作原理
- [ ] 能够使用现有的 SSEClient 类
- [ ] 理解 useSSE Hook 的使用方法

---

#### 2️⃣ 项目结构优化（优先级 P1）

**任务**:
- [ ] 完善前端路由配置
- [ ] 优化页面组件结构
- [ ] 准备状态管理方案（如Zustand/Jotai/Context API）
- [ ] 配置环境变量（VITE_API_BASE_URL）

**文件检查**:
- [ ] `frontend/.env.example` - 环境变量模板
- [ ] `frontend/src/router/index.tsx` - 路由配置
- [ ] `frontend/src/App.tsx` - 应用入口

**验收标准**:
- [ ] 路由配置清晰
- [ ] 环境变量配置完成
- [ ] 项目结构合理

---

#### 3️⃣ API 类型定义验证（优先级 P1）

**任务**:
- [ ] 对比后端API实现，验证TypeScript类型定义
- [ ] 更新 `frontend/src/types/*.ts`（如有变化）
- [ ] 确保类型定义与后端Schema一致

**检查文件**:
- `frontend/src/types/task.types.ts`
- `frontend/src/types/api.types.ts`
- `frontend/src/types/sse.types.ts`

**验收标准**:
- [ ] 类型定义与后端一致
- [ ] TypeScript 编译通过（如果可以运行 `npm run type-check`）

---

#### 4️⃣ 等待 Day 5 API 交接会（阻塞状态）

**准备工作**:
- [ ] 阅读 PRD-02 API设计规范
- [ ] 阅读 PRD-05 前端交互设计
- [ ] 准备API调试工具（Postman/Thunder Client/curl）
- [ ] 等待 Day 5 早上 9:00 API 交接会

**Day 5 交接会内容**:
1. Backend A 演示4个API端点
2. 前端获取API文档（OpenAPI/Swagger）
3. 前端获取测试token
4. 确认接口字段定义
5. 前端开始开发

---

### 📊 Frontend 交付清单

| 序号 | 交付物 | 验收标准 |
|------|-------|---------|
| 1 | 学习 SSE 客户端 | 理解 EventSource API ✅ |
| 2 | 项目结构优化 | 路由配置完善✅, 环境变量配置✅ |
| 3 | 类型定义验证 | 类型一致性✅ |
| 4 | 准备 API 对接 | 环境配置完成✅, 调试工具准备✅ |

**预计完成时间**: 6小时
- 学习 SSE 客户端: 3h
- 项目结构优化: 2h
- 类型定义验证: 1h

---

## 🔗 Day 4 协作节点

### 协作节点 1: 上午 10:00 - 快速同步会（15分钟）

**参与者**: Backend A + Backend B

**讨论内容**:
1. Backend A: 同步 SSE 端点设计方案
2. Backend B: 同步任务进度推送方案
3. 确认 Redis 缓存数据格式（TaskStatusPayload）
4. 确认 SSE 事件格式（event, data）

**产出**:
- Redis 数据格式确认
- SSE 事件格式确认
- 双方无阻塞问题

---

### 协作节点 2: 下午 16:00 - 集成测试（30分钟）

**参与者**: Backend A + Backend B

**测试流程**:
1. Backend A 启动 FastAPI 服务
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Backend B 启动 Celery Worker
   ```bash
   cd backend
   python scripts/start_celery_worker.py
   ```

3. 端到端测试：
   ```bash
   # Step 1: 创建任务
   curl -X POST http://localhost:8000/api/analyze \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer {token}" \
     -d '{"product_description": "测试产品描述..."}'

   # Step 2: 连接 SSE 监听进度
   curl -N http://localhost:8000/api/analyze/stream/{task_id} \
     -H "Authorization: Bearer {token}"

   # Step 3: 查询任务状态
   curl http://localhost:8000/api/status/{task_id} \
     -H "Authorization: Bearer {token}"

   # Step 4: 获取报告
   curl http://localhost:8000/api/report/{task_id} \
     -H "Authorization: Bearer {token}"
   ```

4. 验证任务状态同步正确

**验收点**:
- [ ] SSE 连接成功
- [ ] 进度事件实时推送
- [ ] 任务状态正确
- [ ] 报告数据完整

---

### 协作节点 3: 晚上 18:00 - Day 4 验收会（30分钟）

**参与者**: 全员（Backend A + Backend B + Frontend + Lead）

**验收清单**:
```bash
✅ 4个API端点全部可访问
✅ SSE连接成功建立并推送事件
✅ 任务状态管理正常工作
✅ mypy --strict 0 errors
✅ pytest 所有测试通过
✅ 集成测试通过
```

**验收流程**:
1. Backend A 演示3个新增端点
2. Backend B 演示任务进度推送
3. 运行质量门禁检查
   ```bash
   # mypy 检查
   cd backend
   python -m mypy --strict app

   # pytest 测试
   python -m pytest tests/ -v
   ```
4. Lead 确认所有验收项通过

**验收失败处理**:
- 如果有未通过项，立即分配修复任务
- 修复时间不超过1小时
- 修复后重新验收

---

## 📋 Day 4 执行顺序建议

### Backend A 执行顺序
```
09:00 - 10:00  1. 实现 GET /api/status/{task_id}（最简单）
10:00 - 10:15  [同步会] 与 Backend B 对齐方案
10:15 - 14:00  2. 实现 GET /api/analyze/stream/{task_id}（核心，最复杂）
14:00 - 15:00  3. 实现 GET /api/report/{task_id}（依赖前两个）
15:00 - 16:00  4. 编写测试用例（test_stream.py, test_reports.py）
16:00 - 16:30  [集成测试] 与 Backend B 联调
16:30 - 17:30  5. mypy --strict 验证 + 修复问题
17:30 - 18:00  6. 准备验收材料
18:00 - 18:30  [验收会] 全员验收
```

### Backend B 执行顺序
```
09:00 - 11:00  1. 补充任务状态管理逻辑（task_status_cache.py）
11:00 - 14:00  2. 实现任务进度推送（analysis_task.py）
14:00 - 15:00  3. 编写测试用例（test_task_system.py）
15:00 - 16:00  4. 启动 Worker 验证任务执行
16:00 - 16:30  [集成测试] 与 Backend A 联调
16:30 - 17:00  5. 编写 Worker 运维文档（WORKER_OPS.md）
17:00 - 17:30  6. mypy --strict 验证 + 修复问题
17:30 - 18:00  7. 准备验收材料
18:00 - 18:30  [验收会] 全员验收
```

### Frontend 执行顺序
```
09:00 - 12:00  1. 学习 SSE 客户端实现
12:00 - 14:00  2. 优化项目结构（路由 + 环境变量）
14:00 - 15:00  3. 验证类型定义
15:00 - 17:00  4. 阅读 PRD 文档，准备 API 对接
17:00 - 18:00  5. 准备 API 调试工具和测试环境
18:00 - 18:30  [验收会] 全员验收（主要是观察）
```

---

## ⏰ Day 4 时间预估

| 角色 | 任务 | 预估时间 |
|------|------|---------|
| **Backend A** | GET /api/status | 2h |
| | GET /api/analyze/stream（SSE） | 4h |
| | GET /api/report | 1h |
| | 测试 + 验证 | 1h |
| | **Backend A 总计** | **8h** |
| **Backend B** | 任务状态管理 | 2h |
| | 任务进度推送 | 3h |
| | 测试 + 文档 | 2h |
| | Worker验证 | 1h |
| | **Backend B 总计** | **8h** |
| **Frontend** | 学习 SSE | 3h |
| | 项目优化 | 2h |
| | 类型验证 + 准备 | 1h |
| | **Frontend 总计** | **6h** |

---

## 🚨 Day 4 风险提示与缓解措施

### 风险 1: SSE 实现复杂度高

**风险描述**:
- SSE 端点实现可能遇到技术难点
- EventSource 断线重连机制复杂
- 心跳机制需要精确控制

**影响**: Backend A 进度延迟，可能无法完成

**缓解措施**:
1. Backend A 优先实现基础 SSE 连接（不带心跳）
2. 如遇到问题，立即与 Backend B 协商
3. 保留降级方案（前端使用轮询 GET /api/status）
4. 参考 sse-starlette 官方文档和示例

**应急预案**:
- 如果 18:00 前无法完成 SSE，将 SSE 端点推迟到 Day 5 上午
- 前端 Day 5 先使用轮询方式，后续再切换到 SSE

---

### 风险 2: 任务进度推送时机不准确

**风险描述**:
- Celery 任务中推送进度的时机不准确
- 进度百分比计算复杂
- 分析引擎耗时不确定

**影响**: 前端进度条不准确，用户体验差

**缓解措施**:
1. Backend B 先在 analysis_task.py 中添加简单的进度推送（固定百分比）
2. 后续 Day 6-8 再优化推送精度（基于分析引擎各步骤耗时）
3. 保证至少有 4 个进度更新点：0%, 25%, 75%, 100%

**应急预案**:
- 如果精确进度难以实现，先使用简单的阶段性进度（3-5个阶段）
- 后续迭代优化

---

### 风险 3: 前端等待时间长，积极性受影响

**风险描述**:
- 前端 Day 4 任务较轻，主要是学习和准备
- 可能感觉被阻塞，无法实际开发

**影响**: 前端成员积极性下降

**缓解措施**:
1. 明确告知前端：Day 5 才能开始开发（这是计划设计）
2. 引导前端利用 Day 4 充分学习和准备
3. 鼓励前端深入学习 SSE、React 18 新特性
4. 前端可以参与下午 16:00 的集成测试，观察后端 API

**沟通话术**:
> "Day 4 是后端 API 完成的关键日，前端利用这一天充分学习 SSE 和准备环境，Day 5 早上 9:00 API 交接会后，前端就可以全速开发了。这一天的学习和准备会让 Day 5-11 的开发更加顺利。"

---

### 风险 4: 集成测试失败

**风险描述**:
- 下午 16:00 集成测试时，可能发现 Backend A + Backend B 接口不匹配
- Redis 数据格式不一致
- SSE 事件格式不一致

**影响**: Day 4 无法验收通过

**缓解措施**:
1. 上午 10:00 快速同步会，提前对齐接口格式
2. Backend B 先完成任务状态管理，Backend A 再开始 SSE 开发
3. 定义清晰的数据格式文档（TaskStatusPayload, SSEEvent）

**应急预案**:
- 如果集成测试失败，立即分配修复任务（不超过1小时）
- 如果问题复杂，将部分功能推迟到 Day 5 上午

---

## ✅ Day 4 验收标准

### 功能验收

#### Backend A 功能验收
- [ ] ✅ GET /api/status/{task_id} 端点可访问
- [ ] ✅ GET /api/analyze/stream/{task_id} SSE连接成功
- [ ] ✅ GET /api/report/{task_id} 端点可访问
- [ ] ✅ 多租户权限检查正确（所有端点）
- [ ] ✅ 错误处理完善（404, 403, 409）

#### Backend B 功能验收
- [ ] ✅ 任务状态管理工作正常（写入/读取Redis）
- [ ] ✅ 任务进度推送实时更新（至少4个进度点）
- [ ] ✅ Celery Worker 可以正常启动和执行任务
- [ ] ✅ 任务状态同步正确（Redis ↔ PostgreSQL）

#### Frontend 功能验收
- [ ] ✅ SSE 客户端原理清楚
- [ ] ✅ 项目结构优化完成
- [ ] ✅ 类型定义验证通过
- [ ] ✅ API 对接环境准备完成

---

### 质量验收

#### 代码质量
- [ ] ✅ **mypy --strict**: 0 errors（32 files）
- [ ] ✅ **pytest**: 所有测试通过（预计 10+ tests）
- [ ] ✅ **black**: 代码格式化通过
- [ ] ✅ **isort**: 导入排序正确

#### 测试覆盖
- [ ] ✅ Backend A: 至少新增 5 个测试用例
  - test_stream.py: 4 个测试
  - test_reports.py: 1 个测试
- [ ] ✅ Backend B: 至少新增 4 个测试用例
  - test_task_system.py: 4 个测试

#### API 性能
- [ ] ✅ GET /api/status/{task_id}: 响应时间 <200ms
- [ ] ✅ GET /api/analyze/stream/{task_id}: 连接建立 <500ms
- [ ] ✅ GET /api/report/{task_id}: 响应时间 <500ms

---

### 集成验收

#### 端到端流程
- [ ] ✅ 完整流程可跑通：
  ```
  POST /api/analyze
    → SSE stream 实时监听进度
    → GET /api/status 查询状态
    → GET /api/report 获取报告
  ```

#### 任务状态同步
- [ ] ✅ Celery → Redis: 状态实时写入
- [ ] ✅ Redis → PostgreSQL: 状态最终持久化
- [ ] ✅ Redis 缓存过期后，自动从 PostgreSQL 回退

#### SSE 事件验证
- [ ] ✅ SSE 事件格式符合 PRD-02 规范
- [ ] ✅ 事件类型完整：connected, progress, completed, error, close
- [ ] ✅ 心跳机制正常（每30秒一次）

---

### 文档验收

- [ ] ✅ `backend/docs/WORKER_OPS.md` - Worker 运维文档完整
- [ ] ✅ 代码注释清晰（特别是 SSE 事件生成器）
- [ ] ✅ API 端点文档更新（如有 Swagger/OpenAPI）

---

## 📊 验收流程

### Step 1: 代码质量检查（17:30-17:45）

```bash
# Backend 质量检查
cd backend

# 1. mypy 类型检查
python -m mypy --strict app
# 期望: Success: no issues found in 32 source files

# 2. pytest 测试
python -m pytest tests/ -v
# 期望: X passed in Xs

# 3. black 格式化检查
black app --check
# 期望: All done! ✨ 🍰 ✨

# 4. isort 导入排序检查
isort app --check
# 期望: All done! ✨ 🍰 ✨
```

---

### Step 2: 功能演示（17:45-18:00）

#### Backend A 演示
```bash
# 1. 启动 FastAPI 服务
uvicorn app.main:app --reload

# 2. 演示 GET /api/status/{task_id}
curl http://localhost:8000/api/status/{task_id} \
  -H "Authorization: Bearer {token}"

# 3. 演示 SSE stream
curl -N http://localhost:8000/api/analyze/stream/{task_id} \
  -H "Authorization: Bearer {token}"

# 4. 演示 GET /api/report/{task_id}
curl http://localhost:8000/api/report/{task_id} \
  -H "Authorization: Bearer {token}"
```

#### Backend B 演示
```bash
# 1. 启动 Celery Worker
python scripts/start_celery_worker.py

# 2. 演示任务进度推送
# (通过 Backend A 的 SSE 观察)

# 3. 演示 Worker 文档
cat docs/WORKER_OPS.md
```

---

### Step 3: 集成测试验证（18:00-18:15）

```bash
# 完整流程测试脚本
cd backend

# 1. 创建任务
TASK_ID=$(curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"product_description": "测试产品描述，至少10个字符"}' \
  | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# 2. 连接 SSE 监听进度（另一个终端）
curl -N http://localhost:8000/api/analyze/stream/$TASK_ID \
  -H "Authorization: Bearer {token}"

# 3. 查询任务状态
curl http://localhost:8000/api/status/$TASK_ID \
  -H "Authorization: Bearer {token}"

# 4. 等待任务完成后，获取报告
curl http://localhost:8000/api/report/$TASK_ID \
  -H "Authorization: Bearer {token}"
```

**验收点**:
- [ ] 任务创建成功，返回 task_id
- [ ] SSE 连接成功，收到 connected 事件
- [ ] 收到多个 progress 事件（至少4个）
- [ ] 收到 completed 事件
- [ ] GET /api/status 返回 completed 状态
- [ ] GET /api/report 返回完整报告数据

---

### Step 4: Lead 确认验收（18:15-18:30）

**Lead 检查清单**:
- [ ] ✅ 代码质量：mypy + pytest 全部通过
- [ ] ✅ 功能完整：4个API端点全部可用
- [ ] ✅ 集成测试：端到端流程通过
- [ ] ✅ 文档完整：WORKER_OPS.md 存在且内容完整
- [ ] ✅ 无阻塞问题：Day 5 可以正常启动

**验收结论**:
- ✅ **通过** - Day 4 所有任务完成，可以进入 Day 5
- ❌ **不通过** - 列出未完成项，分配修复任务，1小时内修复后重新验收

---

## 📈 Day 4 成功标志

### 技术指标
- ✅ API 端点数量：4/4（100%）
- ✅ mypy --strict: 0 errors
- ✅ pytest 通过率: 100%
- ✅ API 响应时间: <200ms
- ✅ SSE 连接成功率: 100%

### 业务指标
- ✅ 任务状态管理：实时更新 ✅
- ✅ 任务进度推送：至少4个进度点 ✅
- ✅ 端到端流程：完全打通 ✅

### 团队指标
- ✅ Backend A 按时完成
- ✅ Backend B 按时完成
- ✅ Frontend 学习和准备完成
- ✅ 团队协作顺畅，无阻塞

---

## 🎯 Day 4 完成后的状态

### API 层状态
```
✅ POST /api/analyze          - Day 3 完成
✅ GET /api/status/{task_id}  - Day 4 完成
✅ GET /api/analyze/stream/{task_id} - Day 4 完成
✅ GET /api/report/{task_id}  - Day 4 完成

➡️ API 层 100% 完成，符合 PRD-02
```

### 任务系统状态
```
✅ Celery 基础配置          - Day 3 完成
✅ Worker 启动脚本          - Day 3 完成
✅ 任务状态管理            - Day 4 完成
✅ 任务进度推送            - Day 4 完成

➡️ 任务系统 100% 完成，符合 PRD-04
```

### 为 Day 5 做好准备
```
✅ 4个API端点全部可用
✅ 前端可以开始调用真实API
✅ Day 5 早上 9:00 API 交接会准备完成
✅ 前端开发无阻塞

➡️ Day 5 前端可以全速开发 🚀
```

---

## 📝 验收记录表

**验收日期**: 2025-10-10
**验收时间**: 18:00-18:30
**验收人**: Lead

### Backend A 验收记录

| 验收项 | 状态 | 备注 |
|-------|------|------|
| GET /api/status/{task_id} | [ ] ✅ [ ] ❌ | |
| GET /api/analyze/stream/{task_id} | [ ] ✅ [ ] ❌ | |
| GET /api/report/{task_id} | [ ] ✅ [ ] ❌ | |
| 测试通过（test_stream.py） | [ ] ✅ [ ] ❌ | |
| 测试通过（test_reports.py） | [ ] ✅ [ ] ❌ | |
| mypy --strict 0 errors | [ ] ✅ [ ] ❌ | |

**Backend A 验收结论**: [ ] ✅ 通过 [ ] ❌ 不通过

---

### Backend B 验收记录

| 验收项 | 状态 | 备注 |
|-------|------|------|
| 任务状态管理（Redis） | [ ] ✅ [ ] ❌ | |
| 任务进度推送 | [ ] ✅ [ ] ❌ | |
| 测试通过（test_task_system.py） | [ ] ✅ [ ] ❌ | |
| Worker 文档完整 | [ ] ✅ [ ] ❌ | |
| mypy --strict 0 errors | [ ] ✅ [ ] ❌ | |

**Backend B 验收结论**: [ ] ✅ 通过 [ ] ❌ 不通过

---

### Frontend 验收记录

| 验收项 | 状态 | 备注 |
|-------|------|------|
| 学习 SSE 客户端完成 | [ ] ✅ [ ] ❌ | |
| 项目结构优化完成 | [ ] ✅ [ ] ❌ | |
| 类型定义验证通过 | [ ] ✅ [ ] ❌ | |
| API 对接环境准备完成 | [ ] ✅ [ ] ❌ | |

**Frontend 验收结论**: [ ] ✅ 通过 [ ] ❌ 不通过

---

### 集成验收记录

| 验收项 | 状态 | 备注 |
|-------|------|------|
| 端到端流程测试通过 | [ ] ✅ [ ] ❌ | |
| SSE 事件推送正常 | [ ] ✅ [ ] ❌ | |
| 任务状态同步正确 | [ ] ✅ [ ] ❌ | |

---

### Day 4 最终验收结论

**状态**: [ ] ✅ 通过 [ ] ❌ 不通过

**签字**:
- Lead: ________________  日期: ________
- Backend A: ________________  日期: ________
- Backend B: ________________  日期: ________
- Frontend: ________________  日期: ________

---

## 📞 Day 4 联系方式

如有问题，按以下优先级处理：

### 优先级 P0（阻塞开发）
- 立即 @Lead
- 拉三方紧急会议
- 30分钟内必须解决

### 优先级 P1（影响进度）
- 在协作节点（10:00, 16:00）提出
- 当天必须解决

### 优先级 P2（不紧急）
- 记录到文档
- Day 5 排期处理

---

**Day 4 加油！Let's ship it! 🚀**

---

**文档版本**: v1.0
**最后更新**: 2025-10-10 16:45
**维护人**: Lead
**文档路径**: `/Users/hujia/Desktop/RedditSignalScanner/DAY4-TASK-ASSIGNMENT.md`
