# Day 6 Backend A 开发指南

> **角色**: Backend Agent A (资深后端)
> **日期**: 2025-10-12 (Day 6)
> **核心任务**: 实现分析引擎Step 1 - 社区发现算法
> **预计用时**: 8小时

---

## 🎯 今日目标

1. ✅ 启动Backend服务支持Frontend联调
2. ✅ 实现TF-IDF关键词提取算法
3. ✅ 实现社区发现核心算法
4. ✅ 完成单元测试与性能优化
5. ✅ MyPy --strict 0 errors

---

## 📋 详细任务清单

### 上午任务 (9:00-12:00)

#### ✅ 任务1: 启动Backend服务 (9:00-9:30, 30分钟)

**目标**: 支持Frontend进行API集成测试

**执行步骤**:

```bash
# 1. 启动依赖服务
cd /Users/hujia/Desktop/RedditSignalScanner
docker-compose up -d postgres redis

# 2. 确认服务运行
docker-compose ps

# 3. 运行数据库迁移
cd backend
source ../venv/bin/activate
alembic upgrade head

# 4. 启动FastAPI服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 新终端验证服务
curl http://localhost:8000/health
# 期望: {"status": "healthy"}

curl http://localhost:8000/docs
# 期望: 返回Swagger UI HTML

# 6. 生成测试Token(如需要)
python scripts/generate_test_token.py
```

**验收标准**:
- [ ] Docker容器正常运行
- [ ] 数据库迁移成功
- [ ] FastAPI服务启动无错误
- [ ] /health端点返回200
- [ ] /docs可访问

**通知Frontend**:
```
✅ Backend服务已启动
- 服务地址: http://localhost:8000
- Swagger文档: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- 测试Token已准备好,可以开始集成测试
```

---

#### ✅ 任务2: 实现TF-IDF关键词提取 (9:30-11:30, 2小时)

**目标**: 实现高质量的关键词提取算法

**2.1 安装依赖** (5分钟)

```bash
# 添加scikit-learn到requirements.txt
echo "scikit-learn==1.3.2" >> backend/requirements.txt

# 安装依赖
pip install scikit-learn==1.3.2
```

**2.2 创建模块文件** (5分钟)

```bash
# 创建analysis服务目录
mkdir -p backend/app/services/analysis
touch backend/app/services/analysis/__init__.py

# 创建关键词提取模块
touch backend/app/services/analysis/keyword_extraction.py

# 创建测试目录
mkdir -p backend/tests/services/analysis
touch backend/tests/services/analysis/__init__.py
touch backend/tests/services/analysis/test_keyword_extraction.py
```

**2.3 实现关键词提取算法** (40分钟)

