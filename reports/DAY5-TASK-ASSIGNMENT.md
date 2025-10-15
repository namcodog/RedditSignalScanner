# Day 5 任务分配与验收文档

> **日期**: 2025-10-11 (Day 5)
> **文档用途**: 任务分配、进度跟踪、验收标准
> **创建时间**: 2025-10-10 18:00
> **责任人**: Lead
> **关键里程碑**: 🚀 **前端正式开始开发,基于真实API!**

---

## 📅 Day 5 总体目标

### Day 4 验收结果回顾
- ✅ **Backend A**: 4个API端点100%完成,MyPy类型检查通过
- ✅ **Backend B**: 任务系统100%完成,Worker运维文档完整
- ✅ **Frontend**: SSE客户端准备就绪,学习完成
- ✅ **质量门禁**: MyPy --strict 0 errors (34 files)

### Day 5 关键产出
根据`docs/2025-10-10-3人并行开发方案.md` (第158-174行):
- ✅ **API文档生成完成**(OpenAPI + Swagger UI)
- ✅ **前端开始开发**:输入页面(基于真实API)
- ✅ **认证系统启动**:注册/登录API开发

### Day 5 里程碑
- ✅ **前端可以开始开发**(基于真实API) - 最重要!
- ✅ API层100%完成并交付文档
- ✅ 为Day 6-9前端全速开发铺平道路

---

## 👨‍💻 Backend A（资深后端）任务清单

### 核心职责
1. **API文档生成与交付** (优先级P0)
2. **API支持与联调** (优先级P0)
3. **开始分析引擎设计** (优先级P1)

### 上午任务 (9:00-12:00) - API交接准备

#### 1️⃣ API文档生成 (1小时) - 优先级P0

**任务描述**:
生成OpenAPI文档并验证Swagger UI可访问性

**执行步骤**:
```bash
# 1. 生成OpenAPI JSON文档
cd backend
python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json

# 2. 启动服务验证Swagger UI
uvicorn app.main:app --reload

# 3. 访问验证
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

**交付物**:
- [ ] OpenAPI JSON文件 (`backend/docs/openapi.json`)
- [ ] Swagger UI可访问 (`http://localhost:8000/docs`)
- [ ] API示例请求/响应文档 (`backend/docs/API_EXAMPLES.md`)

**验收标准**:
- [ ] Swagger UI显示所有4个API端点
- [ ] 每个端点有完整的请求/响应示例
- [ ] Schema定义清晰完整

---

#### 2️⃣ 测试Token生成脚本 (30分钟) - 优先级P0

**任务描述**:
为前端测试生成有效的JWT tokens

**实现代码**:
```python
# backend/scripts/generate_test_token.py
"""
为前端开发生成测试用JWT tokens
使用方法: python scripts/generate_test_token.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# 添加backend到路径
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import create_access_token
from app.core.config import get_settings

settings = get_settings()


def generate_test_tokens():
    """为前端测试生成JWT tokens"""
    test_users = [
        {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "email": "frontend-test@example.com",
            "description": "前端开发测试账号"
        },
        {
            "user_id": "00000000-0000-0000-0000-000000000002",
            "email": "frontend-dev@example.com",
            "description": "前端联调测试账号"
        },
    ]

    print("=" * 60)
    print("🔑 前端开发测试Token生成")
    print("=" * 60)
    print()

    for user in test_users:
        # 生成长期有效token (7天)
        token = create_access_token(
            data={"sub": user["user_id"]},
            expires_delta=timedelta(days=7)
        )

        print(f"📧 用户邮箱: {user['email']}")
        print(f"👤 用户ID: {user['user_id']}")
        print(f"📝 说明: {user['description']}")
        print(f"🎫 Token:")
        print(f"   {token}")
        print()
        print(f"💡 使用方法:")
        print(f"   Authorization: Bearer {token}")
        print()
        print("-" * 60)
        print()

    print("⚠️  注意事项:")
    print("1. Token有效期7天,请在有效期内使用")
    print("2. 生产环境不要使用这些Token")
    print("3. 这些user_id对应的用户需要在数据库中存在")
    print()


if __name__ == "__main__":
    generate_test_tokens()
```

**交付物**:
- [ ] 测试Token生成脚本 (`backend/scripts/generate_test_token.py`)
- [ ] 至少2个有效的测试Token (7天有效期)
- [ ] Token使用说明文档

**验收标准**:
- [ ] 脚本可以正常运行
- [ ] 生成的Token能通过API认证
- [ ] 使用说明清晰完整

---

#### 3️⃣ 9:00-9:30 API交接会 (30分钟) - 优先级P0

**会议目标**:
让Frontend获得所有必要信息,无阻塞开始开发

**会议议程**:

**Part 1: API端点演示 (15分钟)**
```bash
# 演示1: POST /api/analyze - 创建分析任务
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "product_description": "一款AI驱动的笔记应用,帮助研究者自动组织和连接想法"
  }'

# 期望响应:
{
  "task_id": "uuid",
  "status": "pending",
  "created_at": "2025-10-11T09:00:00Z"
}

# 演示2: GET /api/status/{task_id} - 查询任务状态
curl http://localhost:8000/api/status/{task_id} \
  -H "Authorization: Bearer {token}"

# 演示3: GET /api/analyze/stream/{task_id} - SSE实时推送
curl -N http://localhost:8000/api/analyze/stream/{task_id} \
  -H "Authorization: Bearer {token}"

# 演示4: GET /api/report/{task_id} - 获取报告
curl http://localhost:8000/api/report/{task_id} \
  -H "Authorization: Bearer {token}"
```

**Part 2: 文档和Token交付 (5分钟)**
- [ ] 交付OpenAPI文档链接
- [ ] 交付测试Token (2个)
- [ ] 交付API使用示例

**Part 3: 字段定义确认 (5分钟)**
- [ ] 确认前端TypeScript类型定义与后端Schema一致
- [ ] 确认SSE事件格式
- [ ] 确认错误响应格式

**Part 4: Q&A (5分钟)**
- [ ] 回答Frontend问题
- [ ] 确认无阻塞问题

**会议产出**:
- [ ] ✅ Frontend确认API文档清晰
- [ ] ✅ Frontend获得2个测试Token
- [ ] ✅ 前端开始开发无阻塞

---

### 下午任务 (14:00-18:00) - 分析引擎设计

#### 4️⃣ 分析引擎架构设计 (2小时) - 优先级P1

**任务描述**:
基于PRD-03设计分析引擎的完整架构

**参考文档**:
- `docs/PRD/PRD-03-分析引擎.md` (完整阅读)
- 四步分析流水线设计
- 缓存优先架构设计

**设计内容**:

**1. 系统架构图**
```
用户产品描述
    ↓
Step 1: 智能社区发现 (30秒)
    ↓ (关键词提取 → 社区评分 → Top-K选择)
Step 2: 并行数据采集 (120秒)
    ↓ (缓存优先 → API补充 → 数据清洗)
Step 3: 统一信号提取 (90秒)
    ↓ (痛点提取 → 竞品识别 → 机会发现)
Step 4: 智能排序输出 (30秒)
    ↓ (相关性排序 → 报告生成)
最终分析报告
```

