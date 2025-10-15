# Day 9 任务分配与验收文档

> **日期**: 2025-10-14 (Day 9)
> **文档用途**: 任务分配、进度跟踪、验收标准
> **创建时间**: 2025-10-13 23:55
> **责任人**: Lead
> **关键里程碑**: 🚀 **集成测试完成 + 性能优化 + Bug修复!**

---

## 🚨 Day 9 前置条件（必须完成）

### ⚠️ 关键环境配置（阻塞所有测试）

#### 1. 启动后端服务（P0 - **阻塞QA**）
```bash
# 终端1: 启动后端API服务器
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8006

# 验证后端服务可访问
curl http://localhost:8006/docs
# 期望: 返回Swagger UI HTML

# 验证健康检查
curl http://localhost:8006/health
# 期望: {"status": "healthy"}
```

**负责人**: QA Agent / Backend Team
**时间**: 2分钟
**状态**: ❌ **Day 8未完成，Day 9必须完成**

#### 2. 启动Celery Worker（P0 - **阻塞分析任务**）
```bash
# 终端2: 启动Celery Worker
cd backend
celery -A app.tasks.celery_app worker --loglevel=info

# 验证Worker运行
celery -A app.tasks.celery_app inspect active
# 期望: 显示活跃Worker列表
```

**负责人**: Backend Team
**时间**: 1分钟

#### 3. 验证认证机制（P0 - **关键变更**）
```bash
# SSE现已改用Bearer token认证
# 所有端到端测试必须先获取有效token

# 示例: 注册并获取token
TOKEN=$(curl -s -X POST http://localhost:8006/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"day9-test@example.com","password":"Test123"}' \
  | jq -r '.access_token')

# 使用token访问SSE
curl -N http://localhost:8006/api/analyze/stream/{task_id} \
  -H "Authorization: Bearer $TOKEN"
# 期望: SSE事件流
```

**负责人**: 全体成员
**重要性**: ⚠️ **SSE认证机制已变更，所有端到端测试必须更新**

---

## 📋 Day 8 遗留问题（必须闭环）

### 问题1: Frontend集成测试失败4个（P0 - **阻塞验收**）

**现状**:
- Frontend测试: 38/42通过 (90%)
- 集成测试: 0/4通过 (后端未启动导致404)
- 导出测试: 12/12通过 ✅
- 单元测试: 26/26通过 ✅

**Day 9任务**:
1. QA Agent启动后端服务
2. 重新运行前端测试: `npm test -- --run`
3. 验证4个集成测试通过
4. 目标: 42/42测试通过 (100%)