```python
# backend/app/services/analysis/keyword_extraction.py
"""
关键词提取算法 - TF-IDF实现
基于PRD-03 § 3.1设计
"""
from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass
import re

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


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

    算法步骤:
    1. 文本预处理(清洗特殊字符、URL、邮箱)
    2. TF-IDF向量化(支持1-2 gram)
    3. 提取Top-K关键词
    4. 过滤短词(<3字符)

    Args:
        text: 输入文本(产品描述)
        max_keywords: 最大关键词数量
        min_keyword_length: 最小关键词长度

    Returns:
        KeywordExtractionResult: 关键词及其权重

    Raises:
        ValueError: 输入文本为空或过短

    示例:
        >>> result = await extract_keywords(
        ...     "AI-powered note-taking app for researchers",
        ...     max_keywords=5
        ... )
        >>> print(result.keywords)
        ['ai powered', 'note taking', 'researchers', 'app']
    """
    # 1. 输入验证
    if not text or len(text) < 10:
        raise ValueError(
            f"Input text must be at least 10 characters long, got {len(text)}"
        )

    # 2. 文本预处理
    cleaned_text = _preprocess_text(text)

    if not cleaned_text or len(cleaned_text) < 10:
        raise ValueError(
            "Text became too short after preprocessing"
        )

    # 3. TF-IDF计算
    vectorizer = TfidfVectorizer(
        max_features=max_keywords * 2,  # 提取更多候选词
        stop_words='english',
        lowercase=True,
        min_df=1,
        ngram_range=(1, 2),  # 单词 + 双词组合
        token_pattern=r'(?u)\b[a-z]{2,}\b',  # 只保留字母,最少2字符
    )

    try:
        # 拟合并转换
        tfidf_matrix = vectorizer.fit_transform([cleaned_text])
        feature_names = vectorizer.get_feature_names_out()

        # 4. 提取关键词和权重
        scores = tfidf_matrix.toarray()[0]

        # 过滤短关键词
        keyword_scores = [
            (feature_names[i], scores[i])
            for i in range(len(feature_names))
            if len(feature_names[i]) >= min_keyword_length
        ]

        # 5. 按权重排序
        keyword_scores.sort(key=lambda x: x[1], reverse=True)

        # 6. 选择Top-K关键词
        top_keywords = keyword_scores[:max_keywords]

        if not top_keywords:
            raise ValueError(
                "No keywords extracted. Text may be too short or contain only stop words."
            )

        keywords = [kw for kw, _ in top_keywords]
        weights = {kw: float(score) for kw, score in top_keywords}

        return KeywordExtractionResult(
            keywords=keywords,
            weights=weights,
            total_keywords=len(keywords)
        )

    except Exception as e:
        raise ValueError(f"TF-IDF extraction failed: {str(e)}")


def _preprocess_text(text: str) -> str:
    """
    文本预处理

    处理步骤:
    1. 转小写
    2. 移除URL
    3. 移除邮箱
    4. 移除特殊字符(保留字母、数字、空格、连字符)
    5. 规范化空格

    Args:
        text: 原始文本

    Returns:
        str: 清洗后的文本

    示例:
        >>> _preprocess_text("Check out https://example.com!")
        'check out'
    """
    # 转小写
    text = text.lower()

    # 移除URL (http/https)
    text = re.sub(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        '',
        text
    )

    # 移除邮箱
    text = re.sub(r'\S+@\S+', '', text)

    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)

    # 保留字母、数字、空格和连字符
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)

    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()

    return text


__all__ = ["extract_keywords", "KeywordExtractionResult"]
```

**2.4 编写单元测试** (50分钟)