**2. 配置文件结构设计**
```yaml
# backend/config/analysis_engine.yml.example
engine:
  version: "1.0"

  # Step 1: 社区发现配置
  community_discovery:
    pool_size: 500
    target_communities:
      min: 10
      default: 20
      max: 30
    cache_thresholds:
      conservative_mode: 0.6
      aggressive_mode: 0.8
    weights:
      description_match: 0.4
      activity_level: 0.3
      quality_score: 0.3

  # Step 2: 数据采集配置
  data_collection:
    concurrency_limit: 10
    timeout_seconds: 30
    retry_attempts: 3
    cache:
      redis_ttl: 3600
      max_posts_per_community: 100

  # Step 3: 信号提取配置
  signal_extraction:
    nlp:
      sentiment_model: "reddit-sentiment-analysis/roberta-base-reddit"
      entity_confidence: 0.8
    keywords:
      pain_indicators: ["frustrated", "annoying", "difficult"]
      opportunity_indicators: ["looking for", "need something"]

  # Step 4: 排序配置
  ranking:
    pain_points:
      frequency_weight: 0.4
      sentiment_weight: 0.3
      quality_weight: 0.3
    output_limits:
      max_pain_points: 10
      max_competitors: 8
      max_opportunities: 6
```

**3. 数据流设计**
```
输入: product_description (str)
    ↓
关键词提取: List[str] (20个关键词)
    ↓
候选社区池: List[Community] (500个社区)
    ↓
Top社区选择: List[Community] (20个社区)
    ↓
并行数据采集: Dict[str, List[Post]] (社区→帖子映射)
    ↓
数据合并清洗: List[Post] (1500+帖子)
    ↓
信号提取: BusinessSignals (痛点/竞品/机会)
    ↓
智能排序: RankedSignals
    ↓
输出: AnalysisReport
```

**交付物**:
- [ ] 分析引擎架构设计文档 (`backend/docs/ANALYSIS_ENGINE_DESIGN.md`)
- [ ] 配置文件模板 (`backend/config/analysis_engine.yml.example`)
- [ ] 数据流图和处理步骤说明

**验收标准**:
- [ ] 文档清晰描述四步流水线
- [ ] 配置文件结构合理,无魔数
- [ ] 数据流设计符合PRD-03要求

---

#### 5️⃣ 社区发现算法原型 (2小时) - 优先级P1

**任务描述**:
实现Step 1社区发现算法的骨架代码

**实现代码**:
```python
# backend/app/services/analysis/community_discovery.py
"""
Step 1: 智能社区发现算法
基于产品描述,从500+社区池中发现最相关的Reddit社区
"""
from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass

from app.schemas.analysis import Community


@dataclass
class KeywordExtractionResult:
    """关键词提取结果"""
    keywords: List[str]
    weights: Dict[str, float]


async def discover_communities(
    product_description: str,
    max_communities: int = 20,
    cache_hit_rate: float = 0.7,
) -> List[Community]:
    """
    智能社区发现算法

    Args:
        product_description: 产品描述文本
        max_communities: 最大返回社区数量
        cache_hit_rate: 当前缓存命中率(用于动态调整社区数量)

    Returns:
        List[Community]: 相关社区列表(按相关性排序)

    Raises:
        ValueError: 产品描述为空或过短
    """
    # 验证输入
    if not product_description or len(product_description) < 10:
        raise ValueError("Product description must be at least 10 characters")

    # Step 1.1: 关键词提取 (TF-IDF)
    keywords = await extract_keywords(product_description, max_keywords=20)

    # Step 1.2: 动态调整社区数量(基于缓存命中率)
    target_communities = _calculate_target_communities(cache_hit_rate)

    # Step 1.3: 候选社区评分
    community_pool = await _load_community_pool()
    scored_communities = await _score_communities(keywords, community_pool)

    # Step 1.4: Top-K选择 + 多样性保证
    selected_communities = _select_diverse_top_k(
        scored_communities,
        k=min(target_communities, max_communities)
    )

    return selected_communities


async def extract_keywords(
    text: str,
    max_keywords: int = 20,
    min_keyword_length: int = 3,
) -> KeywordExtractionResult:
    """
    关键词提取算法 (TF-IDF)

    Args:
        text: 输入文本
        max_keywords: 最大关键词数量
        min_keyword_length: 最小关键词长度

    Returns:
        KeywordExtractionResult: 关键词及其权重
    """
    # TODO: 实现TF-IDF关键词提取
    # 1. 文本预处理(分词、去停用词)
    # 2. 计算TF-IDF分数
    # 3. 选择Top-K关键词
    pass


async def _score_communities(
    keywords: KeywordExtractionResult,
    community_pool: List[Community],
) -> Dict[Community, float]:
    """
    社区相关性评分算法

    评分公式:
    score = description_match * 0.4 + activity_level * 0.3 + quality_score * 0.3

    Args:
        keywords: 提取的关键词
        community_pool: 候选社区池

    Returns:
        Dict[Community, float]: 社区→相关性分数映射
    """
    scores = {}

    for community in community_pool:
        # 描述匹配分数 (40%权重)
        description_score = _calculate_description_match(
            keywords.keywords,
            community.description_keywords
        )

        # 活跃度分数 (30%权重)
        activity_score = min(community.daily_posts / 100, 1.0)

        # 质量指标分数 (30%权重)
        quality_score = min(community.avg_comment_length / 200, 1.0)

        # 综合评分
        total_score = (
            description_score * 0.4 +
            activity_score * 0.3 +
            quality_score * 0.3
        )

        scores[community] = total_score

    return scores


def _calculate_description_match(
    keywords: List[str],
    community_keywords: List[str],
) -> float:
    """
    计算描述匹配分数 (余弦相似度)

    Args:
        keywords: 产品关键词
        community_keywords: 社区关键词

    Returns:
        float: 相似度分数 [0.0, 1.0]
    """
    # TODO: 实现余弦相似度计算
    pass


def _select_diverse_top_k(
    scored_communities: Dict[Community, float],
    k: int,
) -> List[Community]:
    """
    Top-K选择 + 多样性保证

    确保选中的社区来自不同类别,避免重复

    Args:
        scored_communities: 社区评分结果
        k: 选择数量

    Returns:
        List[Community]: 选中的社区列表(按相关性排序)
    """
    # TODO: 实现多样性选择算法
    # 1. 按分数排序
    # 2. 应用多样性约束(同类别不超过5个)
    # 3. 返回Top-K
    pass


def _calculate_target_communities(cache_hit_rate: float) -> int:
    """
    根据缓存命中率动态计算目标社区数量

    策略:
    - 缓存命中率 > 80%: 分析30个社区(积极模式)
    - 缓存命中率 60-80%: 分析20个社区(平衡模式)
    - 缓存命中率 < 60%: 分析10个社区(保守模式)

    Args:
        cache_hit_rate: 当前缓存命中率 [0.0, 1.0]

    Returns:
        int: 目标社区数量
    """
    if cache_hit_rate > 0.8:
        return 30  # 积极模式
    elif cache_hit_rate > 0.6:
        return 20  # 平衡模式
    else:
        return 10  # 保守模式


async def _load_community_pool() -> List[Community]:
    """
    加载候选社区池(500+社区)

    Returns:
        List[Community]: 社区池
    """
    # TODO: 从数据库或配置文件加载社区池
    pass


__all__ = ["discover_communities", "extract_keywords"]
```

