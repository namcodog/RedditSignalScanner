# Day 6 任务分配与验收文档

> **日期**: 2025-10-12 (Day 6)
> **文档用途**: 任务分配、进度跟踪、验收标准
> **创建时间**: 2025-10-11 18:00
> **责任人**: Lead
> **关键里程碑**: 🚀 **分析引擎开始实现 + API全面联调!**

---

## 📅 Day 6 总体目标

### Day 5 验收结果回顾
- ✅ **Backend A**: API文档完成,分析引擎设计完成,MyPy 0 errors
- ✅ **Backend B**: 认证系统完成,JWT验证完善,测试100%通过
- ✅ **Frontend**: InputPage完成,TypeScript 0 errors,单元测试100%通过
- ✅ **技术债**: 0 (零技术债)

### Day 6 关键产出
根据`docs/2025-10-10-3人并行开发方案.md` (第176-203行):
- ✅ **分析引擎**: 社区发现算法实现(Step 1)
- ✅ **认证系统**: 完整集成到所有API端点
- ✅ **前端开发**: API联调通过 + ProgressPage开始开发

### Day 6 里程碑
- ✅ **分析引擎第一步完成** - 关键词提取 + 社区发现
- ✅ **API全面联调成功** - Frontend能调用所有端点
- ✅ **ProgressPage开发启动** - 等待页面UI完成

---

## 👨‍💻 Backend A（资深后端）任务清单

### 核心职责
1. **支持Frontend API联调** (优先级P0)
2. **实现TF-IDF关键词提取** (优先级P0)
3. **实现社区发现算法** (优先级P0)

### 上午任务 (9:00-12:00) - API支持与关键词提取

#### 1️⃣ 启动Backend服务支持Frontend联调 (30分钟) - 优先级P0

**任务描述**:
启动后端服务,支持Frontend运行API集成测试

**执行步骤**:
```bash
# 1. 启动PostgreSQL和Redis
docker-compose up -d postgres redis

# 2. 运行数据库迁移
cd backend
alembic upgrade head

# 3. 启动FastAPI服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. 验证服务可访问
curl http://localhost:8000/health
curl http://localhost:8000/docs

# 5. 通知Frontend可以开始联调
```

**验收标准**:
- [ ] Backend服务正常运行
- [ ] Swagger UI可访问
- [ ] Health check返回200
- [ ] Frontend能成功调用API

---

#### 2️⃣ 实现TF-IDF关键词提取算法 (2小时) - 优先级P0

**任务描述**:
基于PRD-03设计,实现关键词提取算法

**参考文档**:
- `docs/PRD/PRD-03-分析引擎.md` (第99-137行)
- `backend/docs/ANALYSIS_ENGINE_DESIGN.md`

**实现代码**:
```python
# backend/app/services/analysis/keyword_extraction.py
"""
关键词提取算法 - TF-IDF实现
基于PRD-03设计
"""
from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re


@dataclass
class KeywordExtractionResult:
    """关键词提取结果"""
    keywords: List[str]
    weights: Dict[str, float]
    total_keywords: int


async def extract_keywords(
    text: str,
    max_keywords: int = 20,
    min_keyword_length: int = 3,
) -> KeywordExtractionResult:
    """
    TF-IDF关键词提取算法

    Args:
        text: 输入文本(产品描述)
        max_keywords: 最大关键词数量
        min_keyword_length: 最小关键词长度

    Returns:
        KeywordExtractionResult: 关键词及其权重

    Raises:
        ValueError: 输入文本为空或过短
    """
    # 1. 验证输入
    if not text or len(text) < 10:
        raise ValueError(
            "Input text must be at least 10 characters long"
        )

    # 2. 文本预处理
    cleaned_text = _preprocess_text(text)

    # 3. TF-IDF计算
    vectorizer = TfidfVectorizer(
        max_features=max_keywords * 2,  # 提取更多候选词
        stop_words='english',
        lowercase=True,
        min_df=1,
        ngram_range=(1, 2),  # 支持单词和双词组合
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([cleaned_text])
        feature_names = vectorizer.get_feature_names_out()

        # 4. 提取关键词和权重
        scores = tfidf_matrix.toarray()[0]
        keyword_scores = [
            (feature_names[i], scores[i])
            for i in range(len(feature_names))
            if len(feature_names[i]) >= min_keyword_length
        ]

        # 5. 按权重排序
        keyword_scores.sort(key=lambda x: x[1], reverse=True)

        # 6. 选择Top-K关键词
        top_keywords = keyword_scores[:max_keywords]

        keywords = [kw for kw, _ in top_keywords]
        weights = {kw: float(score) for kw, score in top_keywords}

        return KeywordExtractionResult(
            keywords=keywords,
            weights=weights,
            total_keywords=len(keywords)
        )

    except Exception as e:
        raise ValueError(f"TF-IDF extraction failed: {e}")


def _preprocess_text(text: str) -> str:
    """
    文本预处理

    - 转小写
    - 移除特殊字符
    - 保留字母、数字和空格
    """
    # 转小写
    text = text.lower()

    # 移除URL
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

    # 移除邮箱
    text = re.sub(r'\S+@\S+', '', text)

    # 保留字母、数字、空格和连字符
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)

    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()

    return text


__all__ = ["extract_keywords", "KeywordExtractionResult"]
```