```python
# backend/tests/services/analysis/test_keyword_extraction.py
"""
关键词提取算法单元测试
覆盖率目标: >90%
"""
import pytest
from app.services.analysis.keyword_extraction import (
    extract_keywords,
    KeywordExtractionResult,
    _preprocess_text,
)


class TestExtractKeywords:
    """关键词提取功能测试"""

    @pytest.mark.asyncio
    async def test_basic_extraction(self):
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

        # 验证返回的是关键词(包含相关词汇)
        keywords_str = ' '.join(result.keywords).lower()
        relevant_words = ['ai', 'note', 'research', 'learn', 'app', 'machine']
        assert any(word in keywords_str for word in relevant_words)

    @pytest.mark.asyncio
    async def test_keyword_weights(self):
        """测试关键词权重计算"""
        text = "machine learning machine learning deep learning AI AI AI"

        result = await extract_keywords(text, max_keywords=5)

        # 验证权重字典
        assert len(result.weights) == len(result.keywords)
        assert all(0.0 <= w <= 1.0 for w in result.weights.values())

        # AI出现最多,应该权重最高
        sorted_keywords = sorted(
            result.weights.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_keyword = sorted_keywords[0][0]
        assert 'ai' in top_keyword or 'machine' in top_keyword

    @pytest.mark.asyncio
    async def test_min_length_filter(self):
        """测试最小长度过滤"""
        text = "AI ML NLP machine learning deep learning algorithms data science"

        result = await extract_keywords(
            text,
            max_keywords=10,
            min_keyword_length=3
        )

        # 所有关键词长度>=3
        assert all(len(kw) >= 3 for kw in result.keywords)

    @pytest.mark.asyncio
    async def test_bigram_extraction(self):
        """测试双词组合提取"""
        text = (
            "machine learning is powerful. "
            "deep learning is a subset of machine learning. "
            "neural networks are used in deep learning."
        )

        result = await extract_keywords(text, max_keywords=10)

        # 应该提取到双词组合
        has_bigram = any(
            ' ' in kw
            for kw in result.keywords
        )
        assert has_bigram, "Should extract bigrams like 'machine learning'"

    @pytest.mark.asyncio
    async def test_special_characters_handling(self):
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

        # 有效词应该保留
        assert any(
            word in keywords_str
            for word in ['ai', 'note', 'app', 'research']
        )


class TestInputValidation:
    """输入验证测试"""

    @pytest.mark.asyncio
    async def test_empty_input(self):
        """测试空输入"""
        with pytest.raises(ValueError, match="at least 10 characters"):
            await extract_keywords("")

    @pytest.mark.asyncio
    async def test_short_input(self):
        """测试过短输入"""
        with pytest.raises(ValueError, match="at least 10 characters"):
            await extract_keywords("short")

    @pytest.mark.asyncio
    async def test_whitespace_only(self):
        """测试仅空格输入"""
        with pytest.raises(ValueError, match="at least 10 characters"):
            await extract_keywords("        ")

    @pytest.mark.asyncio
    async def test_special_chars_only(self):
        """测试仅特殊字符输入"""
        with pytest.raises(ValueError, match="too short after preprocessing"):
            await extract_keywords("!@#$%^&*()[]{},./<>?")


class TestTextPreprocessing:
    """文本预处理测试"""

    def test_lowercase_conversion(self):
        """测试转小写"""
        result = _preprocess_text("AI Machine Learning")
        assert result == "ai machine learning"

    def test_url_removal(self):
        """测试URL移除"""
        text = "Check https://example.com and http://test.com"
        result = _preprocess_text(text)
        assert 'http' not in result
        assert 'example.com' not in result

    def test_email_removal(self):
        """测试邮箱移除"""
        text = "Contact us at test@example.com"
        result = _preprocess_text(text)
        assert '@' not in result
        assert 'example.com' not in result

    def test_html_removal(self):
        """测试HTML标签移除"""
        text = "<p>AI app</p> <div>machine learning</div>"
        result = _preprocess_text(text)
        assert '<' not in result
        assert '>' not in result
        assert 'ai app' in result

    def test_special_char_removal(self):
        """测试特殊字符移除"""
        text = "AI-powered! @note #app $100"
        result = _preprocess_text(text)
        # 连字符应该保留为空格
        assert result == "ai powered note app 100"

    def test_whitespace_normalization(self):
        """测试空格规范化"""
        text = "AI    machine     learning"
        result = _preprocess_text(text)
        assert result == "ai machine learning"


class TestEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_very_long_text(self):
        """测试超长文本"""
        text = "AI machine learning " * 1000  # 20000+ 字符
        result = await extract_keywords(text, max_keywords=10)

        assert len(result.keywords) <= 10
        assert result.total_keywords > 0

    @pytest.mark.asyncio
    async def test_unicode_characters(self):
        """测试Unicode字符"""
        text = "AI application développement 人工智能 машинное обучение"
        # 应该只保留英文部分
        result = await extract_keywords(text, max_keywords=5)

        keywords_str = ' '.join(result.keywords)
        # Unicode字符应该被移除
        assert all(ord(c) < 128 for c in keywords_str if c != ' ')

    @pytest.mark.asyncio
    async def test_repeated_stopwords(self):
        """测试大量停用词"""
        text = "the the the a a an is are was were machine learning"
        result = await extract_keywords(text, max_keywords=5)

        # 停用词应该被过滤
        keywords_str = ' '.join(result.keywords)
        assert 'the' not in keywords_str
        assert 'machine' in keywords_str or 'learning' in keywords_str
```

**2.5 运行测试** (20分钟)

```bash
# 运行关键词提取测试
pytest backend/tests/services/analysis/test_keyword_extraction.py -v

# 期望输出:
# test_keyword_extraction.py::TestExtractKeywords::test_basic_extraction PASSED
# test_keyword_extraction.py::TestExtractKeywords::test_keyword_weights PASSED
# ...
# ==================== 20 passed in 2.35s ====================

# 检查测试覆盖率
pytest backend/tests/services/analysis/test_keyword_extraction.py \
    --cov=backend.app.services.analysis.keyword_extraction \
    --cov-report=term-missing

# 期望覆盖率: >90%

# MyPy类型检查
mypy --strict backend/app/services/analysis/keyword_extraction.py

# 期望: Success: no issues found
```

**验收标准**:
- [ ] TF-IDF算法正确实现
- [ ] 支持1-2 gram提取
- [ ] 正确处理特殊字符、URL、邮箱
- [ ] 单元测试20+通过
- [ ] 测试覆盖率>90%
- [ ] MyPy --strict 0 errors

---

### 下午任务 (14:00-18:00)