**单元测试骨架**:
```python
# backend/tests/services/test_community_discovery.py
"""
社区发现算法单元测试
"""
import pytest
from app.services.analysis.community_discovery import (
    discover_communities,
    extract_keywords,
)


@pytest.mark.asyncio
async def test_discover_communities_basic():
    """测试基本社区发现功能"""
    product_desc = "AI笔记应用,帮助研究者自动组织和连接想法"

    communities = await discover_communities(product_desc, max_communities=20)

    assert len(communities) <= 20
    assert all(c.relevance_score > 0.0 for c in communities)


@pytest.mark.asyncio
async def test_extract_keywords():
    """测试关键词提取"""
    text = "AI-powered note-taking app for researchers"

    result = await extract_keywords(text, max_keywords=10)

    assert len(result.keywords) <= 10
    assert all(len(kw) >= 3 for kw in result.keywords)


@pytest.mark.asyncio
async def test_dynamic_community_adjustment():
    """测试动态社区数量调整"""
    product_desc = "Test product description"

    # 高缓存命中率 → 30个社区
    communities_high = await discover_communities(
        product_desc,
        cache_hit_rate=0.9
    )
    assert len(communities_high) <= 30

    # 低缓存命中率 → 10个社区
    communities_low = await discover_communities(
        product_desc,
        cache_hit_rate=0.5
    )
    assert len(communities_low) <= 10
```

**交付物**:
- [ ] 社区发现算法骨架代码 (`backend/app/services/analysis/community_discovery.py`)
- [ ] 单元测试框架 (`backend/tests/services/test_community_discovery.py`)
- [ ] 算法配置文件 (`backend/config/community_discovery.yml`)

**验收标准**:
- [ ] 代码结构清晰,函数职责明确
- [ ] 类型注解100%完整
- [ ] MyPy --strict通过
- [ ] 单元测试框架搭建完成

---

#### 6️⃣ API联调支持 (持续,全天候) - 优先级P0

**任务描述**:
随时响应Frontend的API调用问题,确保前端开发无阻塞

**响应职责**:
- [ ] 响应Frontend的API调用错误
- [ ] 协助排查CORS配置问题
- [ ] 协助排查认证Token问题
- [ ] 协助排查数据格式不匹配问题
- [ ] 提供API调试建议和示例

**响应时间要求**:
- **P0问题**(阻塞开发): 15分钟内响应
- **P1问题**(影响进度): 1小时内响应
- **P2问题**(不紧急): 当日响应

**常见问题快速参考**:

**问题1: CORS错误**
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**问题2: 401 Unauthorized**
```bash
# 检查Token格式
Authorization: Bearer <token>  # ✅ 正确
Authorization: <token>         # ❌ 错误,缺少Bearer前缀
```

**问题3: SSE连接失败**
```typescript
// 前端需要正确处理SSE
const eventSource = new EventSource(
  `${API_BASE_URL}/api/analyze/stream/${taskId}`,
  { withCredentials: true }  // 如果需要认证
);
```

**验收标准**:
- [ ] Frontend能成功调用所有4个API端点
- [ ] SSE连接建立成功
- [ ] 响应数据格式符合Frontend类型定义
- [ ] 无阻塞性问题遗留

---

### 📊 Backend A 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | OpenAPI文档 | `backend/docs/openapi.json` | Swagger UI可访问✅ |
| 2 | 测试Token脚本 | `backend/scripts/generate_test_token.py` | 生成2个有效Token✅ |
| 3 | API交接会 | - | Frontend无阻塞开始开发✅ |
| 4 | 分析引擎设计 | `backend/docs/ANALYSIS_ENGINE_DESIGN.md` | 架构清晰完整✅ |
| 5 | 社区发现算法 | `backend/app/services/analysis/community_discovery.py` | 骨架代码完成✅ |
| 6 | API联调支持 | - | Frontend调用成功✅ |
| 7 | MyPy检查 | 全部代码 | 0 errors✅ |

**预计完成时间**: 8小时
- API文档生成: 1h
- 测试Token生成: 0.5h
- API交接会: 0.5h
- 分析引擎设计: 2h
- 社区发现算法: 2h
- API联调支持: 2h

---

## 🔧 Backend B（中级后端）任务清单

### 核心职责
1. **开始用户认证系统开发** (优先级P0)
2. **支持Backend A的API联调** (优先级P1)

### 上午任务 (9:00-12:00) - 认证系统设计

#### 1️⃣ JWT认证架构设计 (1小时) - 优先级P0

**任务描述**:
设计完整的JWT认证系统架构

**参考文档**:
- `docs/PRD/PRD-06-用户认证.md` (完整阅读)

**设计内容**:

**1. 认证流程图**
```
用户注册:
输入(邮箱+密码) → 验证格式 → 密码哈希 → 存储User → 返回UserResponse

用户登录:
输入(邮箱+密码) → 查询User → 验证密码 → 生成JWT → 返回TokenResponse

API调用:
请求 → 提取Token → JWT解码验证 → 提取user_id → 查询User → 注入依赖
```

**2. JWT Token结构**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id (UUID)",
    "exp": 1699000000,
    "iat": 1698900000
  },
  "signature": "..."
}
```

**3. 多租户隔离策略**
```python
# 每个API端点都需要验证user_id匹配
@router.get("/status/{task_id}")
async def get_task_status(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),  # 提取user_id
    db: AsyncSession = Depends(get_session),
):
    task = await db.get(Task, task_id)

    # 多租户权限检查
    if str(task.user_id) != payload.sub:
        raise HTTPException(status_code=403, detail="Not authorized")

    return task
```

**交付物**:
- [ ] 认证系统设计文档 (`backend/docs/AUTH_SYSTEM_DESIGN.md`)
- [ ] JWT Schema定义
- [ ] 认证流程图

**验收标准**:
- [ ] 文档清晰描述认证流程
- [ ] JWT结构设计合理
- [ ] 多租户隔离策略明确

---

#### 2️⃣ 用户注册API (2小时) - 优先级P0

**任务描述**:
实现用户注册端点

**实现代码**:
```python
# backend/app/api/routes/auth.py
"""
用户认证相关API端点
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import (
    UserRegisterRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册"
)
async def register_user(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    用户注册端点

    - 验证邮箱格式和密码强度
    - 检查邮箱是否已存在
    - 创建用户记录
    - 返回用户信息(不含密码)

    Raises:
        409: 邮箱已存在
        422: 请求验证失败
    """
    # 1. 检查邮箱是否已存在
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # 2. 密码哈希
    password_hash = get_password_hash(request.password)

    # 3. 创建用户
    new_user = User(
        email=request.email,
        password_hash=password_hash,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 4. 返回用户信息(不含密码)
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        created_at=new_user.created_at,
    )