**单元测试**:
```python
# backend/tests/services/analysis/test_keyword_extraction.py
"""
关键词提取算法单元测试
"""
import pytest
from app.services.analysis.keyword_extraction import (
    extract_keywords,
    KeywordExtractionResult,
)


@pytest.mark.asyncio
async def test_extract_keywords_basic():
    """测试基本关键词提取功能"""
    text = (
        "AI-powered note-taking app for researchers and creators. "
        "Helps automatically organize and connect ideas using "
        "machine learning algorithms."
    )

    result = await extract_keywords(text, max_keywords=10)

    assert isinstance(result, KeywordExtractionResult)
    assert len(result.keywords) <= 10
    assert len(result.keywords) > 0
    assert result.total_keywords == len(result.keywords)

    # 关键词应该包含相关词汇
    keywords_str = ' '.join(result.keywords).lower()
    assert any(word in keywords_str for word in ['ai', 'note', 'research', 'learn'])


@pytest.mark.asyncio
async def test_extract_keywords_with_weights():
    """测试关键词权重计算"""
    text = "machine learning machine learning deep learning AI"

    result = await extract_keywords(text, max_keywords=5)

    # 验证权重字典
    assert len(result.weights) == len(result.keywords)
    assert all(0.0 <= weight <= 1.0 for weight in result.weights.values())

    # "machine learning"应该有最高权重(出现最多)
    top_keyword = result.keywords[0]
    assert "machine" in top_keyword or "learning" in top_keyword


@pytest.mark.asyncio
async def test_extract_keywords_min_length_filter():
    """测试最小长度过滤"""
    text = "AI ML NLP machine learning deep learning algorithms"

    result = await extract_keywords(
        text,
        max_keywords=10,
        min_keyword_length=3
    )

    # 所有关键词长度应该>=3
    assert all(len(kw) >= 3 for kw in result.keywords)


@pytest.mark.asyncio
async def test_extract_keywords_empty_input():
    """测试空输入处理"""
    with pytest.raises(ValueError, match="at least 10 characters"):
        await extract_keywords("")

    with pytest.raises(ValueError, match="at least 10 characters"):
        await extract_keywords("short")


@pytest.mark.asyncio
async def test_extract_keywords_special_characters():
    """测试特殊字符处理"""
    text = (
        "AI-powered! @note-taking #app for $researchers. "
        "Visit https://example.com or email test@example.com"
    )

    result = await extract_keywords(text, max_keywords=5)

    # URL和邮箱应该被移除
    keywords_str = ' '.join(result.keywords)
    assert 'http' not in keywords_str
    assert '@' not in keywords_str
    assert 'example.com' not in keywords_str


@pytest.mark.asyncio
async def test_extract_keywords_bigrams():
    """测试双词组合提取"""
    text = (
        "machine learning is a subset of artificial intelligence. "
        "deep learning is a subset of machine learning."
    )

    result = await extract_keywords(text, max_keywords=10)

    # 应该包含双词组合
    keywords_str = ' '.join(result.keywords)
    # 可能提取到 "machine learning" 或 "deep learning"
    assert any(
        'machine' in kw or 'learning' in kw or 'deep' in kw
        for kw in result.keywords
    )
```

**性能测试**:
```python
# backend/tests/services/analysis/test_keyword_extraction_performance.py
"""
关键词提取性能测试
"""
import pytest
import time
from app.services.analysis.keyword_extraction import extract_keywords


@pytest.mark.asyncio
async def test_keyword_extraction_performance():
    """测试关键词提取性能(<1秒)"""
    text = (
        "AI-powered note-taking app for researchers and creators. " * 10
    )

    start_time = time.time()
    result = await extract_keywords(text, max_keywords=20)
    duration = time.time() - start_time

    assert duration < 1.0, f"Keyword extraction took {duration:.2f}s, expected <1s"
    assert len(result.keywords) > 0
```

**交付物**:
- [ ] `backend/app/services/analysis/keyword_extraction.py` 实现完成
- [ ] 单元测试覆盖率>90%
- [ ] 性能测试通过(<1秒)
- [ ] MyPy --strict 0 errors