#### ✅ 任务3: 实现社区发现算法 (14:00-16:30, 2.5小时)

**目标**: 实现社区相关性评分和Top-K选择

**3.1 创建社区发现模块** (10分钟)

```bash
# 创建社区发现模块
touch backend/app/services/analysis/community_discovery.py

# 创建测试文件
touch backend/tests/services/analysis/test_community_discovery.py

# 创建配置文件目录
mkdir -p backend/config
touch backend/config/community_discovery.yml
```

**3.2 定义数据模型** (15分钟)

```python
# backend/app/models/community.py
"""
社区数据模型
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Community:
    """Reddit社区模型"""
    name: str  # 社区名称 (如 "r/productivity")
    description: str  # 社区描述
    description_keywords: List[str]  # 预提取的描述关键词
    daily_posts: int  # 每日帖子数
    avg_comment_length: int  # 平均评论长度
    category: str  # 社区类别 (如 "productivity", "tech")
    relevance_score: float = 0.0  # 相关性分数 (0-1)
    subscribers: int = 0  # 订阅人数
    activity_level: float = 0.0  # 活跃度 (0-1)
    quality_score: float = 0.0  # 质量分数 (0-1)


@dataclass
class CommunityPool:
    """社区池"""
    communities: List[Community]
    total_count: int

    def __post_init__(self):
        self.total_count = len(self.communities)


# 示例社区池 (简化版,实际应该从数据库加载)
SAMPLE_COMMUNITY_POOL = CommunityPool(
    communities=[
        Community(
            name="r/productivity",
            description="Tips and tricks for being more productive",
            description_keywords=["productivity", "tips", "efficient", "workflow"],
            daily_posts=150,
            avg_comment_length=180,
            category="productivity",
            subscribers=500000,
            activity_level=0.8,
            quality_score=0.85
        ),
        Community(
            name="r/PKM",
            description="Personal Knowledge Management systems and tools",
            description_keywords=["knowledge", "management", "notes", "systems"],
            daily_posts=50,
            avg_comment_length=250,
            category="knowledge",
            subscribers=50000,
            activity_level=0.6,
            quality_score=0.9
        ),
        Community(
            name="r/ObsidianMD",
            description="Discussion about Obsidian note-taking app",
            description_keywords=["obsidian", "notes", "markdown", "linking"],
            daily_posts=100,
            avg_comment_length=220,
            category="tools",
            subscribers=150000,
            activity_level=0.75,
            quality_score=0.88
        ),
        Community(
            name="r/Notion",
            description="Notion workspace tips and templates",
            description_keywords=["notion", "workspace", "templates", "productivity"],
            daily_posts=200,
            avg_comment_length=160,
            category="tools",
            subscribers=300000,
            activity_level=0.9,
            quality_score=0.75
        ),
        Community(
            name="r/SaaS",
            description="Discussion about Software as a Service",
            description_keywords=["saas", "software", "business", "startups"],
            daily_posts=80,
            avg_comment_length=200,
            category="business",
            subscribers=100000,
            activity_level=0.7,
            quality_score=0.8
        ),
    ]
)
```

**3.3 实现社区发现算法** (90分钟)

