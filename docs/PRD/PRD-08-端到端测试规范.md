# PRD-08: 端到端测试规范

## 0. 对齐口径（现状）
- E2E 入口：`make test-e2e` / `make test-admin-e2e`
- KAG 验收入口：`make kag-acceptance`（检查 knowledge_graph / hybrid_posts_used）
- 前端配置：`frontend/playwright.config.ts`
- 主要执行记录：`reports/phase-log/phase106.md`、`reports/phase-log/phase107.md`

## 1. 问题陈述

### 1.1 背景
基于对PRD 1-7的审查，发现了关键的端到端测试遗漏。虽然每个组件都有单元测试，但缺少完整的用户旅程验证和系统级失败恢复测试。特别是**"5分钟承诺"在极端情况下是否能兑现**这一核心问题，完全没有E2E测试覆盖。

**关键风险**：
- 任务失败后的用户体验完全未测试
- 缓存失效时的性能保证无验证
- 多租户隔离在高并发下可能失效
- SSE降级链条的状态一致性未验证
- JWT过期对长时间任务的影响未知

### 1.2 目标
建立完整的端到端测试体系，验证系统在各种极端情况下的行为：
- **用户旅程完整性**：从注册到报告的全流程验证
- **性能保证可靠性**：5分钟承诺在故障条件下的兑现
- **安全隔离有效性**：多租户数据零泄露保证
- **降级链条正确性**：每个降级方案的实际验证
- **故障恢复能力**：系统在组件失效后的自愈能力
- **LLM 报告可用**：正常任务必须输出 LLM 报告正文；若 C/X 只输出解释页
- **报告结构完整**：报告必须包含“决策卡/概览/战场/痛点/驱动力/机会卡”
- **报告字段口径**：`report.pain_points/opportunities/action_items/purchase_drivers/market_health` 必须存在

### 1.3 非目标
- **不测试**单个函数的逻辑正确性（单元测试负责）
- **不测试**UI的视觉效果（视觉回归测试负责）
- **不测试**第三方服务的可靠性（Mock和合约测试负责）
- **不模拟**超出系统设计范围的极端场景

## 2. 解决方案

### 2.1 核心设计：四层测试金字塔

基于测试金字塔原理，建立端到端测试的层级结构：

```
端到端测试金字塔
├── L4: 业务关键路径测试 (5个核心场景)
├── L3: 组件集成测试 (20个交互场景)  
├── L2: 故障注入测试 (15个失败场景)
└── L1: 性能边界测试 (10个极限场景)
```

**测试哲学**：
- **诚实测试**：测试真实用户场景，不是理想化的happy path
- **故障优先**：重点测试系统在故障条件下的行为
- **数据驱动**：所有测试必须有量化的成功标准
- **可重现**：每个测试都能在任何环境中稳定重现

### 2.2 关键测试场景

#### 场景1：完整用户旅程 (Happy Path)
```python
@pytest.mark.critical
async def test_complete_user_journey():
    """从注册到获得报告的完整用户体验"""
    # 1. 用户注册（30秒内完成）
    user = await register_new_user("test@example.com", "password123")
    assert user.created_at is not None
    
    # 2. 登录获取JWT（1秒内完成）  
    token = await login_user("test@example.com", "password123")
    assert jwt.decode(token)["user_id"] == user.id
    
    # 3. 提交分析任务（200ms内返回task_id）
    start_time = time.time()
    task = await submit_analysis(
        token, 
        "一款AI驱动的项目管理工具，帮助团队提高协作效率"
    )
    response_time = time.time() - start_time
    assert response_time < 0.2  # 200ms承诺
    assert task.status == "pending"
    
    # 4. 等待分析完成（5分钟内完成）
    start_analysis = time.time()
    final_status = await wait_for_completion(task.id, timeout=360)
    analysis_time = time.time() - start_analysis
    assert final_status == "completed"
    assert analysis_time < 300  # 5分钟承诺
    
    # 5. 获取报告（2秒内加载）
    start_report = time.time()
    report = await get_report(token, task.id)
    report_time = time.time() - start_report
    assert report_time < 2  # 2秒承诺
    assert report.data.get("report_html")  # 必须有 LLM 正文
    assert "决策卡片" in report.data.get("report_html", "")
    report_payload = report.data.get("report", {})
    assert "pain_points" in report_payload
    assert "competitors" in report_payload
    assert "opportunities" in report_payload
    assert "action_items" in report_payload
    assert "purchase_drivers" in report_payload
    assert "market_health" in report_payload
    assert report_payload.get("market_health", {}).get("ps_ratio") is not None
```