**验收标准**:
- [ ] TF-IDF算法正确实现
- [ ] 支持单词和双词组合
- [ ] 正确处理特殊字符
- [ ] 所有测试通过
- [ ] 代码符合类型安全标准

---

### 下午任务 (14:00-18:00) - 社区发现算法

#### 3️⃣ 实现社区发现核心算法 (2.5小时) - 优先级P0

**任务描述**:
实现社区相关性评分、余弦相似度计算、Top-K选择算法

**参考文档**:
- `docs/PRD/PRD-03-分析引擎.md` (第94-173行)

**实现代码** - 请参考单独的开发指南文档:
- 详细实现见 `DAY6-BACKEND-A-GUIDE.md`

**交付物**:
- [ ] `backend/app/services/analysis/community_discovery.py` 完成
- [ ] 社区相关性评分算法实现
- [ ] 余弦相似度计算实现
- [ ] Top-K选择与多样性保证实现
- [ ] 单元测试覆盖率>80%

---

#### 4️⃣ 社区发现算法测试与优化 (1.5小时) - 优先级P0

**任务描述**:
编写完整测试套件并进行性能优化

**测试重点**:
1. 功能测试: 关键词提取 → 社区评分 → Top-K选择
2. 性能测试: 500社区池评分 < 30秒
3. 准确性测试: 相关性分数合理性
4. 边界测试: 空输入、超长输入、特殊字符

**性能优化**:
```python
# 性能测试示例
@pytest.mark.asyncio
async def test_community_discovery_performance():
    """测试社区发现性能(<30秒)"""
    product_desc = "AI笔记应用,帮助研究者自动组织和连接想法"

    start_time = time.time()
    communities = await discover_communities(
        product_desc,
        max_communities=20
    )
    duration = time.time() - start_time

    assert duration < 30.0, f"Discovery took {duration:.2f}s, expected <30s"
    assert len(communities) == 20
    assert all(c.relevance_score > 0.0 for c in communities)
```

**交付物**:
- [ ] 完整单元测试套件
- [ ] 性能测试通过(<30秒)
- [ ] MyPy --strict 0 errors
- [ ] 代码优化完成

---

### 📊 Backend A 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | Backend服务启动 | - | Frontend可联调✅ |
| 2 | TF-IDF实现 | `backend/app/services/analysis/keyword_extraction.py` | 测试覆盖>90%✅ |
| 3 | 社区发现算法 | `backend/app/services/analysis/community_discovery.py` | 性能<30秒✅ |
| 4 | 单元测试 | `backend/tests/services/analysis/` | 覆盖率>80%✅ |
| 5 | MyPy检查 | 全部代码 | 0 errors✅ |

**预计完成时间**: 8小时
- Backend启动支持: 0.5h
- TF-IDF实现: 2h
- 社区发现算法: 2.5h
- 测试与优化: 1.5h
- API联调支持: 1.5h

---

## 🔧 Backend B（中级后端）任务清单

### 核心职责
1. **认证系统与API集成** (优先级P0)
2. **任务系统稳定性测试** (优先级P0)
3. **任务监控接口开发** (优先级P1)

### 上午任务 (9:00-12:00) - 认证集成与文档完善

#### 1️⃣ 认证系统与API集成测试 (1.5小时) - 优先级P0

**任务描述**:
验证JWT认证已正确集成到所有API端点

**测试清单**:
```python
# backend/tests/api/test_auth_integration.py
"""
认证系统API集成测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_api_requires_auth(client: AsyncClient):
    """测试POST /api/analyze需要认证"""
    response = await client.post(
        "/api/analyze",
        json={"product_description": "test"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_analyze_api_with_valid_token(
    client: AsyncClient,
    auth_token: str
):
    """测试带有效Token的API调用"""
    response = await client.post(
        "/api/analyze",
        json={"product_description": "AI笔记应用测试" * 5},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data


@pytest.mark.asyncio
async def test_multi_tenant_isolation(
    client: AsyncClient,
    auth_token_user1: str,
    auth_token_user2: str
):
    """测试多租户数据隔离"""
    # User1创建任务
    response1 = await client.post(
        "/api/analyze",
        json={"product_description": "User1的产品描述" * 3},
        headers={"Authorization": f"Bearer {auth_token_user1}"}
    )
    task_id = response1.json()["task_id"]

    # User2尝试访问User1的任务
    response2 = await client.get(
        f"/api/status/{task_id}",
        headers={"Authorization": f"Bearer {auth_token_user2}"}
    )

    # 应该返回403 Forbidden
    assert response2.status_code == 403
```