```python
# backend/app/services/analysis/community_discovery.py
"""
Step 1: 智能社区发现算法
基于PRD-03 § 3.1设计
"""
from __future__ import annotations

from typing import List, Dict, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.analysis.keyword_extraction import extract_keywords
from app.models.community import Community, CommunityPool, SAMPLE_COMMUNITY_POOL


@dataclass
class CommunityDiscoveryResult:
    """社区发现结果"""
    communities: List[Community]
    total_discovered: int
    avg_relevance_score: float
    discovery_time_seconds: float


async def discover_communities(
    product_description: str,
    max_communities: int = 20,
    cache_hit_rate: float = 0.7,
    community_pool: CommunityPool | None = None,
) -> List[Community]:
    """
    智能社区发现算法

    基于产品描述,从社区池中发现最相关的Reddit社区

    算法步骤:
    1. 关键词提取 (TF-IDF)
    2. 动态调整目标社区数量 (基于缓存命中率)
    3. 候选社区评分 (描述匹配40% + 活跃度30% + 质量30%)
    4. Top-K选择 + 多样性保证

    Args:
        product_description: 产品描述文本
        max_communities: 最大社区数量
        cache_hit_rate: 当前缓存命中率 (用于动态调整)
        community_pool: 候选社区池 (None则使用默认池)

    Returns:
        List[Community]: 相关社区列表 (按相关性排序)

    Raises:
        ValueError: 产品描述为空或过短

    示例:
        >>> communities = await discover_communities(
        ...     "AI note-taking app for researchers",
        ...     max_communities=10
        ... )
        >>> print(len(communities))
        10
        >>> print(communities[0].relevance_score)
        0.85
    """
    # 1. 验证输入
    if not product_description or len(product_description) < 10:
        raise ValueError(
            "Product description must be at least 10 characters long"
        )

    # 2. 使用默认社区池(如果未提供)
    if community_pool is None:
        community_pool = SAMPLE_COMMUNITY_POOL

    if not community_pool.communities:
        raise ValueError("Community pool is empty")

    # 3. 关键词提取
    keyword_result = await extract_keywords(
        product_description,
        max_keywords=20
    )

    # 4. 动态调整目标社区数量
    target_communities = _calculate_target_communities(cache_hit_rate)
    target_communities = min(
        target_communities,
        max_communities,
        len(community_pool.communities)
    )

    # 5. 候选社区评分
    scored_communities = await _score_communities(
        keyword_result.keywords,
        community_pool.communities
    )

    # 6. Top-K选择 + 多样性保证
    selected_communities = _select_diverse_top_k(
        scored_communities,
        k=target_communities
    )

    return selected_communities


async def _score_communities(
    keywords: List[str],
    community_pool: List[Community],
) -> List[Tuple[Community, float]]:
    """
    社区相关性评分算法

    评分公式:
    score = description_match * 0.4 + activity_level * 0.3 + quality_score * 0.3

    Args:
        keywords: 产品关键词
        community_pool: 候选社区列表

    Returns:
        List[Tuple[Community, float]]: (社区, 相关性分数) 列表
    """
    scored_communities: List[Tuple[Community, float]] = []

    for community in community_pool:
        # 描述匹配分数 (40%权重)
        description_score = _calculate_description_match(
            keywords,
            community.description_keywords
        )

        # 活跃度分数 (30%权重)
        # 归一化: 100 daily posts = 1.0
        activity_score = min(community.daily_posts / 100.0, 1.0)

        # 质量指标分数 (30%权重)
        # 归一化: 200 avg comment length = 1.0
        quality_score = min(community.avg_comment_length / 200.0, 1.0)

        # 综合评分
        total_score = (
            description_score * 0.4 +
            activity_score * 0.3 +
            quality_score * 0.3
        )

        # 更新社区的相关性分数
        community.relevance_score = total_score

        scored_communities.append((community, total_score))

    return scored_communities


def _calculate_description_match(
    keywords: List[str],
    community_keywords: List[str],
) -> float:
    """
    计算描述匹配分数 (余弦相似度)

    使用TF-IDF向量化后计算余弦相似度

    Args:
        keywords: 产品关键词
        community_keywords: 社区描述关键词

    Returns:
        float: 相似度分数 [0.0, 1.0]
    """
    if not keywords or not community_keywords:
        return 0.0

    # 合并关键词为文本
    product_text = ' '.join(keywords)
    community_text = ' '.join(community_keywords)

    try:
        # TF-IDF向量化
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([product_text, community_text])

        # 计算余弦相似度
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        return float(similarity)

    except Exception:
        # Fallback: 简单的关键词重叠率
        overlap = len(set(keywords) & set(community_keywords))
        return overlap / max(len(keywords), len(community_keywords))


def _select_diverse_top_k(
    scored_communities: List[Tuple[Community, float]],
    k: int,
    max_same_category: int = 5,
) -> List[Community]:
    """
    Top-K选择 + 多样性保证

    确保选中的社区来自不同类别,避免重复

    算法:
    1. 按分数排序
    2. 依次选择社区
    3. 如果同类别社区>5个,跳过
    4. 直到选够k个

    Args:
        scored_communities: (社区, 分数) 列表
        k: 选择数量
        max_same_category: 同类别最大数量

    Returns:
        List[Community]: 选中的社区列表 (按相关性排序)
    """
    # 1. 按分数降序排序
    sorted_communities = sorted(
        scored_communities,
        key=lambda x: x[1],
        reverse=True
    )

    # 2. 应用多样性约束
    selected: List[Community] = []
    category_count: Dict[str, int] = {}

    for community, score in sorted_communities:
        if len(selected) >= k:
            break

        # 检查类别配额
        current_count = category_count.get(community.category, 0)
        if current_count >= max_same_category:
            continue  # 该类别已满,跳过

        # 选择该社区
        selected.append(community)
        category_count[community.category] = current_count + 1

    return selected


def _calculate_target_communities(cache_hit_rate: float) -> int:
    """
    根据缓存命中率动态计算目标社区数量

    策略:
    - 缓存命中率 > 80%: 分析30个社区 (积极模式)
    - 缓存命中率 60-80%: 分析20个社区 (平衡模式)
    - 缓存命中率 < 60%: 分析10个社区 (保守模式)

    Args:
        cache_hit_rate: 当前缓存命中率 [0.0, 1.0]

    Returns:
        int: 目标社区数量

    示例:
        >>> _calculate_target_communities(0.9)
        30
        >>> _calculate_target_communities(0.7)
        20
        >>> _calculate_target_communities(0.5)
        10
    """
    if cache_hit_rate > 0.8:
        return 30  # 积极模式
    elif cache_hit_rate > 0.6:
        return 20  # 平衡模式
    else:
        return 10  # 保守模式


__all__ = [
    "discover_communities",
    "CommunityDiscoveryResult",
]
```