#### 场景2：缓存失效下的5分钟承诺
```python
@pytest.mark.critical
async def test_5_minute_guarantee_with_cache_failure():
    """Redis完全宕机时能否兑现5分钟承诺"""
    # 1. 破坏缓存系统
    await redis_client.flushall()  # 清空缓存
    await redis_client.connection_pool.disconnect()  # 断开连接
    
    # 2. 提交任务（应该自动降级到API模式）
    user_token = await get_test_user_token()
    task = await submit_analysis(
        user_token,
        "社交媒体管理工具，帮助小企业管理多个平台"
    )
    
    # 3. 验证降级提示
    status = await get_task_status(user_token, task.id)
    assert "降级模式" in status.message or "API直连" in status.message
    
    # 4. 等待完成（应该在10分钟内完成，承认降级成本）
    start_time = time.time()
    final_status = await wait_for_completion(task.id, timeout=600)
    actual_time = time.time() - start_time
    
    # 诚实的期望：降级模式下10分钟是可接受的
    assert final_status == "completed"
    assert actual_time < 600  # 降级模式10分钟承诺
    
    # 5. 验证结果质量（降级模式下质量可能下降，但必须可用）
    report = await get_report(user_token, task.id)
    assert len(report.data["pain_points"]) >= 3  # 至少3个痛点
    assert report.confidence_score >= 0.6  # 降级模式最低质量
```

#### 场景3：多租户并发隔离
```python
@pytest.mark.critical  
async def test_concurrent_multi_tenant_isolation():
    """100个用户同时使用时的数据隔离"""
    # 1. 创建100个测试用户
    users = []
    for i in range(100):
        user = await register_new_user(f"user{i}@test.com", f"pass{i}")
        users.append(user)
    
    # 2. 所有用户同时提交不同的分析任务
    tasks = []
    async with asyncio.TaskGroup() as group:
        for i, user in enumerate(users):
            token = await login_user(user.email, f"pass{i}")
            task = group.create_task(submit_analysis(
                token, 
                f"产品{i}：{generate_unique_product_description(i)}"
            ))
            tasks.append((user.id, task))
    
    # 3. 等待所有任务完成
    completed_tasks = []
    for user_id, task in tasks:
        result = await task
        completed_tasks.append((user_id, result.id))
        await wait_for_completion(result.id)
    
    # 4. 验证数据隔离：每个用户只能看到自己的任务
    for user_id, task_id in completed_tasks:
        # 正确用户可以访问
        user_token = await get_user_token(user_id)
        own_report = await get_report(user_token, task_id)
        assert own_report is not None
        
        # 随机其他用户不能访问（应该返回404）
        other_user_id = random.choice([uid for uid, _ in completed_tasks if uid != user_id])
        other_token = await get_user_token(other_user_id)
        
        with pytest.raises(HTTPException) as exc:
            await get_report(other_token, task_id)
        assert exc.value.status_code == 404  # 不是403，避免信息泄露
```

### 2.3 故障注入测试

#### 现状实现入口（真实代码为准）
- 主要用例：`backend/tests/e2e/test_fault_injection.py`
  - Redis 不可用、DB 慢、worker 崩溃重试、Reddit rate limit 失败升级