**验收标准**:
- [ ] 所有API端点都需要认证
- [ ] 无效Token返回401
- [ ] 跨租户访问返回403
- [ ] 所有测试通过

---

#### 2️⃣ 完善认证系统文档 (1.5小时) - 优先级P0

**任务描述**:
更新AUTH_SYSTEM_DESIGN.md,补充Token刷新策略和使用指南

**文档内容**:
```markdown
# 认证系统设计文档

## Token刷新策略

### 短期Token设计
- 访问Token有效期: 30分钟
- 刷新Token有效期: 7天
- Refresh endpoint: POST /api/auth/refresh

### Token刷新流程
1. 客户端检测Token即将过期(剩余<5分钟)
2. 使用refresh_token调用刷新端点
3. 服务器验证refresh_token有效性
4. 返回新的access_token和refresh_token
5. 客户端更新本地存储

### 安全措施
- Refresh token rotation: 每次刷新生成新token
- 检测refresh token重放攻击
- Token黑名单机制(登出时)

## API认证使用指南

### 前端集成
\`\`\`typescript
// 设置Authorization header
const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
  }
});

// 自动Token刷新
apiClient.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Token过期,尝试刷新
      await refreshToken();
      // 重试原请求
      return apiClient.request(error.config);
    }
    return Promise.reject(error);
  }
);
\`\`\`

### 测试用例
\`\`\`bash
# 1. 注册用户
curl -X POST http://localhost:8000/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email":"test@example.com","password":"SecurePass123"}'

# 2. 登录获取Token
curl -X POST http://localhost:8000/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"test@example.com","password":"SecurePass123"}'

# 3. 使用Token调用API
curl -X POST http://localhost:8000/api/analyze \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"product_description":"测试产品描述"}'
\`\`\`
```

**交付物**:
- [ ] AUTH_SYSTEM_DESIGN.md更新完成
- [ ] Token刷新策略文档完整
- [ ] API使用指南清晰
- [ ] 示例代码可运行

---

### 下午任务 (14:00-18:00) - 任务系统测试与监控

#### 3️⃣ Celery任务系统稳定性测试 (2小时) - 优先级P0

**任务描述**:
全面测试Celery任务系统的稳定性和可靠性

**测试场景**:
```python
# backend/tests/tasks/test_task_reliability.py
"""
任务系统可靠性测试
"""
import pytest
from app.tasks.analysis_task import analyze_task
from app.core.celery_app import celery_app


@pytest.mark.asyncio
async def test_task_retry_on_failure():
    """测试任务失败自动重试"""
    # 模拟任务失败场景
    with mock.patch('app.services.reddit_client.fetch_data') as mock_fetch:
        mock_fetch.side_effect = [
            Exception("Network error"),  # 第1次失败
            Exception("Network error"),  # 第2次失败
            {"data": "success"}          # 第3次成功
        ]

        result = await analyze_task.delay(task_id="test-task")

        # 验证重试了3次
        assert mock_fetch.call_count == 3
        assert result.status == "success"


@pytest.mark.asyncio
async def test_task_max_retries():
    """测试达到最大重试次数后失败"""
    with mock.patch('app.services.reddit_client.fetch_data') as mock_fetch:
        mock_fetch.side_effect = Exception("Permanent error")

        with pytest.raises(Exception):
            await analyze_task.delay(task_id="test-task")

        # 验证重试了3次后放弃
        assert mock_fetch.call_count == 3


@pytest.mark.asyncio
async def test_redis_connection_recovery():
    """测试Redis连接恢复"""
    # 模拟Redis断开
    with mock.patch('redis.Redis.ping') as mock_ping:
        mock_ping.side_effect = [
            Exception("Connection lost"),  # 连接失败
            Exception("Connection lost"),  # 连接失败
            True                           # 连接恢复
        ]

        # 任务应该等待并重试
        result = await analyze_task.delay(task_id="test-task")
        assert result is not None


@pytest.mark.asyncio
async def test_worker_graceful_shutdown():
    """测试Worker优雅关闭"""
    # 启动worker
    worker = celery_app.Worker()
    worker.start()

    # 模拟正在执行的任务
    task = analyze_task.delay(task_id="test-task")

    # 发送关闭信号
    worker.stop()

    # 任务应该完成或重新排队
    assert task.status in ["SUCCESS", "PENDING"]
```

**监控指标**:
```python
# 监控任务队列健康状态
async def check_celery_health():
    """检查Celery健康状态"""
    inspect = celery_app.control.inspect()

    # 检查活跃worker
    active_workers = inspect.active()
    assert len(active_workers) > 0, "No active workers"

    # 检查队列积压
    reserved_tasks = inspect.reserved()
    total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())
    assert total_reserved < 100, f"Too many reserved tasks: {total_reserved}"

    # 检查失败任务
    stats = inspect.stats()
    # 验证失败率 < 5%
```