**3.4 编写单元测试** (45分钟)

```python
# backend/tests/services/analysis/test_community_discovery.py
"""
社区发现算法单元测试
"""
import pytest
from app.services.analysis.community_discovery import (
    discover_communities,
    _score_communities,
    _calculate_description_match,
    _select_diverse_top_k,
    _calculate_target_communities,
)
from app.models.community import Community, CommunityPool


class TestDiscoverCommunities:
    """社区发现功能测试"""

    @pytest.mark.asyncio
    async def test_basic_discovery(self):
        """测试基本社区发现"""
        product_desc = "AI笔记应用,帮助研究者自动组织和连接想法"

        communities = await discover_communities(
            product_desc,
            max_communities=20
        )

        assert len(communities) <= 20
        assert len(communities) > 0
        assert all(c.relevance_score > 0.0 for c in communities)

        # 社区应该按相关性排序
        scores = [c.relevance_score for c in communities]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_cache_based_adjustment(self):
        """测试基于缓存命中率的动态调整"""
        product_desc = "note taking app for students"

        # 高缓存命中率 → 更多社区
        communities_high = await discover_communities(
            product_desc,
            cache_hit_rate=0.9
        )

        # 低缓存命中率 → 更少社区
        communities_low = await discover_communities(
            product_desc,
            cache_hit_rate=0.5
        )

        # 高命中率应该返回更多社区
        # (实际数量取决于community_pool大小)
        assert len(communities_high) >= len(communities_low)


class TestCommunityScoring:
    """社区评分测试"""

    @pytest.mark.asyncio
    async def test_score_calculation(self):
        """测试评分计算"""
        keywords = ["productivity", "notes", "workflow"]
        communities = [
            Community(
                name="r/productivity",
                description="Productivity tips",
                description_keywords=["productivity", "tips", "workflow"],
                daily_posts=100,
                avg_comment_length=200,
                category="productivity"
            ),
            Community(
                name="r/gaming",
                description="Gaming discussion",
                description_keywords=["gaming", "games", "esports"],
                daily_posts=500,
                avg_comment_length=150,
                category="gaming"
            ),
        ]

        scored = await _score_communities(keywords, communities)

        # r/productivity应该得分更高
        productivity_score = next(
            score for comm, score in scored
            if comm.name == "r/productivity"
        )
        gaming_score = next(
            score for comm, score in scored
            if comm.name == "r/gaming"
        )

        assert productivity_score > gaming_score


class TestDescriptionMatch:
    """描述匹配测试"""

    def test_perfect_match(self):
        """测试完全匹配"""
        keywords = ["ai", "machine", "learning"]
        community_keywords = ["ai", "machine", "learning"]

        score = _calculate_description_match(keywords, community_keywords)
        assert score > 0.9

    def test_partial_match(self):
        """测试部分匹配"""
        keywords = ["ai", "productivity", "notes"]
        community_keywords = ["productivity", "workflow"]

        score = _calculate_description_match(keywords, community_keywords)
        assert 0.0 < score < 1.0

    def test_no_match(self):
        """测试无匹配"""
        keywords = ["ai", "machine", "learning"]
        community_keywords = ["cooking", "recipes"]

        score = _calculate_description_match(keywords, community_keywords)
        assert score < 0.3


class TestDiversitySelection:
    """多样性选择测试"""

    def test_diversity_enforcement(self):
        """测试多样性约束"""
        communities = [
            (Community(name=f"r/tech{i}", description="", description_keywords=[],
                      daily_posts=100, avg_comment_length=200, category="tech"), 0.9)
            for i in range(10)
        ] + [
            (Community(name="r/business", description="", description_keywords=[],
                      daily_posts=100, avg_comment_length=200, category="business"), 0.8)
        ]

        selected = _select_diverse_top_k(
            communities,
            k=10,
            max_same_category=5
        )

        # 同类别不应超过5个
        tech_count = sum(1 for c in selected if c.category == "tech")
        assert tech_count <= 5

        # 应该包含business类别
        has_business = any(c.category == "business" for c in selected)
        assert has_business


class TestCacheAdjustment:
    """缓存调整测试"""

    def test_aggressive_mode(self):
        """测试积极模式(高缓存命中率)"""
        assert _calculate_target_communities(0.9) == 30

    def test_balanced_mode(self):
        """测试平衡模式(中等命中率)"""
        assert _calculate_target_communities(0.7) == 20

    def test_conservative_mode(self):
        """测试保守模式(低命中率)"""
        assert _calculate_target_communities(0.5) == 10


class TestEdgeCases:
    """边界情况测试"""

    @pytest.mark.asyncio
    async def test_empty_description(self):
        """测试空描述"""
        with pytest.raises(ValueError, match="at least 10 characters"):
            await discover_communities("")

    @pytest.mark.asyncio
    async def test_very_long_description(self):
        """测试超长描述"""
        long_desc = "AI productivity app " * 1000
        communities = await discover_communities(long_desc, max_communities=5)
        assert len(communities) <= 5

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """测试特殊字符"""
        desc = "AI-powered! @note-taking #app $100"
        communities = await discover_communities(desc, max_communities=5)
        assert len(communities) > 0
```