- 故障管理器：`backend/tests/utils/fault_injection.py`
- 说明：本节示例为“概念伪代码”，以实际测试文件为准。

#### 真人演练矩阵（生产演练）
- 演练脚本：`scripts/phase106_rehearsal_matrix.py`
- 场景配置：`scripts/phase106_rehearsal_matrix.sample.json`
- 目标：富样本/窄题/必拦截/故障注入可复现，结果可写入 JSON 复核

#### 任务失败恢复测试
```python
@pytest.mark.failure_injection
async def test_task_failure_user_experience():
    """分析引擎崩溃时的用户体验"""
    # 1. 正常提交任务
    user_token = await get_test_user_token()
    task = await submit_analysis(user_token, "测试产品描述")
    
    # 2. 等待任务开始处理
    await wait_for_status(task.id, "processing")
    
    # 3. 故意杀死处理该任务的Worker
    worker_pid = await get_task_worker_pid(task.id)
    os.kill(worker_pid, signal.SIGKILL)
    
    # 4. 验证系统自动重试（3次重试机制）
    retry_count = 0
    while retry_count < 4:  # 原始 + 3次重试
        status = await get_task_status(user_token, task.id)
        if status.status == "processing":
            retry_count += 1
            await asyncio.sleep(60)  # 等待重试间隔
        elif status.status == "completed":
            break
        elif status.status == "failed":
            assert retry_count == 3  # 确认重试了3次
            break
    
    # 5. 如果最终失败，验证用户得到清晰的错误信息
    if status.status == "failed":
        assert "系统繁忙" in status.error_message
        assert "请重新提交" in status.error_message
        assert status.error_message != "Internal Server Error"  # 不要技术性错误
```

#### SSE重连状态一致性
```python
@pytest.mark.failure_injection
async def test_sse_reconnection_consistency():
    """SSE断开重连后的状态一致性"""
    # 1. 建立SSE连接并提交任务
    user_token = await get_test_user_token()
    task = await submit_analysis(user_token, "SSE测试产品")
    
    sse_events = []
    async with sse_client(f"/api/analyze/stream/{task.id}") as sse:
        # 2. 接收几个状态更新
        for i in range(3):
            event = await sse.receive()
            sse_events.append(event.data)
            if "processing" in event.data:
                break
    
    # 3. 强制断开SSE连接（模拟网络问题）
    await sse.close()
    
    # 4. 立即降级到轮询模式
    polling_status = await get_task_status(user_token, task.id)
    
    # 5. 重新建立SSE连接
    async with sse_client(f"/api/analyze/stream/{task.id}") as sse2:
        first_event = await sse2.receive()
        reconnected_status = json.loads(first_event.data)
    
    # 6. 验证状态一致性
    assert polling_status.status == reconnected_status["status"]
    assert polling_status.started_at == reconnected_status["started_at"]
    # 进度只能前进，不能后退
    if polling_status.progress and reconnected_status.get("progress"):
        assert reconnected_status["progress"] >= polling_status.progress
```

### 2.4 性能边界测试