**交付物**:
- [ ] 任务重试机制测试通过
- [ ] Redis连接恢复测试通过
- [ ] Worker优雅关闭测试通过
- [ ] 健康检查脚本完成

---

#### 4️⃣ 任务监控接口开发 (2小时) - 优先级P1

**任务描述**:
开发任务队列监控API,返回统计信息

**实现代码**:
```python
# backend/app/api/routes/tasks.py
"""
任务监控API端点
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from app.core.celery_app import celery_app
from app.schemas.task import TaskStatsResponse


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "/stats",
    response_model=TaskStatsResponse,
    summary="获取任务队列统计信息"
)
async def get_task_stats() -> TaskStatsResponse:
    """
    获取Celery任务队列统计信息

    返回:
    - 活跃worker数量
    - 队列中的任务数量
    - 正在执行的任务数量
    - 失败任务数量
    """
    inspect = celery_app.control.inspect()

    # 获取活跃worker
    active_workers = inspect.active() or {}

    # 获取保留任务
    reserved_tasks = inspect.reserved() or {}

    # 获取调度任务
    scheduled_tasks = inspect.scheduled() or {}

    # 计算统计数据
    total_active_tasks = sum(
        len(tasks) for tasks in active_workers.values()
    )
    total_reserved_tasks = sum(
        len(tasks) for tasks in reserved_tasks.values()
    )
    total_scheduled_tasks = sum(
        len(tasks) for tasks in scheduled_tasks.values()
    )

    return TaskStatsResponse(
        active_workers=len(active_workers),
        active_tasks=total_active_tasks,
        reserved_tasks=total_reserved_tasks,
        scheduled_tasks=total_scheduled_tasks,
        total_tasks=total_active_tasks + total_reserved_tasks + total_scheduled_tasks
    )
```

**Schema定义**:
```python
# backend/app/schemas/task.py
from pydantic import BaseModel, Field


class TaskStatsResponse(BaseModel):
    """任务统计响应"""
    active_workers: int = Field(..., description="活跃worker数量")
    active_tasks: int = Field(..., description="正在执行的任务数")
    reserved_tasks: int = Field(..., description="已保留的任务数")
    scheduled_tasks: int = Field(..., description="已调度的任务数")
    total_tasks: int = Field(..., description="总任务数")
```

**测试**:
```python
# backend/tests/api/test_task_stats.py
@pytest.mark.asyncio
async def test_get_task_stats(client: AsyncClient):
    """测试获取任务统计"""
    response = await client.get("/api/tasks/stats")

    assert response.status_code == 200
    data = response.json()

    assert "active_workers" in data
    assert "active_tasks" in data
    assert "total_tasks" in data
    assert data["active_workers"] >= 0
```

**交付物**:
- [ ] GET /api/tasks/stats 实现完成
- [ ] TaskStatsResponse Schema定义
- [ ] 单元测试通过
- [ ] API文档更新

---

### 📊 Backend B 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | 认证集成测试 | `backend/tests/api/test_auth_integration.py` | 测试通过✅ |
| 2 | 认证系统文档 | `backend/docs/AUTH_SYSTEM_DESIGN.md` | 文档完整✅ |
| 3 | 任务稳定性测试 | `backend/tests/tasks/test_task_reliability.py` | 测试通过✅ |
| 4 | 任务监控接口 | `backend/app/api/routes/tasks.py` | API可用✅ |
| 5 | MyPy检查 | 全部代码 | 0 errors✅ |

**预计完成时间**: 7小时
- 认证集成测试: 1.5h
- 认证系统文档: 1.5h
- 任务稳定性测试: 2h
- 任务监控接口: 2h

---

## 🎨 Frontend（全栈前端）任务清单

### 核心职责
1. **API集成测试联调** (优先级P0)
2. **修复React测试警告** (优先级P2)
3. **ProgressPage开发** (优先级P0)

### 上午任务 (9:00-12:00) - API联调与测试优化

#### 1️⃣ API集成测试联调 (1小时) - 优先级P0

**任务描述**:
启动后端服务,运行集成测试,验证所有API调用成功

**执行步骤**:
```bash
# 1. 确认Backend服务运行
curl http://localhost:8000/health

# 2. 运行集成测试
cd frontend
npm test -- integration.test.ts

# 3. 预期结果: 8/8 tests passed
```

**问题排查**:
```typescript
// 常见问题1: CORS错误
// 解决: 检查backend的CORS配置

// 常见问题2: 401 Unauthorized
// 解决: 检查测试Token是否有效

// 常见问题3: 网络超时
// 解决: 增加timeout配置
```