__all__ = ["router"]
```

**Pydantic Schema定义**:
```python
# backend/app/schemas/user.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="用户密码(8-100字符)"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    """用户响应(不含密码)"""
    id: UUID
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}
```

**单元测试**:
```python
# backend/tests/api/test_auth.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """测试用户注册成功"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "password" not in data  # 不应该返回密码


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """测试重复邮箱注册"""
    # 第一次注册
    await client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "SecurePass123"}
    )

    # 第二次注册相同邮箱
    response = await client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "SecurePass123"}
    )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """测试弱密码验证"""
    response = await client.post(
        "/api/auth/register",
        json={"email": "weak@example.com", "password": "weak"}
    )

    assert response.status_code == 422
```

**交付物**:
- [ ] POST /api/auth/register 端点实现
- [ ] UserRegisterRequest Schema (密码强度验证)
- [ ] UserResponse Schema
- [ ] 错误处理(邮箱已存在409)
- [ ] 单元测试(3个测试用例)

**验收标准**:
- [ ] 端点可访问
- [ ] 密码强度验证正常工作
- [ ] 邮箱重复检查正常工作
- [ ] 返回数据不包含密码
- [ ] MyPy --strict通过
- [ ] 单元测试全部通过

---

### 下午任务 (14:00-18:00) - 登录与Token管理

#### 3️⃣ 用户登录API (2小时) - 优先级P0

**任务描述**:
实现用户登录端点并返回JWT token

**实现代码**:
```python
# backend/app/api/routes/auth.py (继续)
from app.core.security import (
    verify_password,
    create_access_token,
)
from app.schemas.auth import (
    UserLoginRequest,
    TokenResponse,
)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录"
)
async def login_user(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    用户登录端点

    - 验证用户凭证
    - 生成JWT token
    - 返回access_token

    Raises:
        401: 邮箱或密码错误
    """
    # 1. 查询用户
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # 2. 验证用户存在且密码正确
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. 生成JWT token
    access_token = create_access_token(data={"sub": str(user.id)})

    # 4. 返回token
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
        )
    )
```

**Pydantic Schema定义**:
```python
# backend/app/schemas/auth.py
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., description="用户密码")


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: UserResponse = Field(..., description="用户信息")
```

**单元测试**:
```python
# backend/tests/api/test_auth.py (继续)
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """测试用户登录成功"""
    # 先注册用户
    await client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "SecurePass123"}
    )

    # 登录
    response = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "SecurePass123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """测试错误密码登录"""
    # 先注册用户
    await client.post(
        "/api/auth/register",
        json={"email": "wrong@example.com", "password": "SecurePass123"}
    )

    # 使用错误密码登录
    response = await client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass456"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """测试不存在的用户登录"""
    response = await client.post(
        "/api/auth/login",
        json={"email": "notexist@example.com", "password": "SecurePass123"}
    )

    assert response.status_code == 401
```

**交付物**:
- [ ] POST /api/auth/login 端点实现
- [ ] UserLoginRequest Schema
- [ ] TokenResponse Schema
- [ ] 密码验证逻辑
- [ ] JWT token生成
- [ ] 单元测试(3个测试用例)

**验收标准**:
- [ ] 端点可访问
- [ ] 登录成功返回有效Token
- [ ] 错误密码返回401
- [ ] 不存在的用户返回401
- [ ] MyPy --strict通过
- [ ] 单元测试全部通过

---

#### 4️⃣ 权限中间件优化 (1.5小时) - 优先级P1

**任务描述**:
增强JWT验证逻辑和错误处理

**实现代码**:
```python
# backend/app/core/security.py (增强)
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session


settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class TokenPayload(BaseModel):
    """JWT Token Payload"""
    sub: str  # user_id
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None
) -> str:
    """
    创建JWT access token

    Args:
        data: Token载荷数据 (必须包含'sub'字段)
        expires_delta: 过期时间增量 (默认30分钟)

    Returns:
        str: JWT token字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp())
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