#### 极限并发测试
```python
@pytest.mark.performance
async def test_system_under_extreme_load():
    """系统在极限负载下的表现"""
    # 配置：100并发用户，每用户提交1个任务
    CONCURRENT_USERS = 100
    MAX_RESPONSE_TIME = 5.0  # 最大可接受响应时间
    
    # 1. 准备100个用户账户
    users = await create_test_users(CONCURRENT_USERS)
    
    # 2. 监控系统资源使用
    system_monitor = SystemResourceMonitor()
    system_monitor.start()
    
    # 3. 并发提交任务
    submit_times = []
    tasks = []
    
    async def submit_single_task(user, user_index):
        start_time = time.time()
        try:
            token = await login_user(user.email, f"pass{user_index}")
            task = await submit_analysis(token, f"高并发测试产品{user_index}")
            response_time = time.time() - start_time
            submit_times.append(response_time)
            return task
        except Exception as e:
            submit_times.append(float('inf'))  # 记录失败
            raise
    
    # 4. 并发执行
    async with asyncio.TaskGroup() as group:
        for i, user in enumerate(users):
            task = group.create_task(submit_single_task(user, i))
            tasks.append(task)
    
    # 5. 分析结果
    successful_submits = [t for t in submit_times if t != float('inf')]
    failed_submits = len(submit_times) - len(successful_submits)
    
    # 6. 性能断言
    assert failed_submits <= CONCURRENT_USERS * 0.05  # 最多5%失败率
    assert statistics.median(successful_submits) <= MAX_RESPONSE_TIME
    assert statistics.percentile(successful_submits, 95) <= MAX_RESPONSE_TIME * 2
    
    # 7. 系统资源断言
    max_memory = system_monitor.get_max_memory_usage()
    max_cpu = system_monitor.get_max_cpu_usage() 
    assert max_memory < 2048  # 最大2GB内存
    assert max_cpu < 90  # 最大90% CPU
    
    system_monitor.stop()
```

## 3. 技术规范

### 3.1 测试环境配置

```python
# conftest.py - 测试环境配置
import pytest
import docker
import asyncio
from testcontainers import compose

@pytest.fixture(scope="session")
async def test_environment():
    """完整的测试环境（Docker Compose）"""
    compose_file = """
    version: '3.8'
    services:
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
      
      postgres:
        image: postgres:15-alpine
        environment:
          POSTGRES_DB: reddit_scanner_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      
      app:
        build: .
        environment:
          DATABASE_URL: postgresql://test:test@postgres:5432/reddit_scanner_test
          REDIS_URL: redis://redis:6379
          JWT_SECRET_KEY: test-secret-key-for-testing
          CELERY_WORKER_COUNT: 2
        ports: ["8000:8000"]
        depends_on: [redis, postgres]
      
      worker:
        build: .
        command: celery -A app.celery worker --loglevel=info
        environment:
          DATABASE_URL: postgresql://test:test@postgres:5432/redis_scanner_test
          REDIS_URL: redis://redis:6379
        depends_on: [redis, postgres, app]
    """
    
    with compose.DockerCompose(".", compose_file_content=compose_file) as env:
        # 等待服务启动
        await asyncio.sleep(10)
        
        # 运行数据库迁移
        env.exec_in_container("app", ["alembic", "upgrade", "head"])
        
        yield {
            "app_url": f"http://localhost:{env.get_service_port('app', 8000)}",
            "redis_url": f"redis://localhost:{env.get_service_port('redis', 6379)}",
            "db_url": f"postgresql://test:test@localhost:{env.get_service_port('postgres', 5432)}/reddit_scanner_test"
        }

@pytest.fixture
async def clean_database(test_environment):
    """每个测试前清理数据库"""
    async with get_test_db() as db:
        await db.execute("TRUNCATE users, task, analysis, report CASCADE")
    yield
```

### 3.2 故障注入工具

```python
# backend/tests/utils/fault_injection.py
class FaultInjectionManager:
    """故障注入管理器"""
    
    async def kill_redis(self):
        """模拟Redis宕机"""
        container = docker.from_env().containers.get("redis")
        container.kill()
        return container
    
    async def simulate_network_partition(self, duration=30):
        """模拟网络分区"""
        # 使用iptables阻断特定端口
        subprocess.run([
            "sudo", "iptables", "-A", "INPUT", 
            "-p", "tcp", "--dport", "6379", "-j", "DROP"
        ])
        await asyncio.sleep(duration)
        subprocess.run([
            "sudo", "iptables", "-D", "INPUT",
            "-p", "tcp", "--dport", "6379", "-j", "DROP"
        ])
    
    async def exhaust_db_connections(self):
        """耗尽数据库连接池"""
        connections = []
        try:
            # 创建超过连接池限制的连接
            for _ in range(50):  # 假设连接池最大20
                conn = await asyncpg.connect(TEST_DB_URL)
                connections.append(conn)
        finally:
            for conn in connections:
                await conn.close()
    
    async def fill_redis_memory(self):
        """填满Redis内存"""
        redis_client = redis.Redis.from_url(TEST_REDIS_URL)
        # 写入大量数据直到内存满
        for i in range(100000):
            large_value = "x" * 10000  # 10KB per key
            redis_client.set(f"memory_filler_{i}", large_value)
```