**验收标准**:
- [ ] 8/8 集成测试通过
- [ ] POST /api/analyze 成功
- [ ] GET /api/status/{task_id} 成功
- [ ] SSE连接建立成功
- [ ] GET /api/report/{task_id} 成功

---

#### 2️⃣ 修复React act()警告 (1小时) - 优先级P2

**任务描述**:
修复InputPage测试中的React act()警告

**修复方案**:
```typescript
// frontend/src/pages/__tests__/InputPage.test.tsx

// 修复前:
fireEvent.change(textarea, { target: { value: 'test' } });
expect(submitButton).not.toBeDisabled();

// 修复后:
fireEvent.change(textarea, { target: { value: 'test' } });
await waitFor(() => {
  expect(submitButton).not.toBeDisabled();
});
```

**完整示例**:
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

it('should enable submit button after typing', async () => {
  const user = userEvent.setup();
  render(<InputPage />);

  const textarea = screen.getByRole('textbox', { name: /产品描述/i });
  const button = screen.getByRole('button', { name: /开始分析/i });

  // 使用userEvent代替fireEvent
  await user.type(textarea, 'AI笔记应用测试产品描述');

  // 等待状态更新
  await waitFor(() => {
    expect(button).not.toBeDisabled();
  });
});
```

**交付物**:
- [ ] 所有act()警告修复
- [ ] 测试仍然100%通过
- [ ] 使用userEvent替代fireEvent

---

#### 3️⃣ ProgressPage组件设计 (1小时) - 优先级P0

**任务描述**:
设计ProgressPage页面布局和状态管理

**设计要点**:
```typescript
// frontend/src/pages/ProgressPage.tsx

interface ProgressPageState {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;  // 0-100
  currentStep: string;
  estimatedTime: number;  // 剩余秒数
  error: string | null;
}