**验收标准**:
- [ ] 社区评分算法正确实现
- [ ] 余弦相似度计算正确
- [ ] 多样性约束生效
- [ ] 动态数量调整正确
- [ ] 单元测试15+通过

---

#### ✅ 任务4: 测试与性能优化 (16:30-18:00, 1.5小时)

**目标**: 确保算法性能和质量

**4.1 性能测试** (30分钟)

```python
# backend/tests/services/analysis/test_community_discovery_performance.py
"""
社区发现性能测试
"""
import pytest
import time
from app.services.analysis.community_discovery import discover_communities
from app.models.community import CommunityPool, Community


@pytest.mark.asyncio
async def test_discovery_performance_small_pool():
    """测试小池性能(<1秒)"""
    product_desc = "AI笔记应用,帮助研究者自动组织和连接想法"

    start_time = time.time()
    communities = await discover_communities(
        product_desc,
        max_communities=20
    )
    duration = time.time() - start_time

    assert duration < 1.0, f"Discovery took {duration:.2f}s, expected <1s"
    assert len(communities) > 0


@pytest.mark.asyncio
async def test_discovery_performance_large_pool():
    """测试大池性能(<30秒)"""
    # 创建500个社区的大池
    large_pool = CommunityPool(
        communities=[
            Community(
                name=f"r/test{i}",
                description=f"Test community {i}",
                description_keywords=["test", f"keyword{i}"],
                daily_posts=100,
                avg_comment_length=200,
                category="test"
            )
            for i in range(500)
        ]
    )

    product_desc = "AI笔记应用测试性能" * 5

    start_time = time.time()
    communities = await discover_communities(
        product_desc,
        max_communities=20,
        community_pool=large_pool
    )
    duration = time.time() - start_time

    assert duration < 30.0, f"Discovery took {duration:.2f}s, expected <30s"
    assert len(communities) == 20
```

**4.2 集成测试** (30分钟)