### 3.3 测试数据生成

```python
# tests/utils/data_generators.py
class TestDataGenerator:
    """测试数据生成器"""
    
    def generate_product_descriptions(self, count=100):
        """生成多样化的产品描述"""
        industries = ["AI", "SaaS", "电商", "教育", "医疗", "金融", "游戏"]
        features = ["自动化", "智能", "协作", "管理", "分析", "优化", "安全"]
        targets = ["企业", "个人", "团队", "开发者", "学生", "老师", "医生"]
        
        descriptions = []
        for i in range(count):
            industry = random.choice(industries)
            feature = random.choice(features)  
            target = random.choice(targets)
            
            desc = f"一款面向{target}的{industry}{feature}工具，产品编号{i}"
            descriptions.append(desc)
        
        return descriptions
    
    async def create_test_users(self, count=10):
        """创建测试用户"""
        users = []
        for i in range(count):
            user_data = {
                "email": f"test_user_{i}@example.com",
                "password": f"testpass{i}123"
            }
            user = await register_user(user_data)
            users.append(user)
        return users
    
    def generate_realistic_load_pattern(self):
        """生成真实负载模式"""
        # 模拟一天中的用户活动模式
        hourly_multipliers = [
            0.1, 0.1, 0.1, 0.1, 0.2, 0.3,  # 深夜到清晨
            0.5, 0.8, 1.0, 1.2, 1.5, 1.8,  # 上午高峰
            1.5, 1.0, 0.8, 1.0, 1.3, 1.6,  # 下午
            1.4, 1.0, 0.8, 0.6, 0.4, 0.2   # 晚上
        ]
        
        current_hour = datetime.now().hour
        base_load = 10  # 基础每小时任务数
        return int(base_load * hourly_multipliers[current_hour])
```

## 4. 验收标准

### 4.1 功能要求

**P0级别测试（必须100%通过）**：
- ✅ 完整用户旅程测试：注册→登录→分析→报告
- ✅ 5分钟承诺在正常情况下兑现率≥95%  
- ✅ 多租户数据隔离：0泄露容忍度
- ✅ 任务失败自动重试：3次重试机制验证
- ✅ SSE降级到轮询：状态完全一致

**P1级别测试（必须90%通过）**：
- ✅ 缓存失效时的降级处理：10分钟内完成
- ✅ JWT过期时的任务状态保持
- ✅ 配置热更新对运行任务的影响
- ✅ 100并发用户测试：95%成功率
- ✅ 系统资源使用监控：内存<2GB，CPU<90%

**P2级别测试（必须80%通过）**：
- ✅ 级联故障恢复能力
- ✅ 极限负载测试
- ✅ 黑色星期五场景模拟

### 4.2 性能指标

| 测试场景 | 目标指标 | 测量方法 | 通过标准 |
|---------|---------|----------|----------|
| 任务提交响应 | <200ms | HTTP响应时间 | 95%达标 |
| 5分钟分析承诺 | <300秒 | 任务完成时间 | 95%达标 |
| 降级模式分析 | <600秒 | 缓存失效下完成时间 | 80%达标 |
| 报告加载时间 | <2秒 | 前端加载测量 | 99%达标 |
| SSE重连时间 | <5秒 | 连接重建时间 | 90%达标 |
| 并发处理能力 | 100用户 | 同时在线用户数 | 系统稳定 |

### 4.3 测试覆盖要求