**验收标准**:
- [ ] 后端服务运行 (http://localhost:8006)
- [ ] 前端测试100%通过 (42/42)
- [ ] 集成测试覆盖: 注册、登录、创建任务、查询状态

**负责人**: QA Agent
**优先级**: P0
**预计时间**: 30分钟

---

## 👨‍💻 Backend A（资深后端）任务清单

### 核心职责
1. **性能优化** (优先级P1)
2. **信号提取准确率优化** (优先级P1)
3. **Bug修复** (优先级P0)

### 上午任务 (9:00-12:00) - 性能优化

#### 1️⃣ 分析引擎性能优化 (2小时) - 优先级P1

**任务描述**:
优化分析引擎性能，确保分析时间<270秒

**分析重点**:
1. Reddit API调用性能
2. 数据库查询优化
3. 缓存策略优化
4. 信号提取算法性能

**优化方向**:
```python
# 1. 并发优化
# 增加并发度，减少等待时间
async def collect_posts_optimized(subreddits: List[str]):
    tasks = [fetch_subreddit(sub) for sub in subreddits]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 2. 数据库查询优化
# 使用select_in_loading减少N+1查询
from sqlalchemy.orm import selectinload

stmt = select(Analysis).options(
    selectinload(Analysis.task)
).where(Analysis.id == analysis_id)

# 3. 缓存策略优化
# 增加缓存TTL，减少API调用
CACHE_TTL = 86400 * 2  # 48小时（原24小时）

# 4. 信号提取优化
# 使用集合操作提升性能
negative_terms_set = set(NEGATIVE_WORDS)
matched_terms = [term for term in text_words if term in negative_terms_set]
```

**验收标准**:
- [ ] 分析时间<270秒 (目标: <180秒)
- [ ] 缓存命中率>60% (目标: >75%)
- [ ] API调用次数优化 (减少20%)
- [ ] 数据库查询优化 (减少N+1查询)

---

#### 2️⃣ 信号提取准确率优化 (2小时) - 优先级P1

**任务描述**:
优化信号提取算法，提升痛点/竞品/机会识别准确率

**优化方向**:
```python
# 1. 痛点识别优化
# 增加更多痛点模式
PAIN_POINT_PATTERNS = [
    r"\b(i\s+(?:hate|can't stand)\s+.+)",
    r"\b(.+?\s+is\s+(?:too\s+)?(?:slow|broken|unreliable|expensive))",
    r"\b(struggle[s]? to\s+.+)",
    r"\b(problem[s]? with\s+.+)",
    # 新增模式
    r"\b(why is .+? so .+)",  # "why is X so slow"
    r"\b(can't believe .+)",   # "can't believe how bad X is"
    r"\b(.+? doesn't work)",   # "X doesn't work"
]

# 2. 竞品识别优化
# 增加品牌识别规则
def extract_product_names_enhanced(sentence: str) -> List[str]:
    # 识别产品名称模式
    # - 大写开头的连续词组
    # - URL域名
    # - 常见产品后缀 (App, Tool, Platform)
    pass

# 3. 机会识别优化
# 增加需求信号强度计算
def calculate_demand_signal(frequency: int, urgency: float, avg_score: float) -> float:
    # 综合考虑频率、紧迫性、社区热度
    demand_score = min(frequency / 5.0, 1.0)
    urgency_weight = min(urgency / frequency, 1.0)
    market_signal = min(avg_score / 80.0, 1.0)

    return (demand_score * 0.4) + (urgency_weight * 0.3) + (market_signal * 0.3)
```

**验收标准**:
- [ ] 痛点识别准确率>75% (人工评估)
- [ ] 竞品识别准确率>80% (人工评估)
- [ ] 机会识别准确率>70% (人工评估)
- [ ] 信号排序合理性验证

---

### 下午任务 (14:00-18:00) - Bug修复和测试

#### 3️⃣ Bug修复和测试完善 (2小时) - 优先级P0

**任务描述**:
修复已知Bug，完善单元测试和集成测试

**Bug清单**:
1. 检查信号提取中的边界情况处理
2. 验证异步任务异常处理
3. 检查数据库连接池配置
4. 验证缓存失效策略

**测试完善**:
```python
# 1. 增加边界测试
def test_signal_extraction_empty_posts():
    """测试空帖子列表"""
    extractor = SignalExtractor()
    result = extractor.extract([], keywords=[])
    assert len(result.pain_points) == 0
    assert len(result.competitors) == 0
    assert len(result.opportunities) == 0

def test_signal_extraction_special_characters():
    """测试特殊字符处理"""
    posts = [{"text": "I hate <script>alert('xss')</script>"}]
    result = extractor.extract(posts, keywords=[])
    # 验证XSS过滤

# 2. 增加性能测试
@pytest.mark.benchmark
def test_signal_extraction_performance(benchmark):
    """测试信号提取性能"""
    posts = generate_mock_posts(1000)
    result = benchmark(extractor.extract, posts, keywords=[])
    assert benchmark.stats.mean < 1.0  # 期望<1秒
```

**验收标准**:
- [ ] 所有已知Bug修复
- [ ] 单元测试覆盖率>90%
- [ ] 边界测试通过
- [ ] 性能测试通过

---

#### 4️⃣ 端到端测试脚本创建 (1小时) - 优先级P1

**任务描述**:
创建Day 8缺失的端到端测试脚本

**实现文件**: `backend/scripts/test_end_to_end_day9.py`

```python
"""
Day 9 端到端测试脚本
验证完整分析流水线（包含信号提取）
使用Bearer token认证
"""
import asyncio
import time
import httpx
from typing import Dict, Any

BASE_URL = "http://localhost:8006"

async def test_full_analysis_with_signals():
    """测试完整分析流程（含信号提取验证）"""
    print("🚀 开始Day 9端到端测试...")

    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. 注册用户并获取token
        print("1️⃣ 注册用户...")
        register_resp = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"day9-e2e-{int(time.time())}@example.com",
                "password": "Test123"
            }
        )
        assert register_resp.status_code == 200, f"注册失败: {register_resp.text}"
        token = register_resp.json()["access_token"]
        print(f"✅ Token获取成功: {token[:20]}...")

        # 2. 创建分析任务
        print("2️⃣ 创建分析任务...")
        headers = {"Authorization": f"Bearer {token}"}
        analyze_resp = await client.post(
            f"{BASE_URL}/api/analyze",
            headers=headers,
            json={"product_description": "AI-powered note-taking app for researchers"}
        )
        assert analyze_resp.status_code == 200, f"任务创建失败: {analyze_resp.text}"
        task_id = analyze_resp.json()["task_id"]
        print(f"✅ 任务创建成功: {task_id}")

        # 3. 等待任务完成
        print("3️⃣ 等待任务完成...")
        start_time = time.time()
        max_wait = 300  # 最大等待5分钟

        while True:
            status_resp = await client.get(
                f"{BASE_URL}/api/status/{task_id}",
                headers=headers
            )
            assert status_resp.status_code == 200, f"查询状态失败: {status_resp.text}"
            status_data = status_resp.json()

            if status_data["status"] == "completed":
                print(f"✅ 任务完成")
                break
            elif status_data["status"] == "failed":
                raise AssertionError(f"❌ 任务失败: {status_data.get('error')}")

            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"❌ 任务超时: {elapsed:.2f}秒 > {max_wait}秒")

            print(f"   进度: {status_data.get('progress', 0)}% - {elapsed:.1f}秒")
            await asyncio.sleep(3)

        duration = time.time() - start_time

        # 4. 获取报告并验证信号
        print("4️⃣ 获取分析报告...")
        report_resp = await client.get(
            f"{BASE_URL}/api/report/{task_id}",
            headers=headers
        )
        assert report_resp.status_code == 200, f"获取报告失败: {report_resp.text}"
        report = report_resp.json()

        # 5. 验证信号数据结构
        print("5️⃣ 验证信号数据...")
        pain_points = report.get("report", {}).get("pain_points", [])
        competitors = report.get("report", {}).get("competitors", [])
        opportunities = report.get("report", {}).get("opportunities", [])

        print(f"\n📊 分析结果:")
        print(f"   ⏱️  耗时: {duration:.2f}秒")
        print(f"   😣 痛点数: {len(pain_points)}")
        print(f"   🏢 竞品数: {len(competitors)}")
        print(f"   💡 机会数: {len(opportunities)}")

        # 6. 验收标准检查
        print("\n✅ 验收标准检查:")

        # 性能指标
        assert duration < 270, f"❌ 耗时超标: {duration:.2f}秒 > 270秒"
        print(f"   ✅ 性能达标: {duration:.2f}秒 < 270秒")

        # 信号数量
        assert len(pain_points) >= 5, f"❌ 痛点数不足: {len(pain_points)} < 5"
        print(f"   ✅ 痛点数达标: {len(pain_points)} >= 5")

        assert len(competitors) >= 3, f"❌ 竞品数不足: {len(competitors)} < 3"
        print(f"   ✅ 竞品数达标: {len(competitors)} >= 3")

        assert len(opportunities) >= 3, f"❌ 机会数不足: {len(opportunities)} < 3"
        print(f"   ✅ 机会数达标: {len(opportunities)} >= 3")

        # 7. 数据结构验证
        print("\n📋 数据结构验证:")
        if pain_points:
            first_pain = pain_points[0]
            assert "description" in first_pain, "痛点缺少description字段"
            assert "frequency" in first_pain, "痛点缺少frequency字段"
            print(f"   ✅ 痛点数据结构完整")
            print(f"      示例: {first_pain.get('description', '')[:50]}...")

        if competitors:
            first_comp = competitors[0]
            assert "name" in first_comp, "竞品缺少name字段"
            assert "mentions" in first_comp, "竞品缺少mentions字段"
            print(f"   ✅ 竞品数据结构完整")
            print(f"      示例: {first_comp.get('name', '')}")

        if opportunities:
            first_opp = opportunities[0]
            assert "description" in first_opp, "机会缺少description字段"
            assert "relevance_score" in first_opp, "机会缺少relevance_score字段"
            print(f"   ✅ 机会数据结构完整")
            print(f"      示例: {first_opp.get('description', '')[:50]}...")

        print("\n🎉 所有验收标准通过!")
        return True

async def test_sse_with_bearer_token():
    """测试SSE Bearer token认证"""
    print("\n🔐 测试SSE认证...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 获取token
        register_resp = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"day9-sse-{int(time.time())}@example.com",
                "password": "Test123"
            }
        )
        token = register_resp.json()["access_token"]

        # 创建任务
        headers = {"Authorization": f"Bearer {token}"}
        analyze_resp = await client.post(
            f"{BASE_URL}/api/analyze",
            headers=headers,
            json={"product_description": "test"}
        )
        task_id = analyze_resp.json()["task_id"]

        # 测试SSE连接（使用Bearer token）
        async with client.stream(
            "GET",
            f"{BASE_URL}/api/analyze/stream/{task_id}",
            headers=headers
        ) as response:
            assert response.status_code == 200, f"SSE连接失败: {response.status_code}"
            print("✅ SSE Bearer token认证成功")

            # 读取前几个事件
            event_count = 0
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    event_count += 1
                    print(f"   收到事件: {line[:50]}...")
                    if event_count >= 3:
                        break

            assert event_count > 0, "未收到SSE事件"
            print(f"✅ SSE事件流正常 (收到{event_count}个事件)")

if __name__ == "__main__":
    print("=" * 60)
    print("Day 9 端到端测试")
    print("=" * 60)

    try:
        # 测试1: 完整分析流程
        asyncio.run(test_full_analysis_with_signals())

        # 测试2: SSE认证
        asyncio.run(test_sse_with_bearer_token())

        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise
```

**验收标准**:
- [ ] 测试脚本创建完成
- [ ] 测试包含Bearer token认证
- [ ] 测试验证信号数据结构
- [ ] 测试验证性能指标
- [ ] 测试可重复执行

---

## 👨‍💻 Backend B（支撑后端）任务清单

### 核心职责
1. **完成Frontend集成测试环境配置** (优先级P0 - **阻塞QA**)
2. **Admin后台完善** (优先级P1)
3. **监控和告警** (优先级P2)

### 上午任务 (9:00-12:00) - 测试环境配置

#### 1️⃣ 配置测试环境，支持Frontend集成测试 (2小时) - 优先级P0

**任务描述**:
确保Frontend集成测试可以正常运行，解决后端未启动导致的404问题

**任务清单**:
1. ✅ 确认后端服务启动脚本
2. ✅ 配置测试数据库（独立于开发数据库）
3. ✅ 创建测试前置脚本
4. ✅ 验证4个集成测试通过

**测试数据库配置**:
```bash
# 1. 创建测试数据库
createdb reddit_scanner_test

# 2. 配置测试环境变量
# .env.test
DATABASE_URL=postgresql://postgres:password@localhost:5432/reddit_scanner_test
REDIS_URL=redis://localhost:6379/1
JWT_SECRET=test-secret-key

# 3. 运行数据库迁移
cd backend
alembic -c alembic.ini upgrade head
```

**前置脚本创建**:
```bash
# backend/scripts/start_test_server.sh
#!/bin/bash

echo "Starting test environment..."

# 1. 清理测试数据库
psql -U postgres -d reddit_scanner_test -c "TRUNCATE users, tasks, analyses CASCADE;"

# 2. 启动测试服务器
uvicorn app.main:app --host 0.0.0.0 --port 8006 &
SERVER_PID=$!

# 3. 等待服务器启动
sleep 3

# 4. 验证服务器可访问
curl -s http://localhost:8006/docs > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Test server started (PID: $SERVER_PID)"
    echo $SERVER_PID > /tmp/test_server.pid
else
    echo "❌ Test server failed to start"
    kill $SERVER_PID
    exit 1
fi
```

**验收标准**:
- [ ] 测试数据库配置完成
- [ ] 测试服务器启动脚本创建
- [ ] 前端集成测试4/4通过
- [ ] 测试环境文档完善

---

### 下午任务 (14:00-18:00) - Admin完善

#### 2️⃣ Admin后台功能完善 (2小时) - 优先级P1

**任务描述**:
完善Admin后台功能，增加更多监控和管理功能

**功能清单**:
1. 任务失败率统计
2. 用户活跃度分析
3. 系统性能监控
4. 错误日志查询

**实现示例**:
```python
@router.get("/dashboard/performance")
async def get_performance_metrics(
    _payload: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """获取系统性能指标"""

    # 1. 任务失败率
    total_tasks = await db.scalar(select(func.count(Task.id)))
    failed_tasks = await db.scalar(
        select(func.count(Task.id)).where(Task.status == TaskStatus.FAILED)
    )
    failure_rate = (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # 2. 平均响应时间
    avg_response_time = await db.scalar(
        select(
            func.avg(
                func.extract("epoch", Task.completed_at - Task.created_at)
            )
        ).where(
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at.is_not(None)
        )
    )

    # 3. API调用统计（从Redis获取）
    # TODO: 实现API调用计数器

    return _response({
        "failure_rate": round(failure_rate, 2),
        "avg_response_time_seconds": round(float(avg_response_time or 0), 2),
        "total_tasks": int(total_tasks or 0),
        "failed_tasks": int(failed_tasks or 0),
    })
```

**验收标准**:
- [ ] 性能监控接口实现
- [ ] 失败率统计接口实现
- [ ] Admin API测试通过
- [ ] API文档更新

---

## 👩‍💻 Frontend（全栈前端）任务清单

### 核心职责
1. **配合QA完成集成测试** (优先级P0)
2. **UI优化和Bug修复** (优先级P1)
3. **性能优化** (优先级P2)

### 上午任务 (9:00-12:00) - 集成测试配合

#### 1️⃣ 配合QA完成集成测试验证 (1小时) - 优先级P0

**任务描述**:
配合QA Agent完成4个集成测试的验证

**任务清单**:
1. 确认后端服务已启动
2. 验证Bearer token认证更新
3. 协助调试集成测试失败问题
4. 确认所有测试通过

**测试验证**:
```bash
# 1. 验证后端服务
curl http://localhost:8006/docs

# 2. 运行前端测试
cd frontend
npm test -- --run

# 期望结果:
#  Test Files  7 passed (7)
#       Tests  42 passed (42)
#    Duration  < 3s
```

**验收标准**:
- [ ] 后端服务运行正常
- [ ] 前端测试42/42通过 (100%)
- [ ] 集成测试覆盖完整

---

### 下午任务 (14:00-18:00) - UI优化

#### 2️⃣ ReportPage UI优化 (2小时) - 优先级P1

**任务描述**:
优化ReportPage的用户体验和视觉效果

**优化清单**:
1. 加载动画优化（骨架屏）
2. 空状态优化
3. 错误提示优化
4. 响应式布局优化
5. 导出功能UX优化

**优化示例**:
```typescript
// 1. 骨架屏加载
const SkeletonLoader = () => (
  <div className="space-y-4">
    {[1, 2, 3].map((i) => (
      <div key={i} className="rounded-lg border border-border bg-card p-6">
        <div className="h-4 w-3/4 animate-pulse bg-muted rounded" />
        <div className="mt-2 h-4 w-1/2 animate-pulse bg-muted rounded" />
      </div>
    ))}
  </div>
);

// 2. 空状态优化
const EmptyState = ({ type }: { type: string }) => (
  <div className="rounded-xl border border-dashed border-border bg-muted/10 p-12 text-center">
    <AlertCircle className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
    <h3 className="text-lg font-semibold text-foreground mb-2">
      暂无{type}数据
    </h3>
    <p className="text-sm text-muted-foreground">
      分析结果中未发现相关{type}信号
    </p>
  </div>
);

// 3. 导出进度指示
const [exporting, setExporting] = useState(false);

const handleExport = async (format: 'json' | 'csv' | 'text') => {
  setExporting(true);
  try {
    await exportFunction(report, taskId, format);
    toast.success(`${format.toUpperCase()}导出成功`);
  } catch (error) {
    toast.error('导出失败，请重试');
  } finally {
    setExporting(false);
  }
};
```

**验收标准**:
- [ ] 骨架屏加载实现
- [ ] 空状态组件完善
- [ ] 导出进度指示
- [ ] 响应式布局优化
- [ ] 用户体验提升

---

## 🧪 QA Agent任务清单

### 核心职责
1. **完成Frontend集成测试** (优先级P0 - **阻塞验收**)
2. **执行端到端测试** (优先级P0)
3. **性能测试** (优先级P1)

### 上午任务 (9:00-12:00) - 集成测试闭环

#### 1️⃣ 完成Frontend集成测试闭环 (1小时) - 优先级P0

**任务描述**:
启动后端服务，重新运行前端测试，验证4个集成测试通过

**执行步骤**:
```bash
# Step 1: 启动后端服务
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8006 &
BACKEND_PID=$!

# Step 2: 等待服务启动
sleep 3

# Step 3: 验证服务可访问
curl http://localhost:8006/docs
# 期望: 返回HTML

# Step 4: 运行前端测试
cd ../frontend
npm test -- --run

# Step 5: 验证结果
# 期望: Test Files 7 passed (7), Tests 42 passed (42)

# Step 6: 记录结果
echo "Frontend测试结果:" > /tmp/day9_test_result.txt
echo "- 总测试数: 42" >> /tmp/day9_test_result.txt
echo "- 通过数: 42" >> /tmp/day9_test_result.txt
echo "- 失败数: 0" >> /tmp/day9_test_result.txt
echo "- 通过率: 100%" >> /tmp/day9_test_result.txt
```

**验收标准**:
- [ ] 后端服务启动成功
- [ ] 前端测试42/42通过
- [ ] 集成测试覆盖验证
- [ ] 测试结果记录

**预计时间**: 30分钟
**负责人**: QA Agent
**优先级**: P0

---

#### 2️⃣ 执行端到端测试 (2小时) - 优先级P0

**任务描述**:
执行Backend A创建的端到端测试脚本，验证完整流程

**执行步骤**:
```bash
# Step 1: 确保所有服务运行
# - PostgreSQL (5432)
# - Redis (6379)
# - Backend (8006)
# - Celery Worker

# Step 2: 运行端到端测试脚本
cd backend
python scripts/test_end_to_end_day9.py

# Step 3: 验证输出
# 期望:
# ✅ 任务完成，耗时: XX秒
# ✅ 痛点数: XX
# ✅ 竞品数: XX
# ✅ 机会数: XX
# ✅ 所有验收标准通过!

# Step 4: 手动浏览器测试
# 1. 打开 http://localhost:3006
# 2. 输入产品描述
# 3. 等待分析完成
# 4. 验证ReportPage显示
# 5. 测试导出功能（JSON/CSV/TXT）
# 6. 截图记录
```

**验收标准**:
- [ ] 端到端测试脚本通过
- [ ] 分析时间<270秒
- [ ] 信号数量达标（痛点≥5，竞品≥3，机会≥3）
- [ ] 浏览器手动测试通过
- [ ] 导出功能验证通过
- [ ] 截图记录保存

**预计时间**: 2小时
**负责人**: QA Agent
**优先级**: P0

---

### 下午任务 (14:00-18:00) - 性能测试

#### 3️⃣ 性能测试和压力测试 (2小时) - 优先级P1

**任务描述**:
执行性能测试，验证系统在负载下的表现

**测试场景**:
```bash
# 1. 单任务性能测试
# - 验证分析时间<270秒
# - 验证内存使用<500MB
# - 验证CPU使用<80%

# 2. 并发测试（5个并发用户）
# - 同时创建5个分析任务
# - 验证所有任务完成
# - 验证平均响应时间<300秒

# 3. 缓存性能测试
# - 第1次分析（冷缓存）
# - 第2次分析（热缓存）
# - 验证缓存命中率>60%
# - 验证性能提升>30%
```

**测试脚本**:
```python
# backend/scripts/test_performance_day9.py
import asyncio
import httpx
import time
import statistics

async def test_concurrent_analysis(num_users: int = 5):
    """测试并发分析"""
    print(f"🚀 并发测试: {num_users}个用户")

    async def single_user_analysis(user_id: int):
        async with httpx.AsyncClient(timeout=400.0) as client:
            # 注册
            register_resp = await client.post(
                "http://localhost:8006/api/auth/register",
                json={"email": f"perf-user-{user_id}@example.com", "password": "Test123"}
            )
            token = register_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 创建任务
            start = time.time()
            analyze_resp = await client.post(
                "http://localhost:8006/api/analyze",
                headers=headers,
                json={"product_description": f"Test product {user_id}"}
            )
            task_id = analyze_resp.json()["task_id"]

            # 等待完成
            while True:
                status_resp = await client.get(
                    f"http://localhost:8006/api/status/{task_id}",
                    headers=headers
                )
                if status_resp.json()["status"] == "completed":
                    break
                await asyncio.sleep(2)

            duration = time.time() - start
            print(f"   用户{user_id}: {duration:.2f}秒")
            return duration

    # 并发执行
    tasks = [single_user_analysis(i) for i in range(num_users)]
    durations = await asyncio.gather(*tasks)

    # 统计结果
    print(f"\n📊 并发测试结果:")
    print(f"   平均耗时: {statistics.mean(durations):.2f}秒")
    print(f"   最大耗时: {max(durations):.2f}秒")
    print(f"   最小耗时: {min(durations):.2f}秒")

    assert max(durations) < 300, f"最大耗时超标: {max(durations):.2f}秒"
    print("✅ 并发测试通过")

if __name__ == "__main__":
    asyncio.run(test_concurrent_analysis(5))
```

**验收标准**:
- [ ] 单任务性能达标
- [ ] 并发测试通过（5用户）
- [ ] 缓存性能提升验证
- [ ] 性能测试报告

**预计时间**: 2小时
**负责人**: QA Agent
**优先级**: P1

---

## 📝 Day 9 验收清单

### Backend A验收 ✅
- [ ] 性能优化完成（分析时间<270秒）
- [ ] 信号提取准确率优化（>75%）
- [ ] Bug修复完成
- [ ] 端到端测试脚本创建
- [ ] 单元测试覆盖率>90%
- [ ] MyPy --strict 0 errors

### Backend B验收 ✅
- [ ] Frontend集成测试环境配置完成
- [ ] 测试数据库配置完成
- [ ] Admin性能监控接口实现
- [ ] 所有测试通过

### Frontend验收 ✅
- [ ] 集成测试42/42通过 (100%)
- [ ] UI优化完成
- [ ] 骨架屏加载实现
- [ ] 导出功能UX优化
- [ ] TypeScript 0 errors

### QA验收 ✅
- [ ] Frontend集成测试闭环 (42/42通过)
- [ ] 端到端测试通过
- [ ] 性能测试通过
- [ ] 浏览器手动测试通过
- [ ] 测试报告完成

---

## 🎯 Day 9 成功标志

- ✅ **集成测试100%通过** - Frontend 42/42测试通过
- ✅ **端到端测试通过** - 完整流程验证，性能达标
- ✅ **性能优化完成** - 分析时间<270秒，缓存命中率>60%
- ✅ **信号提取优化** - 准确率>75%
- ✅ **SSE认证更新** - Bearer token机制验证通过

---

## 🚨 关键提醒

### ⚠️ SSE认证机制变更（重要）
```typescript
// 旧方式（已废弃）
const eventSource = new EventSource(`/api/analyze/stream/${taskId}`);

// 新方式（必须使用）
const eventSource = new EventSource(
  `/api/analyze/stream/${taskId}`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

// 注意: 原生EventSource不支持自定义header，需要使用polyfill
// 推荐: 使用fetch + ReadableStream或第三方库（如event-source-polyfill）
```

### ⚠️ 前端测试依赖后端服务
```bash
# 运行前端测试前，必须确保:
# 1. 后端服务运行: http://localhost:8006 ✅
# 2. PostgreSQL运行: localhost:5432 ✅
# 3. Redis运行: localhost:6379 ✅
# 4. Celery Worker运行 ✅

# 验证命令:
curl http://localhost:8006/docs           # 后端
psql -h localhost -p 5432 -U postgres     # PostgreSQL
redis-cli ping                             # Redis
celery -A app.tasks.celery_app inspect active  # Celery
```

---

**Day 9 加油！集成测试必须闭环！** 🚀