interface SSEEvent {
  event: 'connected' | 'progress' | 'completed' | 'error';
  data: {
    percentage?: number;
    step?: string;
    message?: string;
  };
}
```

**页面布局**:
```
┌─────────────────────────────────┐
│        正在分析中...             │
│                                 │
│  ████████████░░░░░░░░  60%      │
│                                 │
│  当前步骤: 正在提取商业信号      │
│  预计剩余: 1分30秒               │
│                                 │
│  ✓ 智能社区发现 (已完成)         │
│  ⟳ 统一信号提取 (进行中)         │
│  ○ 智能排序输出 (等待中)         │
│                                 │
│      [取消分析] [切换到轮询]     │
└─────────────────────────────────┘
```

**交付物**:
- [ ] ProgressPage组件结构设计
- [ ] 状态管理接口定义
- [ ] SSE事件类型定义
- [ ] 页面布局mockup

---

### 下午任务 (14:00-18:00) - ProgressPage实现

#### 4️⃣ ProgressPage UI开发 (2小时) - 优先级P0

**实现代码** - 请参考单独的开发指南文档:
- 详细实现见 `DAY6-FRONTEND-GUIDE.md`

**交付物**:
- [ ] ProgressPage组件实现
- [ ] 进度条组件
- [ ] 状态展示组件
- [ ] 错误处理UI
- [ ] 响应式设计

---

#### 5️⃣ SSE客户端集成 (2小时) - 优先级P0

**任务描述**:
实现SSE客户端,处理实时进度更新

**实现重点**:
1. EventSource连接管理
2. 事件处理和状态更新
3. 自动重连机制
4. 错误处理和降级

**详细实现** - 请参考单独的开发指南文档:
- 详细实现见 `DAY6-FRONTEND-GUIDE.md`

**交付物**:
- [ ] SSE客户端实现
- [ ] 实时进度更新
- [ ] 自动重连机制
- [ ] 降级到轮询
- [ ] 单元测试覆盖

---

### 📊 Frontend 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | API集成测试 | `frontend/src/api/__tests__/integration.test.ts` | 8/8通过✅ |
| 2 | React警告修复 | `frontend/src/pages/__tests__/InputPage.test.tsx` | 无警告✅ |
| 3 | ProgressPage UI | `frontend/src/pages/ProgressPage.tsx` | 功能完整✅ |
| 4 | SSE客户端 | `frontend/src/services/sse.service.ts` | 实时更新✅ |
| 5 | TypeScript检查 | 全部代码 | 0 errors✅ |

**预计完成时间**: 7小时
- API集成测试: 1h
- React警告修复: 1h
- ProgressPage设计: 1h
- ProgressPage UI: 2h
- SSE客户端集成: 2h

---

## 🔗 Day 6 协作节点

### 节点1: 上午9:00 - Backend启动确认会 (15分钟)

**参与者**: Backend A + Frontend
**主持人**: Backend A

**议程**:
1. Backend A启动服务并确认可访问 (5分钟)
2. Frontend确认API端点正常 (5分钟)
3. 同步联调计划和注意事项 (5分钟)

**产出**:
- ✅ Backend服务正常运行
- ✅ Frontend可以开始集成测试
- ✅ 无阻塞问题

---

### 节点2: 上午10:00 - API联调检查 (15分钟)

**参与者**: Backend A + Frontend

**检查清单**:
- [ ] Frontend集成测试运行结果如何?
- [ ] 是否有CORS或认证问题?
- [ ] SSE连接是否正常建立?
- [ ] 需要Backend A协助解决什么问题?

**问题处理**:
- 发现问题立即记录
- Backend A优先解决阻塞问题
- 15分钟内必须给出解决方案或workaround

---

### 节点3: 下午16:00 - 进度同步会 (30分钟)

**参与者**: Backend A + Backend B + Frontend + Lead

**汇报内容**:
1. **Backend A**: TF-IDF和社区发现算法进度
2. **Backend B**: 认证集成和任务监控进度
3. **Frontend**: API联调结果和ProgressPage进度
4. **Lead**: 识别风险和协调资源

**决策事项**:
- 是否需要调整任务优先级?
- 是否需要其他角色协助?
- 晚上验收标准是否需要调整?

---

### 节点4: 晚上18:00 - Day 6验收会 (30分钟)

**参与者**: 全员 + Lead

**验收清单**:

**Backend A验收**:
- [ ] TF-IDF关键词提取实现完成
- [ ] 社区发现算法实现完成
- [ ] 单元测试覆盖率>80%
- [ ] MyPy --strict 0 errors
- [ ] 性能测试通过(<30秒)

**Backend B验收**:
- [ ] 认证系统100%集成
- [ ] 任务系统稳定性测试通过
- [ ] 任务监控接口实现完成
- [ ] MyPy --strict 0 errors
- [ ] 文档完整

**Frontend验收**:
- [ ] API集成测试8/8通过
- [ ] ProgressPage组件完成
- [ ] SSE客户端正常工作
- [ ] TypeScript编译0错误
- [ ] 单元测试覆盖率>70%

**质量验收**:
- [ ] Backend MyPy --strict: 0 errors
- [ ] Frontend TypeScript: 0 errors
- [ ] 所有单元测试通过
- [ ] 无新增技术债

---

## 📊 Day 6 预期产出

### Backend A
- ✅ TF-IDF关键词提取算法实现
- ✅ 社区发现算法实现
- ✅ 单元测试覆盖率>80%
- ✅ 性能测试通过(<30秒)
- ✅ MyPy --strict 0 errors

### Backend B
- ✅ 认证系统100%集成到API
- ✅ 任务系统稳定性测试完成
- ✅ 任务监控接口实现
- ✅ AUTH_SYSTEM_DESIGN.md更新
- ✅ MyPy --strict 0 errors

### Frontend
- ✅ API集成测试8/8通过
- ✅ ProgressPage组件完整实现
- ✅ SSE客户端正常工作
- ✅ React测试警告修复
- ✅ TypeScript 0 errors

---

## ⏰ Day 6 时间预估

| 角色 | 任务 | 预估时间 |
|------|------|---------|
| **Backend A** | Backend启动支持 | 0.5h |
| | TF-IDF实现 | 2h |
| | 社区发现算法 | 2.5h |
| | 测试与优化 | 1.5h |
| | API联调支持 | 1.5h |
| | **Backend A 总计** | **8h** |
| **Backend B** | 认证集成测试 | 1.5h |
| | 认证系统文档 | 1.5h |
| | 任务稳定性测试 | 2h |
| | 任务监控接口 | 2h |
| | **Backend B 总计** | **7h** |
| **Frontend** | API集成测试 | 1h |
| | React警告修复 | 1h |
| | ProgressPage设计 | 1h |
| | ProgressPage UI | 2h |
| | SSE客户端集成 | 2h |
| | **Frontend 总计** | **7h** |

---

## 🚨 Day 6 风险与缓解

### 风险1: API集成测试失败

**影响**: Frontend无法继续开发ProgressPage
**概率**: 中
**缓解**:
- Backend A上午优先支持Frontend联调
- 准备详细的API调试指南
- CORS配置提前验证
- 预留1小时问题排查时间

**应急方案**:
- 使用Mock API让Frontend先开发UI
- Backend A和Frontend pair debugging
- 必要时延后ProgressPage开发到Day 7

---

### 风险2: TF-IDF实现复杂度超预期

**影响**: 社区发现算法开发时间不足
**概率**: 低
**缓解**:
- 使用成熟的scikit-learn库
- 提前准备单元测试数据
- 简化初版实现,后续优化

**应急方案**:
- 降级到简单的词频统计算法
- 硬编码测试数据先让流程跑通
- 社区发现算法延后到Day 7完成

---

### 风险3: SSE连接不稳定

**影响**: ProgressPage实时进度显示失败
**概率**: 中
**缓解**:
- 实现完整的自动重连机制
- 测试多种网络环境(弱网、断网)
- 准备轮询降级方案

**应急方案**:
- 优先实现轮询方案
- SSE作为渐进增强功能
- 用户可以手动切换SSE/轮询模式

---

### 风险4: 任务系统稳定性问题

**影响**: Backend B任务完成延迟
**概率**: 低
**缓解**:
- 使用成熟的Celery框架
- 完整的错误处理和重试机制
- 详细的监控和日志

**应急方案**:
- 简化重试逻辑
- 降低测试复杂度
- 优先保证核心功能可用

---

## ✅ Day 6 验收标准

### 功能验收
- ✅ Backend A: TF-IDF + 社区发现算法完成
- ✅ Backend B: 认证集成 + 任务监控完成
- ✅ Frontend: API联调通过 + ProgressPage完成
- ✅ 分析引擎Step 1完成

### 质量验收
- ✅ MyPy --strict 0 errors (Backend)
- ✅ TypeScript编译0错误 (Frontend)
- ✅ 单元测试覆盖率: Backend>80%, Frontend>70%
- ✅ 性能测试: 社区发现<30秒

### 协作验收
- ✅ API联调顺利完成
- ✅ 团队协作顺畅
- ✅ 无遗留阻塞问题
- ✅ 文档同步更新

---

## 🎯 Day 6 成功标志

**最重要的里程碑**: 🚀 **分析引擎第一步完成 + Frontend进入全速开发!**

- ✅ TF-IDF关键词提取算法可用
- ✅ 社区发现算法可以发现相关社区
- ✅ Frontend能看到实时的分析进度
- ✅ ProgressPage实时显示SSE事件
- ✅ 为Day 7-9分析引擎完整实现铺平道路

---

## 📝 每日总结模板

```markdown
### Day 6 总结 (2025-10-12)