async def decode_jwt_token(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
) -> TokenPayload:
    """
    解码并验证JWT token

    Args:
        token: JWT token字符串
        db: 数据库会话

    Returns:
        TokenPayload: Token载荷数据

    Raises:
        HTTPException(401): Token无效、过期或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 解码JWT
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # 构造TokenPayload
        token_data = TokenPayload(
            sub=user_id,
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0),
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    # 验证用户是否存在
    from app.models.user import User
    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception

    return token_data


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


__all__ = [
    "TokenPayload",
    "create_access_token",
    "decode_jwt_token",
    "get_password_hash",
    "verify_password",
]
```

**单元测试**:
```python
# backend/tests/core/test_security.py
import pytest
from datetime import timedelta
import jwt

from app.core.security import (
    create_access_token,
    decode_jwt_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    """测试密码哈希"""
    password = "SecurePass123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPass", hashed) is False


def test_create_access_token():
    """测试JWT token创建"""
    user_id = "test-user-id"
    token = create_access_token(data={"sub": user_id})

    assert isinstance(token, str)
    assert len(token) > 0


def test_token_expiration():
    """测试Token过期"""
    from app.core.config import get_settings
    settings = get_settings()

    # 创建已过期的token
    expired_token = create_access_token(
        data={"sub": "test-user"},
        expires_delta=timedelta(seconds=-1)
    )

    # 尝试解码应该失败
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(
            expired_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
```

**交付物**:
- [ ] 增强的JWT验证逻辑
- [ ] 完善的错误处理(401 Token过期/无效)
- [ ] Token过期自动处理
- [ ] 单元测试(3个测试用例)

**验收标准**:
- [ ] Token验证逻辑正确
- [ ] 过期Token返回明确错误
- [ ] 用户不存在时返回401
- [ ] MyPy --strict通过

---

#### 5️⃣ 认证系统测试 (30分钟) - 优先级P1

**任务描述**:
编写完整的认证系统集成测试

**实现代码**:
```python
# backend/tests/api/test_auth_integration.py
"""
认证系统集成测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient):
    """测试完整认证流程: 注册 → 登录 → 调用受保护API"""

    # 1. 注册新用户
    register_response = await client.post(
        "/api/auth/register",
        json={
            "email": "fullflow@example.com",
            "password": "SecurePass123"
        }
    )
    assert register_response.status_code == 201
    user_data = register_response.json()

    # 2. 登录获取Token
    login_response = await client.post(
        "/api/auth/login",
        json={
            "email": "fullflow@example.com",
            "password": "SecurePass123"
        }
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    access_token = token_data["access_token"]

    # 3. 使用Token调用受保护API
    protected_response = await client.post(
        "/api/analyze",
        json={"product_description": "Test product description for auth"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert protected_response.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_requires_token(client: AsyncClient):
    """测试受保护端点需要Token"""
    response = await client.post(
        "/api/analyze",
        json={"product_description": "Test"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(client: AsyncClient):
    """测试无效Token被拒绝"""
    response = await client.post(
        "/api/analyze",
        json={"product_description": "Test"},
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
```

**交付物**:
- [ ] 至少3个认证集成测试用例
- [ ] 完整认证流程测试(注册→登录→调用API)
- [ ] 测试覆盖率>80%

**验收标准**:
- [ ] 所有测试通过
- [ ] 覆盖主要认证场景
- [ ] 测试代码清晰易读

---

### 📊 Backend B 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | 认证系统设计文档 | `backend/docs/AUTH_SYSTEM_DESIGN.md` | 架构清晰✅ |
| 2 | POST /api/auth/register | `backend/app/api/routes/auth.py` | 端点可用✅ |
| 3 | POST /api/auth/login | `backend/app/api/routes/auth.py` | 返回有效Token✅ |
| 4 | JWT验证中间件 | `backend/app/core/security.py` | 错误处理完善✅ |
| 5 | 认证系统测试 | `backend/tests/api/test_auth.py` | 测试通过✅ |
| 6 | MyPy检查 | 全部代码 | 0 errors✅ |

**预计完成时间**: 8小时
- 认证系统设计: 1h
- 用户注册API: 2h
- 用户登录API: 2h
- 权限中间件优化: 1.5h
- 认证系统测试: 0.5h
- API联调支持: 1h

---

## 🎨 Frontend（全栈前端）任务清单

### 核心职责
1. **参加9:00 API交接会** (优先级P0)
2. **开始输入页面开发** (优先级P0)
3. **API集成测试** (优先级P0)

### 上午任务 (9:00-12:00) - API对接与环境配置

#### 1️⃣ 9:00-9:30 参加API交接会 (30分钟) - 优先级P0

**准备工作** (9:00前完成):
- [ ] 准备API调试工具(Postman/Thunder Client/curl)
- [ ] 准备问题清单
- [ ] 准备类型定义对比文档

**会议记录清单**:
- [ ] 记录API base URL: `http://localhost:8000`
- [ ] 记录测试Token (2个)
- [ ] 记录接口字段变更(如有)
- [ ] 记录CORS配置信息
- [ ] 记录错误响应格式

**会后行动**:
- [ ] 更新环境变量配置
- [ ] 更新TypeScript类型定义(如有变更)
- [ ] 确认无阻塞问题

---

#### 2️⃣ 环境变量配置 (30分钟) - 优先级P0

**任务描述**:
配置前端环境变量,连接后端API

**实现代码**:
```env
# frontend/.env.development
# API配置
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# SSE配置
VITE_SSE_RECONNECT_INTERVAL=3000
VITE_SSE_MAX_RETRIES=5
VITE_SSE_HEARTBEAT_TIMEOUT=30000

# 开发配置
VITE_DEV_MODE=true
VITE_LOG_LEVEL=debug
```

```env
# frontend/.env.example
# API配置
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# SSE配置
VITE_SSE_RECONNECT_INTERVAL=3000
VITE_SSE_MAX_RETRIES=5
VITE_SSE_HEARTBEAT_TIMEOUT=30000
```

**交付物**:
- [ ] `.env.development` 配置完成
- [ ] `.env.example` 模板更新
- [ ] 环境变量使用文档 (`frontend/README.md`更新)

**验收标准**:
- [ ] 环境变量可以正确读取
- [ ] API base URL正确配置

---

#### 3️⃣ API客户端完善 (1小时) - 优先级P0

**任务描述**:
完善API客户端配置,添加请求/响应拦截器

**实现代码**:
```typescript
// frontend/src/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';

/**
 * API客户端配置
 * 统一管理所有HTTP请求
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器
 * 自动添加认证Token
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 开发模式日志
    if (import.meta.env.VITE_DEV_MODE) {
      console.log('[API Request]', config.method?.toUpperCase(), config.url);
    }

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 * 统一错误处理
 */
apiClient.interceptors.response.use(
  (response) => {
    // 开发模式日志
    if (import.meta.env.VITE_DEV_MODE) {
      console.log('[API Response]', response.status, response.config.url);
    }

    return response;
  },
  (error: AxiosError) => {
    // 统一错误处理
    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // Token过期或无效,清除并跳转登录
          console.error('[Auth Error] Token expired or invalid');
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
          break;

        case 403:
          // 无权限
          console.error('[Auth Error] Permission denied');
          break;

        case 404:
          // 资源不存在
          console.error('[API Error] Resource not found');
          break;

        case 409:
          // 冲突(如邮箱已存在)
          console.error('[API Error] Conflict:', data);
          break;

        case 422:
          // 请求验证失败
          console.error('[Validation Error]', data);
          break;

        case 500:
          // 服务器错误
          console.error('[Server Error] Internal server error');
          break;

        default:
          console.error('[API Error]', status, data);
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应(网络错误)
      console.error('[Network Error] No response received');
    } else {
      // 请求配置错误
      console.error('[Request Error]', error.message);
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

**交付物**:
- [ ] 完善的API客户端配置
- [ ] 请求拦截器(自动添加Token)
- [ ] 响应拦截器(统一错误处理)
- [ ] 开发模式日志

**验收标准**:
- [ ] API客户端可以正常请求
- [ ] Token自动添加到请求头
- [ ] 401错误自动跳转登录
- [ ] TypeScript编译0错误

---

#### 4️⃣ API集成测试 (1小时) - 优先级P0

**任务描述**:
验证所有4个API端点可用

**实现代码**:
```typescript
// frontend/src/api/__tests__/integration.test.ts
/**
 * API集成测试
 * 验证前端能成功调用所有后端API
 */
import { describe, it, expect, beforeAll } from 'vitest';
import {
  createAnalysisTask,
  getTaskStatus,
  getAnalysisReport
} from '../analyze.api';

// 使用Backend A提供的测试Token
const TEST_TOKEN = 'eyJ...'; // 从API交接会获得

describe('API Integration Tests', () => {
  beforeAll(() => {
    // 设置测试Token
    localStorage.setItem('auth_token', TEST_TOKEN);
  });

  it('should create analysis task successfully', async () => {
    const response = await createAnalysisTask({
      product_description: 'AI-powered note-taking app for researchers and creators',
    });

    expect(response).toHaveProperty('task_id');
    expect(response).toHaveProperty('status');
    expect(response.status).toBe('pending');

    console.log('✅ POST /api/analyze - Success');
    console.log('   Task ID:', response.task_id);
  });

  it('should get task status successfully', async () => {
    // 先创建任务
    const createResponse = await createAnalysisTask({
      product_description: 'Test product description',
    });

    const taskId = createResponse.task_id;

    // 查询任务状态
    const statusResponse = await getTaskStatus(taskId);

    expect(statusResponse).toHaveProperty('task_id');
    expect(statusResponse).toHaveProperty('status');
    expect(['pending', 'processing', 'completed', 'failed']).toContain(statusResponse.status);

    console.log('✅ GET /api/status/{task_id} - Success');
    console.log('   Status:', statusResponse.status);
  });

  it('should establish SSE connection successfully', async () => {
    // 先创建任务
    const createResponse = await createAnalysisTask({
      product_description: 'Test SSE connection',
    });

    const taskId = createResponse.task_id;

    // 建立SSE连接
    const eventSource = new EventSource(
      `${import.meta.env.VITE_API_BASE_URL}/api/analyze/stream/${taskId}`
    );

    // 等待连接建立
    await new Promise((resolve, reject) => {
      eventSource.onopen = () => {
        console.log('✅ GET /api/analyze/stream/{task_id} - SSE Connected');
        eventSource.close();
        resolve(true);
      };

      eventSource.onerror = (error) => {
        console.error('❌ SSE Connection Failed', error);
        eventSource.close();
        reject(error);
      };

      // 5秒超时
      setTimeout(() => {
        eventSource.close();
        reject(new Error('SSE connection timeout'));
      }, 5000);
    });
  });

  it('should handle API errors correctly', async () => {
    // 测试错误处理: 描述太短
    try {
      await createAnalysisTask({
        product_description: 'short',
      });

      // 不应该执行到这里
      expect(true).toBe(false);

    } catch (error: any) {
      expect(error.response.status).toBe(422);
      console.log('✅ API Error Handling - Success');
      console.log('   422 Validation Error correctly handled');
    }
  });
});
```

**手动测试脚本**:
```bash
# frontend/scripts/test-api.sh
#!/bin/bash

echo "🧪 前端API集成测试"
echo "===================="

# 设置测试Token (从Backend A获得)
export TEST_TOKEN="eyJ..."

echo ""
echo "1️⃣  测试 POST /api/analyze"
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"product_description": "AI笔记应用测试"}' \
  | jq '.'

echo ""
echo "2️⃣  测试 GET /api/status/{task_id}"
# 使用上一步返回的task_id
TASK_ID="..."
curl http://localhost:8000/api/status/$TASK_ID \
  -H "Authorization: Bearer $TEST_TOKEN" \
  | jq '.'

echo ""
echo "3️⃣  测试 SSE连接"
curl -N http://localhost:8000/api/analyze/stream/$TASK_ID \
  -H "Authorization: Bearer $TEST_TOKEN"

echo ""
echo "✅ API集成测试完成"
```

**交付物**:
- [ ] API集成测试用例 (`frontend/src/api/__tests__/integration.test.ts`)
- [ ] 验证所有4个API端点可用
- [ ] 验证SSE连接成功
- [ ] 手动测试脚本 (`frontend/scripts/test-api.sh`)

**验收标准**:
- [ ] 所有API端点测试通过
- [ ] SSE连接测试通过
- [ ] 错误处理测试通过
- [ ] 测试日志清晰

---

### 下午任务 (14:00-18:00) - 输入页面开发

#### 5️⃣ 输入页面UI开发 (2小时) - 优先级P0

**任务描述**:
实现完整的输入页面UI和交互逻辑

**参考文档**:
- `docs/PRD/PRD-05-前端交互.md` (第97-150行)

**实现代码**:
```tsx
// frontend/src/pages/InputPage.tsx
/**
 * 输入页面
 * 用户输入产品描述并启动分析
 */
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { createAnalysisTask } from '@/api';
import type { AnalyzeRequest } from '@/types';
import './InputPage.css';

export const InputPage: React.FC = () => {
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    // 验证输入
    if (!description.trim()) {
      setError('请输入产品描述');
      return;
    }

    if (description.length < 10) {
      setError('产品描述至少需要10个字符');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // 调用API创建分析任务
      const response = await createAnalysisTask({
        product_description: description,
      });

      // 跳转到进度页面
      navigate(`/progress/${response.task_id}`);

    } catch (err: any) {
      console.error('Failed to create analysis task:', err);

      // 错误处理
      if (err.response) {
        const { status, data } = err.response;

        if (status === 422) {
          setError(data.detail || '输入验证失败,请检查产品描述');
        } else if (status === 401) {
          setError('未登录或登录已过期,请重新登录');
        } else {
          setError('提交失败,请稍后重试');
        }
      } else {
        setError('网络错误,请检查网络连接');
      }

    } finally {
      setIsSubmitting(false);
    }
  }, [description, navigate]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setDescription(e.target.value);
    // 清除错误提示
    if (error) {
      setError(null);
    }
  }, [error]);

  return (
    <div className="input-container">
      <header className="input-header">
        <h1>发现你的Reddit商业信号</h1>
        <p className="subtitle">30秒描述,5分钟洞察</p>
      </header>

      <form onSubmit={handleSubmit} className="input-form">
        <div className="textarea-wrapper">
          <textarea
            value={description}
            onChange={handleChange}
            placeholder="描述你的产品或服务。例如:一款帮助研究者和创作者自动组织和连接想法的AI笔记应用。"
            rows={6}
            className="product-input"
            disabled={isSubmitting}
            maxLength={2000}
            aria-label="产品描述输入框"
            aria-invalid={!!error}
            aria-describedby={error ? 'input-error' : undefined}
          />

          <div className="input-footer">
            <span className="char-count">
              {description.length}/2000
            </span>
          </div>
        </div>

        {error && (
          <div id="input-error" className="error-message" role="alert">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || !description.trim()}
          className="analyze-button"
          aria-busy={isSubmitting}
        >
          {isSubmitting ? (
            <>
              <span className="spinner"></span>
              正在提交...
            </>
          ) : (
            '开始分析'
          )}
        </button>
      </form>

      <footer className="input-tips">
        <p>💡 提示: 详细描述你的产品功能和目标用户,将获得更精准的洞察</p>
      </footer>
    </div>
  );
};
```

**交付物**:
- [ ] InputPage组件实现
- [ ] 表单验证(10-2000字符)
- [ ] 错误处理和提示
- [ ] 加载状态显示
- [ ] 可访问性支持(ARIA)

**验收标准**:
- [ ] 页面可以正常渲染
- [ ] 表单验证正常工作
- [ ] 成功调用API并跳转
- [ ] 错误提示清晰友好
- [ ] TypeScript编译0错误

---

#### 6️⃣ 输入页面样式 (1小时) - 优先级P0

**任务描述**:
实现完整的页面样式和响应式设计

**实现代码**:
```css
/* frontend/src/pages/InputPage.css */

.input-container {
  max-width: 600px;
  margin: 100px auto;
  padding: 40px 20px;
  text-align: center;
}

/* Header */
.input-header h1 {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #1a1a1a;
  line-height: 1.2;
}

.subtitle {
  font-size: 16px;
  color: #666;
  margin-bottom: 40px;
}

/* Form */
.input-form {
  width: 100%;
}

.textarea-wrapper {
  position: relative;
  width: 100%;
}

.product-input {
  width: 100%;
  min-height: 150px;
  padding: 16px;
  font-size: 16px;
  line-height: 1.5;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  resize: vertical;
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.product-input:focus {
  outline: none;
  border-color: #0066cc;
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}

.product-input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.product-input[aria-invalid="true"] {
  border-color: #dc3545;
}

/* Input Footer */
.input-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
  padding-right: 4px;
}

.char-count {
  font-size: 14px;
  color: #666;
}

/* Error Message */
.error-message {
  margin: 16px 0;
  padding: 12px 16px;
  background-color: #fee;
  border: 1px solid #fcc;
  border-radius: 6px;
  color: #c33;
  font-size: 14px;
  text-align: left;
}

/* Submit Button */
.analyze-button {
  margin-top: 20px;
  padding: 16px 48px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background-color: #0066cc;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 200px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analyze-button:hover:not(:disabled) {
  background-color: #0052a3;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 102, 204, 0.2);
}

.analyze-button:active:not(:disabled) {
  transform: translateY(0);
}

.analyze-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
  transform: none;
}

/* Spinner */
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Tips */
.input-tips {
  margin-top: 40px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.input-tips p {
  margin: 0;
  font-size: 14px;
  color: #666;
  line-height: 1.5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .input-container {
    margin: 60px auto;
    padding: 20px 16px;
  }

  .input-header h1 {
    font-size: 24px;
  }

  .subtitle {
    font-size: 14px;
  }

  .product-input {
    font-size: 14px;
  }

  .analyze-button {
    width: 100%;
    padding: 14px 24px;
  }
}

@media (min-width: 1366px) {
  .input-container {
    max-width: 700px;
  }
}

@media (min-width: 1920px) {
  .input-container {
    max-width: 800px;
  }

  .input-header h1 {
    font-size: 36px;
  }

  .subtitle {
    font-size: 18px;
  }
}
```

**交付物**:
- [ ] 完整的页面样式
- [ ] 响应式设计(1920x1080, 1366x768, 移动端)
- [ ] 交互动画效果
- [ ] 可访问性样式

**验收标准**:
- [ ] 样式在所有分辨率下正常显示
- [ ] 交互动画流畅自然
- [ ] 颜色对比度符合WCAG标准
- [ ] 样式代码组织清晰

---

#### 7️⃣ 输入页面测试 (1小时) - 优先级P0

**任务描述**:
编写输入页面的单元测试

**实现代码**:
```typescript
// frontend/src/pages/__tests__/InputPage.test.tsx
/**
 * 输入页面单元测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { InputPage } from '../InputPage';
import * as api from '@/api';

// Mock API
vi.mock('@/api');

const renderInputPage = () => {
  return render(
    <BrowserRouter>
      <InputPage />
    </BrowserRouter>
  );
};

describe('InputPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render input form', () => {
    renderInputPage();

    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /开始分析/ })).toBeInTheDocument();
    expect(screen.getByText(/发现你的Reddit商业信号/)).toBeInTheDocument();
  });

  it('should show validation error for empty input', async () => {
    renderInputPage();

    const button = screen.getByRole('button', { name: /开始分析/ });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/请输入产品描述/)).toBeInTheDocument();
    });
  });

  it('should show validation error for short input', async () => {
    renderInputPage();

    const textarea = screen.getByRole('textbox');
    const button = screen.getByRole('button', { name: /开始分析/ });

    fireEvent.change(textarea, { target: { value: 'short' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/至少需要10个字符/)).toBeInTheDocument();
    });
  });

  it('should show character count', () => {
    renderInputPage();

    const textarea = screen.getByRole('textbox');

    fireEvent.change(textarea, { target: { value: 'Test description' } });

    expect(screen.getByText(/16\/2000/)).toBeInTheDocument();
  });

  it('should submit form and navigate on success', async () => {
    const mockCreateTask = vi.spyOn(api, 'createAnalysisTask').mockResolvedValue({
      task_id: 'test-task-id',
      status: 'pending',
      created_at: new Date().toISOString(),
    });

    renderInputPage();

    const textarea = screen.getByRole('textbox');
    const button = screen.getByRole('button', { name: /开始分析/ });

    fireEvent.change(textarea, { target: { value: 'Test product description for analysis' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockCreateTask).toHaveBeenCalledWith({
        product_description: 'Test product description for analysis',
      });
    });
  });

  it('should show error message on API failure', async () => {
    vi.spyOn(api, 'createAnalysisTask').mockRejectedValue({
      response: {
        status: 422,
        data: { detail: 'Validation error' },
      },
    });

    renderInputPage();

    const textarea = screen.getByRole('textbox');
    const button = screen.getByRole('button', { name: /开始分析/ });

    fireEvent.change(textarea, { target: { value: 'Test description' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('should disable button while submitting', async () => {
    vi.spyOn(api, 'createAnalysisTask').mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    renderInputPage();

    const textarea = screen.getByRole('textbox');
    const button = screen.getByRole('button');

    fireEvent.change(textarea, { target: { value: 'Test description' } });
    fireEvent.click(button);

    expect(button).toBeDisabled();
    expect(screen.getByText(/正在提交/)).toBeInTheDocument();
  });
});
```

**交付物**:
- [ ] 输入页面单元测试 (`frontend/src/pages/__tests__/InputPage.test.tsx`)
- [ ] 表单验证测试
- [ ] API调用测试
- [ ] 错误处理测试
- [ ] 测试覆盖率>70%

**验收标准**:
- [ ] 所有测试通过
- [ ] 测试覆盖主要交互场景
- [ ] 测试代码清晰易读

---

### 📊 Frontend 交付清单

| 序号 | 交付物 | 文件位置 | 验收标准 |
|------|-------|---------|---------|
| 1 | API交接会参会 | - | 获得Token和文档✅ |
| 2 | 环境变量配置 | `frontend/.env.development` | 配置完成✅ |
| 3 | API客户端完善 | `frontend/src/api/client.ts` | 拦截器完整✅ |
| 4 | API集成测试 | `frontend/src/api/__tests__/integration.test.ts` | 测试通过✅ |
| 5 | 输入页面UI | `frontend/src/pages/InputPage.tsx` | 功能完整✅ |
| 6 | 输入页面样式 | `frontend/src/pages/InputPage.css` | 响应式设计✅ |
| 7 | 输入页面测试 | `frontend/src/pages/__tests__/InputPage.test.tsx` | 覆盖率>70%✅ |
| 8 | TypeScript检查 | 全部代码 | 0 errors✅ |

**预计完成时间**: 8小时
- API交接会: 0.5h
- 环境变量配置: 0.5h
- API客户端完善: 1h
- API集成测试: 1h
- 输入页面UI: 2h
- 输入页面样式: 1h
- 输入页面测试: 1h
- API联调调试: 1h

---

## 🔗 Day 5 协作节点

### 协作节点 1: 上午9:00 - API交接会 (30分钟)

**参与者**: Backend A + Frontend
**主持人**: Backend A

**议程**:
1. Backend A演示4个API端点 (15分钟)
   - POST /api/analyze - 任务创建
   - GET /api/status/{task_id} - 状态查询
   - GET /api/analyze/stream/{task_id} - SSE实时推送
   - GET /api/report/{task_id} - 报告获取

2. Frontend获取API文档和测试Token (5分钟)
   - OpenAPI文档链接
   - 2个测试Token (7天有效期)
   - API使用示例

3. 确认接口字段定义 (5分钟)
   - TypeScript类型定义与后端Schema对比
   - SSE事件格式确认
   - 错误响应格式确认

4. Q&A (5分钟)
   - 回答Frontend问题
   - 确认无阻塞问题

**产出**:
- ✅ Frontend确认API文档清晰
- ✅ Frontend获得2个测试Token
- ✅ 前端开始开发无阻塞

---

### 协作节点 2: 下午16:00 - API联调检查 (30分钟)

**参与者**: Backend A + Backend B + Frontend
**目标**: 验证Frontend能成功调用所有API

**检查清单**:
- [ ] ✅ Frontend能创建分析任务 (POST /api/analyze)
- [ ] ✅ Frontend能查询任务状态 (GET /api/status/{task_id})
- [ ] ✅ Frontend能建立SSE连接 (GET /api/analyze/stream/{task_id})
- [ ] ✅ Frontend能获取报告 (GET /api/report/{task_id})
- [ ] ✅ CORS配置正确
- [ ] ✅ 认证Token工作正常
- [ ] ✅ 错误响应格式正确

**问题处理**:
- 如有问题,Backend A立即协助排查
- 记录问题和解决方案
- 确保无阻塞问题遗留

---

### 协作节点 3: 晚上18:00 - Day 5验收会 (30分钟)

**参与者**: Backend A + Backend B + Frontend + Lead

**验收清单**:

**Backend A验收**:
- [ ] ✅ OpenAPI文档完整
- [ ] ✅ 测试Token生成脚本可用
- [ ] ✅ 分析引擎设计文档完成
- [ ] ✅ 社区发现算法骨架完成
- [ ] ✅ Frontend能成功调用API

**Backend B验收**:
- [ ] ✅ 认证系统设计文档完成
- [ ] ✅ POST /api/auth/register 可用
- [ ] ✅ POST /api/auth/login 可用并返回有效Token
- [ ] ✅ JWT验证中间件增强完成
- [ ] ✅ 认证系统测试通过

**Frontend验收**:
- [ ] ✅ 输入页面完整实现
- [ ] ✅ API集成测试通过
- [ ] ✅ 能成功调用所有4个API端点
- [ ] ✅ TypeScript编译0错误
- [ ] ✅ 单元测试覆盖率>70%

**质量验收**:
- [ ] ✅ Backend: MyPy --strict 0 errors
- [ ] ✅ Frontend: TypeScript 0 errors
- [ ] ✅ Backend: pytest 所有测试通过
- [ ] ✅ Frontend: vitest 所有测试通过

---

## 📊 Day 5 预期产出

### Backend A
- ✅ OpenAPI文档 + Swagger UI
- ✅ 测试Token生成脚本
- ✅ 分析引擎架构设计文档
- ✅ 社区发现算法骨架代码
- ✅ API联调支持完成

### Backend B
- ✅ POST /api/auth/register
- ✅ POST /api/auth/login
- ✅ 增强的JWT验证中间件
- ✅ 认证系统测试(6+用例)
- ✅ 认证系统设计文档

### Frontend
- ✅ 完整的输入页面(InputPage)
- ✅ API客户端配置完善
- ✅ API集成测试通过
- ✅ 单元测试覆盖率>70%
- ✅ 响应式设计完成

---

## ⏰ Day 5 时间预估

| 角色 | 任务 | 预估时间 |
|------|------|---------|
| **Backend A** | API文档生成 | 1h |
| | 测试Token生成 | 0.5h |
| | API交接会 | 0.5h |
| | 分析引擎设计 | 2h |
| | 社区发现算法 | 2h |
| | API联调支持 | 2h |
| | **Backend A 总计** | **8h** |
| **Backend B** | 认证系统设计 | 1h |
| | 用户注册API | 2h |
| | 用户登录API | 2h |
| | 权限中间件优化 | 1.5h |
| | 认证系统测试 | 0.5h |
| | API联调支持 | 1h |
| | **Backend B 总计** | **8h** |
| **Frontend** | API交接会 | 0.5h |
| | 环境变量配置 | 0.5h |
| | API客户端完善 | 1h |
| | API集成测试 | 1h |
| | 输入页面UI | 2h |
| | 输入页面样式 | 1h |
| | 输入页面测试 | 1h |
| | API联调调试 | 1h |
| | **Frontend 总计** | **8h** |

---

## 🚨 Day 5 风险与缓解

### 风险1: API交接会时间延误
**影响**: Frontend无法按时开始开发
**概率**: 低
**缓解**:
- Backend A 8:30前准备好API文档
- 如交接会延误,先提供文档和Token让Frontend开始
- 准备录制视频演示作为备份

### 风险2: Frontend调用API失败
**影响**: 输入页面无法提交任务
**概率**: 中
**缓解**:
- Backend A全天候待命支持
- 准备详细的API调试指南
- CORS配置提前验证
- 提供Postman Collection作为参考

### 风险3: 认证系统开发延误
**影响**: Backend B任务未完成
**概率**: 低
**缓解**:
- 优先实现注册/登录核心功能
- Token刷新等高级功能可推迟到Day 6
- 使用测试Token让Frontend先开发

### 风险4: 输入页面样式问题
**影响**: UI不符合设计要求
**概率**: 低
**缓解**:
- 参考PRD-05的设计规范
- 实现响应式设计确保兼容性
- 测试多种分辨率

---

## ✅ Day 5 验收标准

### 功能验收
- ✅ Frontend能成功调用4个API端点
- ✅ Frontend输入页面完整实现
- ✅ Backend A分析引擎设计完成
- ✅ Backend B注册/登录API可用

### 质量验收
- ✅ MyPy --strict 0 errors (Backend)
- ✅ TypeScript编译0错误 (Frontend)
- ✅ 测试覆盖率>70% (Frontend)
- ✅ API响应时间<200ms

### 协作验收
- ✅ API交接会顺利完成
- ✅ Frontend无阻塞开始开发
- ✅ 团队协作顺畅
- ✅ 无遗留阻塞问题

---

## 🎯 Day 5 成功标志

**最重要的里程碑**: 🚀 **前端正式开始开发,基于真实API!**

- ✅ Frontend能看到真实的任务创建响应
- ✅ Frontend能看到真实的任务状态
- ✅ Frontend能建立真实的SSE连接
- ✅ Frontend输入页面完整可用
- ✅ 为Day 6-11前端全速开发铺平道路

---

## 📝 每日总结模板

```markdown
### Day 5 总结 (2025-10-11)

**计划任务**:
1. Backend A: API文档生成、分析引擎设计
2. Backend B: 认证系统开发
3. Frontend: 输入页面开发

**实际完成**:
- [ ] Backend A: API文档生成完成
- [ ] Backend A: 分析引擎设计完成
- [ ] Backend B: 注册/登录API完成
- [ ] Frontend: 输入页面完成
- [ ] API交接会顺利完成

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

**明日计划** (Day 6):
1. Backend A: 继续分析引擎开发(Step 1社区发现)
2. Backend B: 完成认证系统测试和优化
3. Frontend: 开始等待页面开发(进度显示+SSE集成)

**风险提示**:
- __
```

---

**Day 5 加油!前端终于可以开始开发了! 🚀**

---

**文档版本**: v1.0
**最后更新**: 2025-10-10 18:00
**维护人**: Lead
**文档路径**: `/Users/hujia/Desktop/RedditSignalScanner/DAY5-TASK-ASSIGNMENT.md`