```python
# backend/tests/services/analysis/test_analysis_integration.py
"""
分析引擎集成测试
测试关键词提取 → 社区发现的完整流程
"""
import pytest
from app.services.analysis.keyword_extraction import extract_keywords
from app.services.analysis.community_discovery import discover_communities


@pytest.mark.asyncio
async def test_full_discovery_pipeline():
    """测试完整发现流程"""
    product_desc = (
        "AI-powered note-taking app for researchers and creators. "
        "Automatically organize ideas and connect concepts using "
        "machine learning algorithms. Perfect for academic writing "
        "and personal knowledge management."
    )

    # Step 1: 关键词提取
    keywords = await extract_keywords(product_desc, max_keywords=20)
    assert len(keywords.keywords) > 0

    # Step 2: 社区发现
    communities = await discover_communities(
        product_desc,
        max_communities=10
    )
    assert len(communities) <= 10

    # 验证社区相关性
    assert all(c.relevance_score > 0.0 for c in communities)

    # 验证多样性
    categories = set(c.category for c in communities)
    assert len(categories) > 1, "Should have diverse categories"


@pytest.mark.asyncio
async def test_discovery_with_different_products():
    """测试不同产品类型"""
    test_cases = [
        {
            "description": "Project management tool for software teams",
            "expected_min_communities": 5,
        },
        {
            "description": "E-commerce platform for small businesses",
            "expected_min_communities": 5,
        },
        {
            "description": "Fitness tracking app with AI coaching",
            "expected_min_communities": 5,
        },
    ]

    for case in test_cases:
        communities = await discover_communities(
            case["description"],
            max_communities=10
        )

        assert len(communities) >= case["expected_min_communities"]
        assert all(c.relevance_score > 0.0 for c in communities)
```

**4.3 代码质量检查** (30分钟)

```bash
# 1. MyPy类型检查
mypy --strict backend/app/services/analysis/

# 期望: Success: no issues found

# 2. 运行所有测试
pytest backend/tests/services/analysis/ -v

# 期望: 所有测试通过

# 3. 测试覆盖率报告
pytest backend/tests/services/analysis/ \
    --cov=backend.app.services.analysis \
    --cov-report=html \
    --cov-report=term-missing

# 期望: 覆盖率>80%

# 4. 代码格式检查
black backend/app/services/analysis/ --check
isort backend/app/services/analysis/ --check

# 期望: All done! ✨
```

**验收标准**:
- [ ] 性能测试通过(小池<1s, 大池<30s)
- [ ] 集成测试全部通过
- [ ] MyPy --strict 0 errors
- [ ] 测试覆盖率>80%
- [ ] 代码格式规范

---

## 📊 今日验收清单

### 功能验收
- [ ] ✅ Backend服务启动,Frontend可联调
- [ ] ✅ TF-IDF关键词提取实现完成
- [ ] ✅ 社区发现算法实现完成
- [ ] ✅ 余弦相似度计算正确
- [ ] ✅ 多样性约束正常工作
- [ ] ✅ 动态数量调整正确

### 测试验收
- [ ] ✅ 关键词提取测试20+通过
- [ ] ✅ 社区发现测试15+通过
- [ ] ✅ 性能测试通过(<30秒)
- [ ] ✅ 集成测试通过
- [ ] ✅ 测试覆盖率>80%

### 质量验收
- [ ] ✅ MyPy --strict 0 errors
- [ ] ✅ Black格式化通过
- [ ] ✅ 无新增技术债
- [ ] ✅ 代码review完成

---

## 🚀 快速参考

### 关键命令
```bash
# 启动服务
uvicorn app.main:app --reload

# 运行测试
pytest backend/tests/services/analysis/ -v

# 类型检查
mypy --strict backend/app/services/analysis/

# 覆盖率报告
pytest --cov=backend.app.services.analysis --cov-report=term-missing
```

### 重要文件
- `backend/app/services/analysis/keyword_extraction.py` - TF-IDF实现
- `backend/app/services/analysis/community_discovery.py` - 社区发现
- `backend/app/models/community.py` - 数据模型
- `backend/tests/services/analysis/` - 测试目录

### 参考文档
- `docs/PRD/PRD-03-分析引擎.md` - 分析引擎设计
- `backend/docs/ANALYSIS_ENGINE_DESIGN.md` - 引擎设计文档
- `DAY6-TASK-ASSIGNMENT.md` - 今日任务总览

---

**Day 6 Backend A 加油! 🚀**

分析引擎的第一步即将完成,这是整个系统的核心!