**计划任务**:
1. Backend A: TF-IDF实现 + 社区发现算法
2. Backend B: 认证集成 + 任务监控
3. Frontend: API联调 + ProgressPage开发

**实际完成**:
- [ ] Backend A: TF-IDF实现完成
- [ ] Backend A: 社区发现算法完成
- [ ] Backend B: 认证集成完成
- [ ] Backend B: 任务监控接口完成
- [ ] Frontend: API联调通过
- [ ] Frontend: ProgressPage完成

**代码统计**:
- Backend新增文件: __个
- Backend代码行数: __行
- Frontend新增文件: __个
- Frontend代码行数: __行

**质量指标**:
- Backend MyPy: ✅/❌
- Frontend TypeScript: ✅/❌
- Backend测试通过率: ___%
- Frontend测试覆盖率: ___%

**遇到问题**:
1. 问题描述
   - 解决方案
   - 用时: __小时

**明日计划** (Day 7):
1. Backend A: 数据采集模块开发(Step 2)
2. Backend B: Admin后台API开发
3. Frontend: ProgressPage优化 + 报告页面准备

**风险提示**:
- __
```

---

## 📚 相关文档

### 核心PRD文档
- `docs/PRD/PRD-03-分析引擎.md` - 分析引擎完整设计
- `docs/PRD/PRD-02-API设计.md` - API规范
- `docs/PRD/PRD-05-前端交互.md` - 前端设计

### 项目文档
- `docs/2025-10-10-3人并行开发方案.md` - 并行开发计划
- `docs/2025-10-10-实施检查清单.md` - 每日检查清单

### Backend文档
- `backend/docs/ANALYSIS_ENGINE_DESIGN.md` - 分析引擎设计
- `backend/docs/AUTH_SYSTEM_DESIGN.md` - 认证系统设计
- `backend/docs/API_EXAMPLES.md` - API使用示例

### Day 5文档
- `DAY5-TASK-ASSIGNMENT.md` - Day 5任务分配
- `reports/phase-log/DAY5-ZERO-DEBT-ACCEPTANCE-REPORT.md` - Day 5验收报告

---

**Day 6 加油! 分析引擎第一步即将完成! 🚀**

---

**文档版本**: v1.0
**最后更新**: 2025-10-11 18:00
**维护人**: Lead
**文档路径**: `/Users/hujia/Desktop/RedditSignalScanner/DAY6-TASK-ASSIGNMENT.md`