```python
# tests/coverage_requirements.py
COVERAGE_REQUIREMENTS = {
    "critical_paths": {
        "target": 100,  # 关键路径必须100%覆盖
        "paths": [
            "user_registration_flow",
            "analysis_submission_flow", 
            "result_retrieval_flow",
            "multi_tenant_isolation"
        ]
    },
    
    "failure_scenarios": {
        "target": 80,   # 失败场景80%覆盖
        "scenarios": [
            "task_failure_recovery",
            "cache_unavailable_fallback",
            "database_connection_lost",
            "worker_process_crash",
            "sse_connection_drop"
        ]
    },
    
    "performance_limits": {
        "target": 70,   # 性能边界70%覆盖
        "limits": [
            "concurrent_user_load",
            "memory_usage_limits",
            "queue_depth_limits",
            "api_rate_limiting"
        ]
    }
}

def validate_coverage(test_results):
    """验证测试覆盖率是否达标"""
    for category, requirements in COVERAGE_REQUIREMENTS.items():
        actual_coverage = calculate_coverage(test_results, category)
        assert actual_coverage >= requirements["target"], \
            f"{category} coverage {actual_coverage}% below target {requirements['target']}%"
```

## 5. 风险管理

### 5.1 测试环境风险

**风险1：测试环境与生产环境差异**
- **影响**：测试通过但生产失败
- **缓解**：使用Docker保证环境一致性，生产配置参数化
- **降级方案**：在staging环境进行预生产验证

**风险2：测试数据污染**
- **影响**：测试之间相互影响，结果不可信
- **缓解**：每个测试使用独立数据库，测试后自动清理
- **降级方案**：数据库快照回滚机制

**风险3：外部服务依赖**
- **影响**：Reddit API限制影响测试执行
- **缓解**：使用Mock服务，记录真实API响应
- **降级方案**：离线测试模式，使用预录制的数据

### 5.2 测试执行风险

**风险1：测试执行时间过长**
- **影响**：开发反馈周期延长
- **缓解**：并行执行测试，分级测试策略
- **目标**：P0测试<5分钟，完整套件<30分钟

**风险2：测试结果不稳定**
- **影响**：假阳性/假阴性影响开发信心
- **缓解**：重试机制，统计学验证
- **标准**：相同测试连续执行10次，至少9次相同结果

### 5.3 降级方案

**完全降级：手动验证（无脚本）**
```bash
echo "🔍 手动验证关键功能..."

echo "1. 用户注册测试:"
curl -X POST http://localhost:8006/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"manual@test.com","password":"test123"}'

echo "2. 任务提交测试:"
TOKEN=$(curl -s -X POST http://localhost:8006/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"manual@test.com","password":"test123"}' \
  | jq -r '.access_token')

curl -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_description":"手动测试产品"}'

echo "3. 多租户隔离测试:"
# 创建第二个用户，尝试访问第一个用户的数据
```

**部分降级：核心测试优先**
```python
# 当测试环境不稳定时，只运行最关键的测试
@pytest.mark.smoke
class SmokeTests:
    """烟雾测试 - 系统基本可用性"""
    
    def test_system_alive(self):
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
    
    def test_user_can_register(self):
        # 最基本的用户注册功能
        pass
        
    def test_analysis_can_submit(self):
        # 最基本的任务提交功能
        pass
```

---

## 总结

这个端到端测试规范**直面了PRD体系的测试盲点**：

1. **诚实验证**：不再假设"理论上应该工作"，而是用真实场景验证
2. **故障优先**：重点测试系统在故障条件下的行为，而不只是happy path
3. **量化标准**：每个承诺都有可测量的成功标准
4. **分级策略**：P0/P1/P2分级，确保关键功能优先覆盖

**最关键的突破**：我们不再回避"5分钟承诺在Redis宕机时能否兑现"这样的尖锐问题，而是用E2E测试给出明确答案。

正如Linus所说："Theory and practice sometimes clash. Theory loses." 

这套测试规范确保我们的系统承诺不是纸上谈兵，而是经过真实验证的可靠保证。
