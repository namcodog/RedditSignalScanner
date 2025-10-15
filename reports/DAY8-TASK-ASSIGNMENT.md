# Day 8 任务分配与验收文档

> **日期**: 2025-10-13 (Day 8)
> **文档用途**: 任务分配、进度跟踪、验收标准
> **创建时间**: 2025-10-13 10:00
> **责任人**: Lead
> **关键里程碑**: 🚀 **信号提取完成 + Admin后台完成 + ReportPage完成!**

---

## 📅 Day 8 总体目标

### Day 7 验收结果回顾
- ✅ **Backend A**: Reddit API客户端 + 缓存管理器 + 数据采集服务完成
- ✅ **Backend A**: MyPy 0 errors, 8/8单元测试通过
- ✅ **Backend B**: 认证系统集成完成, 6/6测试通过
- ✅ **Frontend**: TypeScript 0 errors, ProgressPage组件完成
- ❌ **Frontend**: 测试失败率44% (8/18失败) - **阻塞性问题**
- ❌ **服务未启动**: Backend/Frontend服务未运行 - **阻塞验收**

### Day 8 关键产出
根据`docs/2025-10-10-3人并行开发方案.md` (第208-217行):
- 🎯 **分析引擎 - 信号提取**: 痛点/竞品/机会识别 + 多维度排序
- 🎯 **Admin后台完成**: Dashboard接口 + 监控数据
- 🎯 **ReportPage完成**: 数据可视化 + 导出功能

### Day 8 里程碑
- 🎯 **信号提取完成** - 分析引擎4步流水线完整可用
- 🎯 **Admin后台完成** - Dashboard + 监控功能
- 🎯 **ReportPage完成** - 完整报告展示 + 导出

---

## 👨‍💻 Backend A（资深后端）任务清单

### 核心职责
1. **实现信号提取模块** (优先级P0)
2. **实现多维度排序** (优先级P0)
3. **完成4步分析流水线** (优先级P0)

### 上午任务 (9:00-12:00) - 信号提取实现

#### 1️⃣ 实现痛点识别算法 (1.5小时) - 优先级P0

**任务描述**:
基于PRD-03设计,实现痛点识别算法,从Reddit帖子中提取用户痛点

**参考文档**:
- `docs/PRD/PRD-03-分析引擎.md` (第268-371行)
- `backend/docs/ANALYSIS_ENGINE_DESIGN.md`

**实现文件**: `backend/app/services/signal_extraction.py`

**核心功能**:
```python
"""
信号提取服务 - 痛点/竞品/机会识别
基于PRD-03 Step 3设计
"""
from __future__ import annotations

from typing import List, Dict, Set
from dataclasses import dataclass
import re
from collections import Counter

@dataclass
class PainPoint:
    """痛点信号"""
    text: str
    score: int
    frequency: int
    sentiment: float  # -1.0 to 1.0
    source_posts: List[str]  # Post IDs
    keywords: List[str]

@dataclass
class Competitor:
    """竞品信号"""
    name: str
    mention_count: int
    sentiment: float
    features_mentioned: List[str]
    source_posts: List[str]

@dataclass
class Opportunity:
    """商业机会信号"""
    description: str
    demand_signal: float  # 0.0 to 1.0
    unmet_need: str
    potential_users: int
    source_posts: List[str]

class SignalExtractor:
    """信号提取器 - 识别痛点/竞品/机会"""

    # 痛点关键词模式
    PAIN_POINT_PATTERNS = [
        r"I (hate|dislike|can't stand) (.+)",
        r"(.+) is (terrible|awful|horrible|annoying|frustrating)",
        r"wish (.+) would (.+)",
        r"need (.+) but (.+)",
        r"tired of (.+)",
        r"struggle with (.+)",
        r"difficult to (.+)",
        r"problem with (.+)",
    ]

    # 情感否定词
    NEGATIVE_WORDS = {
        "hate", "terrible", "awful", "horrible", "annoying",
        "frustrating", "difficult", "problem", "issue", "bug",
        "slow", "broken", "confusing", "complicated", "expensive"
    }

    def __init__(self):
        self.pain_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.PAIN_POINT_PATTERNS
        ]

    def extract_pain_points(
        self,
        posts: List[Dict],
        min_frequency: int = 3
    ) -> List[PainPoint]:
        """
        提取痛点信号

        算法:
        1. 使用正则表达式匹配痛点模式
        2. 计算关键词频率
        3. 情感分析（基于否定词）
        4. 按频率和情感得分排序

        Args:
            posts: 帖子列表
            min_frequency: 最小出现频率

        Returns:
            痛点列表（按重要性排序）
        """
        pain_candidates: Dict[str, Dict] = {}

        # 1. 匹配痛点模式
        for post in posts:
            text = f"{post['title']} {post['selftext']}"
            post_id = post['id']

            for pattern in self.pain_patterns:
                matches = pattern.findall(text)
                for match in matches:
                    pain_text = (
                        match if isinstance(match, str) else " ".join(match)
                    )
                    pain_text = pain_text.strip()

                    if pain_text not in pain_candidates:
                        pain_candidates[pain_text] = {
                            "text": pain_text,
                            "frequency": 0,
                            "source_posts": [],
                            "keywords": []
                        }

                    pain_candidates[pain_text]["frequency"] += 1
                    pain_candidates[pain_text]["source_posts"].append(
                        post_id
                    )

        # 2. 计算情感得分
        pain_points = []
        for pain_text, data in pain_candidates.items():
            if data["frequency"] < min_frequency:
                continue

            # 情感得分 = 否定词密度
            words = pain_text.lower().split()
            negative_count = sum(
                1 for word in words if word in self.NEGATIVE_WORDS
            )
            sentiment = -1.0 * (negative_count / len(words))

            # 提取关键词
            keywords = [
                word for word in words
                if len(word) > 3 and word not in {"the", "and", "but"}
            ]

            pain_points.append(PainPoint(
                text=pain_text,
                score=data["frequency"] * 10 + int(abs(sentiment) * 100),
                frequency=data["frequency"],
                sentiment=sentiment,
                source_posts=data["source_posts"],
                keywords=keywords[:5]  # Top 5 keywords
            ))

        # 3. 按score排序
        pain_points.sort(key=lambda x: x.score, reverse=True)

        return pain_points[:20]  # Top 20 pain points

    def extract_competitors(
        self,
        posts: List[Dict],
        product_keywords: List[str]
    ) -> List[Competitor]:
        """
        提取竞品信号

        算法:
        1. 识别品牌名称（大写词 + URL域名）
        2. 统计提及次数
        3. 分析情感倾向
        4. 提取功能提及

        Args:
            posts: 帖子列表
            product_keywords: 产品关键词

        Returns:
            竞品列表（按提及次数排序）
        """
        competitor_mentions: Dict[str, Dict] = {}

        # URL模式匹配
        url_pattern = re.compile(r'https?://([^/\s]+)')
        # 品牌名称模式（连续大写词）
        brand_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')

        for post in posts:
            text = f"{post['title']} {post['selftext']}"
            post_id = post['id']

            # 提取URL域名
            urls = url_pattern.findall(text)
            for domain in urls:
                # 移除www和常见后缀
                domain = domain.replace("www.", "").split(".")[0]
                if domain not in competitor_mentions:
                    competitor_mentions[domain] = {
                        "mention_count": 0,
                        "source_posts": [],
                        "features": Counter()
                    }
                competitor_mentions[domain]["mention_count"] += 1
                competitor_mentions[domain]["source_posts"].append(post_id)

            # 提取品牌名称
            brands = brand_pattern.findall(text)
            for brand in brands:
                # 过滤常见词
                if brand.lower() in {"reddit", "google", "microsoft"}:
                    continue
                if brand not in competitor_mentions:
                    competitor_mentions[brand] = {
                        "mention_count": 0,
                        "source_posts": [],
                        "features": Counter()
                    }
                competitor_mentions[brand]["mention_count"] += 1
                competitor_mentions[brand]["source_posts"].append(post_id)

        # 转换为Competitor对象
        competitors = []
        for name, data in competitor_mentions.items():
            if data["mention_count"] < 2:  # 至少提及2次
                continue

            competitors.append(Competitor(
                name=name,
                mention_count=data["mention_count"],
                sentiment=0.0,  # TODO: 实现情感分析
                features_mentioned=list(data["features"].keys())[:5],
                source_posts=data["source_posts"]
            ))

        # 按提及次数排序
        competitors.sort(key=lambda x: x.mention_count, reverse=True)

        return competitors[:15]  # Top 15 competitors

    def extract_opportunities(
        self,
        posts: List[Dict],
        product_keywords: List[str]
    ) -> List[Opportunity]:
        """
        提取商业机会信号

        算法:
        1. 识别"wish"/"need"/"want"模式
        2. 统计需求频率
        3. 评估未满足程度
        4. 估算潜在用户数

        Args:
            posts: 帖子列表
            product_keywords: 产品关键词

        Returns:
            机会列表（按需求强度排序）
        """
        opportunity_patterns = [
            re.compile(r"wish (.+?) (had|would|could) (.+)", re.IGNORECASE),
            re.compile(r"need (.+?) that (.+)", re.IGNORECASE),
            re.compile(r"want (.+?) to (.+)", re.IGNORECASE),
            re.compile(r"if only (.+?) (had|could) (.+)", re.IGNORECASE),
        ]

        opportunity_candidates: Dict[str, Dict] = {}

        for post in posts:
            text = f"{post['title']} {post['selftext']}"
            post_id = post['id']
            upvotes = post.get('score', 0)

            for pattern in opportunity_patterns:
                matches = pattern.findall(text)
                for match in matches:
                    desc = " ".join(match).strip()

                    if desc not in opportunity_candidates:
                        opportunity_candidates[desc] = {
                            "frequency": 0,
                            "total_upvotes": 0,
                            "source_posts": []
                        }

                    opportunity_candidates[desc]["frequency"] += 1
                    opportunity_candidates[desc]["total_upvotes"] += upvotes
                    opportunity_candidates[desc]["source_posts"].append(
                        post_id
                    )

        # 转换为Opportunity对象
        opportunities = []
        for desc, data in opportunity_candidates.items():
            if data["frequency"] < 2:  # 至少提及2次
                continue

            # 需求信号强度 = 频率 * 平均upvotes
            avg_upvotes = data["total_upvotes"] / data["frequency"]
            demand_signal = min(
                1.0,
                (data["frequency"] * avg_upvotes) / 1000
            )

            opportunities.append(Opportunity(
                description=desc,
                demand_signal=demand_signal,
                unmet_need=desc,  # 简化版本
                potential_users=data["total_upvotes"],
                source_posts=data["source_posts"]
            ))

        # 按需求信号强度排序
        opportunities.sort(key=lambda x: x.demand_signal, reverse=True)

        return opportunities[:15]  # Top 15 opportunities
```

**验收标准**:
- [ ] SignalExtractor类实现完成
- [ ] 痛点识别算法实现（正则匹配 + 频率统计）
- [ ] 竞品识别算法实现（品牌名称 + URL提取）
- [ ] 机会识别算法实现（需求模式匹配）
- [ ] 单元测试覆盖率>80%
- [ ] MyPy --strict 0 errors

**测试文件**: `backend/tests/services/test_signal_extraction.py`

**测试用例**:
```python
import pytest
from app.services.signal_extraction import (
    SignalExtractor,
    PainPoint,
    Competitor,
    Opportunity
)

def test_extract_pain_points():
    """测试痛点提取"""
    extractor = SignalExtractor()

    posts = [
        {
            "id": "1",
            "title": "I hate how slow this app is",
            "selftext": "It's so frustrating when it crashes",
            "score": 100
        },
        {
            "id": "2",
            "title": "Tired of the complicated interface",
            "selftext": "wish it would be simpler",
            "score": 80
        }
    ]

    pain_points = extractor.extract_pain_points(posts, min_frequency=1)

    assert len(pain_points) > 0
    assert pain_points[0].frequency >= 1
    assert pain_points[0].sentiment < 0  # 负面情感

def test_extract_competitors():
    """测试竞品提取"""
    extractor = SignalExtractor()

    posts = [
        {
            "id": "1",
            "title": "Using Notion for note-taking",
            "selftext": "Check out https://notion.so",
            "score": 50
        },
        {
            "id": "2",
            "title": "Notion is great but expensive",
            "selftext": "Tried Obsidian as well",
            "score": 30
        }
    ]

    competitors = extractor.extract_competitors(
        posts,
        product_keywords=["note-taking"]
    )

    assert len(competitors) > 0
    assert any(c.name.lower() == "notion" for c in competitors)

def test_extract_opportunities():
    """测试机会提取"""
    extractor = SignalExtractor()

    posts = [
        {
            "id": "1",
            "title": "wish there was a tool to organize research papers",
            "selftext": "need something that integrates with Zotero",
            "score": 150
        },
        {
            "id": "2",
            "title": "want a note app to support LaTeX",
            "selftext": "if only Notion had better math support",
            "score": 80
        }
    ]

    opportunities = extractor.extract_opportunities(
        posts,
        product_keywords=["note-taking"]
    )

    assert len(opportunities) > 0
    assert opportunities[0].demand_signal > 0
```

---

#### 2️⃣ 实现多维度排序算法 (1小时) - 优先级P0

**任务描述**:
实现信号的多维度排序算法,支持按热度/新鲜度/相关性排序

**实现文件**: `backend/app/services/signal_ranking.py`

**核心功能**:
```python
"""
信号排序服务 - 多维度排序
基于PRD-03 Step 4设计
"""
from __future__ import annotations

from typing import List, Union, Literal
from datetime import datetime
from dataclasses import dataclass

from app.services.signal_extraction import (
    PainPoint,
    Competitor,
    Opportunity
)

SignalType = Union[PainPoint, Competitor, Opportunity]
SortMethod = Literal["score", "recency", "relevance"]

@dataclass
class RankedSignal:
    """排序后的信号"""
    signal: SignalType
    rank_score: float
    rank_position: int

class SignalRanker:
    """信号排序器 - 多维度排序"""

    def rank_pain_points(
        self,
        pain_points: List[PainPoint],
        sort_by: SortMethod = "score"
    ) -> List[RankedSignal]:
        """
        痛点排序

        排序维度:
        - score: 按频率*情感强度
        - recency: 按最近提及时间（需要时间戳数据）
        - relevance: 按关键词相关性
        """
        if sort_by == "score":
            # 按原始score排序（已在提取时计算）
            sorted_points = sorted(
                pain_points,
                key=lambda x: x.score,
                reverse=True
            )
        elif sort_by == "relevance":
            # 按关键词数量排序
            sorted_points = sorted(
                pain_points,
                key=lambda x: len(x.keywords),
                reverse=True
            )
        else:
            sorted_points = pain_points

        # 转换为RankedSignal
        ranked = []
        for i, signal in enumerate(sorted_points):
            ranked.append(RankedSignal(
                signal=signal,
                rank_score=signal.score,
                rank_position=i + 1
            ))

        return ranked

    def rank_competitors(
        self,
        competitors: List[Competitor],
        sort_by: SortMethod = "score"
    ) -> List[RankedSignal]:
        """
        竞品排序

        排序维度:
        - score: 按提及次数
        - relevance: 按功能相关性
        """
        if sort_by == "score":
            sorted_competitors = sorted(
                competitors,
                key=lambda x: x.mention_count,
                reverse=True
            )
        else:
            sorted_competitors = competitors

        ranked = []
        for i, signal in enumerate(sorted_competitors):
            ranked.append(RankedSignal(
                signal=signal,
                rank_score=float(signal.mention_count),
                rank_position=i + 1
            ))

        return ranked

    def rank_opportunities(
        self,
        opportunities: List[Opportunity],
        sort_by: SortMethod = "score"
    ) -> List[RankedSignal]:
        """
        机会排序

        排序维度:
        - score: 按需求信号强度
        - relevance: 按潜在用户数
        """
        if sort_by == "score":
            sorted_opportunities = sorted(
                opportunities,
                key=lambda x: x.demand_signal,
                reverse=True
            )
        elif sort_by == "relevance":
            sorted_opportunities = sorted(
                opportunities,
                key=lambda x: x.potential_users,
                reverse=True
            )
        else:
            sorted_opportunities = opportunities

        ranked = []
        for i, signal in enumerate(sorted_opportunities):
            ranked.append(RankedSignal(
                signal=signal,
                rank_score=signal.demand_signal,
                rank_position=i + 1
            ))

        return ranked
```

**验收标准**:
- [ ] SignalRanker类实现完成
- [ ] 痛点排序实现（3种维度）
- [ ] 竞品排序实现
- [ ] 机会排序实现
- [ ] 单元测试通过
- [ ] MyPy --strict 0 errors

---

### 下午任务 (14:00-18:00) - 流水线集成

#### 3️⃣ 集成到Celery分析任务 (2小时) - 优先级P0

**任务描述**:
将信号提取和排序集成到Celery分析任务,完成4步流水线

**修改文件**: `backend/app/tasks/analysis_task.py`

**集成代码**:
```python
from app.services.signal_extraction import SignalExtractor
from app.services.signal_ranking import SignalRanker
from app.services.data_collection import DataCollectionService
from app.services.analysis.community_discovery import discover_communities

@celery_app.task(name="tasks.analysis.run", bind=True)
def run_analysis_task(
    self,
    task_id: str,
    product_description: str,
    user_id: str
) -> Dict[str, Any]:
    """
    执行分析任务 - 完整4步流水线

    流程:
    1. 社区发现 (Day 6已完成)
    2. 数据采集 (Day 7已完成)
    3. 信号提取 (Day 8新增)
    4. 排序输出 (Day 8新增)
    """
    # Step 1: 社区发现
    update_task_progress(task_id, progress=10, message="正在发现相关社区...")
    communities = discover_communities(product_description, limit=20)
    subreddits = [c.name for c in communities]

    # Step 2: 数据采集
    update_task_progress(task_id, progress=30, message="正在采集数据...")
    collection_service = DataCollectionService(reddit_client, cache_manager)
    collection_result = await collection_service.collect_posts(
        subreddits=subreddits,
        limit_per_subreddit=100
    )

    # Step 3: 信号提取
    update_task_progress(task_id, progress=60, message="正在提取信号...")
    extractor = SignalExtractor()

    # 合并所有帖子
    all_posts = []
    for posts in collection_result.posts_by_subreddit.values():
        all_posts.extend(posts)

    # 提取信号
    pain_points = extractor.extract_pain_points(all_posts, min_frequency=3)
    competitors = extractor.extract_competitors(
        all_posts,
        product_keywords=product_description.split()
    )
    opportunities = extractor.extract_opportunities(
        all_posts,
        product_keywords=product_description.split()
    )

    # Step 4: 排序输出
    update_task_progress(task_id, progress=85, message="正在排序结果...")
    ranker = SignalRanker()

    ranked_pain_points = ranker.rank_pain_points(pain_points, sort_by="score")
    ranked_competitors = ranker.rank_competitors(
        competitors,
        sort_by="score"
    )
    ranked_opportunities = ranker.rank_opportunities(
        opportunities,
        sort_by="score"
    )

    # 保存结果到数据库
    update_task_progress(task_id, progress=95, message="正在保存结果...")
    analysis = save_analysis_result(
        task_id=task_id,
        user_id=user_id,
        communities=len(communities),
        posts_collected=collection_result.total_posts,
        cache_hit_rate=collection_result.cache_hit_rate,
        pain_points=[p.signal for p in ranked_pain_points],
        competitors=[c.signal for c in ranked_competitors],
        opportunities=[o.signal for o in ranked_opportunities]
    )

    # 完成
    update_task_progress(task_id, progress=100, message="分析完成!")

    return {
        "task_id": task_id,
        "status": "completed",
        "communities_found": len(communities),
        "posts_collected": collection_result.total_posts,
        "cache_hit_rate": collection_result.cache_hit_rate,
        "pain_points_count": len(pain_points),
        "competitors_count": len(competitors),
        "opportunities_count": len(opportunities)
    }
```

**验收标准**:
- [ ] 4步流水线完整集成
- [ ] 任务进度更新正确
- [ ] 结果保存到数据库
- [ ] 端到端测试通过

---

#### 4️⃣ 端到端测试 (1小时) - 优先级P0

**任务描述**:
执行完整端到端测试,验证分析引擎功能

**测试脚本**: `backend/scripts/test_end_to_end_day8.py`

```python
"""
Day 8 端到端测试脚本
验证完整分析流水线
"""
import asyncio
import time
from app.services.analysis_task import run_analysis_task

async def test_full_analysis():
    """测试完整分析流程"""
    print("🚀 开始端到端测试...")

    # 1. 创建测试任务
    task_id = "test-task-day8"
    product_description = "AI-powered note-taking app for researchers"
    user_id = "test-user-1"

    # 2. 执行分析任务
    start_time = time.time()

    result = await run_analysis_task(
        task_id=task_id,
        product_description=product_description,
        user_id=user_id
    )

    duration = time.time() - start_time

    # 3. 验证结果
    print(f"✅ 任务完成，耗时: {duration:.2f}秒")
    print(f"✅ 社区数: {result['communities_found']}")
    print(f"✅ 帖子数: {result['posts_collected']}")
    print(f"✅ 缓存命中率: {result['cache_hit_rate']:.2%}")
    print(f"✅ 痛点数: {result['pain_points_count']}")
    print(f"✅ 竞品数: {result['competitors_count']}")
    print(f"✅ 机会数: {result['opportunities_count']}")

    # 4. 验收标准检查
    assert duration < 270, f"❌ 耗时超标: {duration:.2f}秒 > 270秒"
    assert result['communities_found'] >= 15, "❌ 社区数不足"
    assert result['posts_collected'] >= 1000, "❌ 帖子数不足"
    assert result['cache_hit_rate'] >= 0.6, "❌ 缓存命中率不足"
    assert result['pain_points_count'] >= 10, "❌ 痛点数不足"
    assert result['competitors_count'] >= 5, "❌ 竞品数不足"
    assert result['opportunities_count'] >= 5, "❌ 机会数不足"

    print("✅ 所有验收标准通过!")

if __name__ == "__main__":
    asyncio.run(test_full_analysis())
```

**验收标准**:
- [ ] 完整流程可用（无报错）
- [ ] 处理时间<270秒
- [ ] 社区发现>=15个
- [ ] 帖子采集>=1000个
- [ ] 缓存命中率>=60%
- [ ] 痛点识别>=10个
- [ ] 竞品识别>=5个
- [ ] 机会识别>=5个

---

## 👨‍💻 Backend B（支撑后端）任务清单

### 核心职责
1. **修复Frontend测试失败** (优先级P0 - **阻塞性问题**)
2. **完善Admin后台API** (优先级P0)
3. **实现监控数据采集** (优先级P1)

### 上午任务 (9:00-12:00) - Frontend测试修复

#### 1️⃣ 修复Frontend测试失败 (2小时) - 优先级P0 🚨

**问题分析**:
根据Day 7验收报告：
- 测试失败率: 44% (8/18测试失败)
- 主要问题: 按钮文本匹配失败
- 错误信息: `Unable to find an element with the role "button" and name /开始 5 分钟分析/i`
- 根因: 按钮文本因状态变化（`isAuthenticating`, `isSubmitting`）

**修复方案1: 使用data-testid（推荐）**

**修改文件**: `frontend/src/pages/InputPage.tsx`

```typescript
// 修改前
<button
  type="submit"
  disabled={isAuthenticating || isSubmitting}
>
  {isAuthenticating ? '正在初始化...' : isSubmitting ? '创建任务中...' : '开始 5 分钟分析'}
</button>

// 修改后
<button
  type="submit"
  disabled={isAuthenticating || isSubmitting}
  data-testid="submit-button"  // 添加测试ID
>
  {isAuthenticating ? '正在初始化...' : isSubmitting ? '创建任务中...' : '开始 5 分钟分析'}
</button>
```

**修改文件**: `frontend/src/pages/InputPage.test.tsx`

```typescript
// 修改前
const submitButton = screen.getByRole('button', { name: /开始 5 分钟分析/i });

// 修改后
const submitButton = screen.getByTestId('submit-button');
```

**修复方案2: 使用灵活选择器**

```typescript
// 修改测试用例
const submitButton = screen.getByRole('button', {
  name: /开始|初始化|创建任务/i
});
```

**验收标准**:
- [ ] 所有18个测试通过 ✅
- [ ] 测试覆盖率保持>70%
- [ ] TypeScript 0 errors
- [ ] 测试执行时间<3秒

**测试命令**:
```bash
cd frontend
npm test -- --run

# 期望输出:
# Test Files  3 passed (3)
#      Tests  18 passed (18)
#   Duration  2.18s
```

---

#### 2️⃣ 创建完整认证测试文件 (1小时) - 优先级P1

**任务描述**:
创建Day 7缺失的完整认证测试文件

**新建文件**: `backend/tests/api/test_auth_complete.py`

```python
"""
认证系统完整测试
基于PRD-06用户认证系统
"""
import pytest
from fastapi.testclient import TestClient

def test_register_success(client: TestClient):
    """测试注册成功"""
    response = client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@example.com"

def test_register_duplicate_email(client: TestClient):
    """测试重复邮箱注册"""
    client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "password": "Pass123!"
    })
    response = client.post("/api/auth/register", json={
        "email": "duplicate@example.com",
        "password": "Pass123!"
    })
    assert response.status_code == 409

def test_login_success(client: TestClient):
    """测试登录成功"""
    client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "Pass123!"
    })
    response = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "Pass123!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password(client: TestClient):
    """测试错误密码"""
    client.post("/api/auth/register", json={
        "email": "user@example.com",
        "password": "CorrectPass123!"
    })
    response = client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "WrongPass123!"
    })
    assert response.status_code == 401

def test_token_expiration(client: TestClient):
    """测试Token过期"""
    expired_token = "eyJ..."  # 过期的Token
    response = client.get(
        "/api/status/some-task-id",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
```

**验收标准**:
- [ ] 测试文件创建完成
- [ ] 所有测试用例通过
- [ ] 测试覆盖率>90%

---

### 下午任务 (14:00-18:00) - Admin后台开发

#### 3️⃣ 实现Admin后台Dashboard API (2小时) - 优先级P0

**任务描述**:
实现Admin后台Dashboard API,提供系统监控数据

**参考文档**:
- `docs/PRD/PRD-07-Admin后台.md`

**实现文件**: `backend/app/api/routes/admin.py`

```python
"""
Admin后台API
基于PRD-07设计
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.core.auth import require_admin
from app.core.database import get_db
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.analysis import Analysis

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取Dashboard统计数据

    Returns:
        {
            "total_users": 1234,
            "total_tasks": 5678,
            "tasks_today": 123,
            "tasks_completed_today": 100,
            "avg_processing_time": 45.6,
            "cache_hit_rate": 0.85,
            "active_workers": 4
        }
    """
    # 总用户数
    total_users = db.query(func.count(User.id)).scalar()

    # 总任务数
    total_tasks = db.query(func.count(Task.id)).scalar()

    # 今日任务数
    today = datetime.now().date()
    tasks_today = db.query(func.count(Task.id)).filter(
        func.date(Task.created_at) == today
    ).scalar()

    # 今日完成任务数
    tasks_completed_today = db.query(func.count(Task.id)).filter(
        func.date(Task.created_at) == today,
        Task.status == TaskStatus.COMPLETED
    ).scalar()

    # 平均处理时间（最近100个完成任务）
    recent_completed_tasks = db.query(Task).filter(
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at.isnot(None)
    ).order_by(desc(Task.completed_at)).limit(100).all()

    if recent_completed_tasks:
        processing_times = [
            (task.completed_at - task.created_at).total_seconds()
            for task in recent_completed_tasks
        ]
        avg_processing_time = sum(processing_times) / len(processing_times)
    else:
        avg_processing_time = 0.0

    # 缓存命中率（从Analysis表获取）
    recent_analyses = db.query(Analysis).order_by(
        desc(Analysis.created_at)
    ).limit(100).all()

    if recent_analyses:
        cache_hit_rates = [
            a.cache_hit_rate for a in recent_analyses
            if a.cache_hit_rate is not None
        ]
        avg_cache_hit_rate = (
            sum(cache_hit_rates) / len(cache_hit_rates)
            if cache_hit_rates else 0.0
        )
    else:
        avg_cache_hit_rate = 0.0

    # TODO: Celery Worker数量（需要Celery监控）
    active_workers = 1  # 简化实现

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "tasks_today": tasks_today,
        "tasks_completed_today": tasks_completed_today,
        "avg_processing_time": round(avg_processing_time, 2),
        "cache_hit_rate": round(avg_cache_hit_rate, 2),
        "active_workers": active_workers
    }

@router.get("/tasks/recent")
async def get_recent_tasks(
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取最近的任务列表

    Args:
        limit: 返回数量限制

    Returns:
        [
            {
                "task_id": "...",
                "user_email": "user@example.com",
                "status": "completed",
                "created_at": "2025-10-13T10:00:00",
                "processing_time": 45.6
            },
            ...
        ]
    """
    tasks = db.query(Task).order_by(
        desc(Task.created_at)
    ).limit(limit).all()

    result = []
    for task in tasks:
        processing_time = None
        if task.completed_at:
            processing_time = (
                task.completed_at - task.created_at
            ).total_seconds()

        result.append({
            "task_id": task.task_id,
            "user_email": task.user.email if task.user else "unknown",
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "processing_time": (
                round(processing_time, 2) if processing_time else None
            )
        })

    return result

@router.get("/users/active")
async def get_active_users(
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取活跃用户列表

    Returns:
        [
            {
                "user_id": "...",
                "email": "user@example.com",
                "total_tasks": 123,
                "last_active": "2025-10-13T10:00:00"
            },
            ...
        ]
    """
    # 获取最近30天有活动的用户
    thirty_days_ago = datetime.now() - timedelta(days=30)

    active_users = db.query(
        User.id,
        User.email,
        func.count(Task.id).label('total_tasks'),
        func.max(Task.created_at).label('last_active')
    ).join(Task).filter(
        Task.created_at >= thirty_days_ago
    ).group_by(User.id, User.email).order_by(
        desc('total_tasks')
    ).limit(limit).all()

    result = []
    for user in active_users:
        result.append({
            "user_id": str(user.id),
            "email": user.email,
            "total_tasks": user.total_tasks,
            "last_active": user.last_active.isoformat()
        })

    return result
```

**验收标准**:
- [ ] Dashboard统计接口实现
- [ ] 最近任务列表接口实现
- [ ] 活跃用户列表接口实现
- [ ] 权限控制实现（require_admin）
- [ ] 单元测试通过
- [ ] MyPy --strict 0 errors

---

#### 4️⃣ 实现监控数据采集 (1小时) - 优先级P1

**任务描述**:
实现Celery/Redis/API监控数据采集

**实现文件**: `backend/app/services/monitoring.py`

```python
"""
监控服务 - Celery/Redis/API指标采集
"""
from __future__ import annotations

from typing import Dict, Any
import redis
from celery import Celery

class MonitoringService:
    """监控服务"""

    def __init__(self, redis_client: redis.Redis, celery_app: Celery):
        self.redis = redis_client
        self.celery = celery_app

    def get_celery_stats(self) -> Dict[str, Any]:
        """获取Celery统计数据"""
        # TODO: 实现Celery监控
        return {
            "active_workers": 1,
            "active_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }

    def get_redis_stats(self) -> Dict[str, Any]:
        """获取Redis统计数据"""
        info = self.redis.info()
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_mb": info.get("used_memory", 0) / 1024 / 1024,
            "hit_rate": info.get("keyspace_hits", 0) / (
                info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1)
            )
        }
```

**验收标准**:
- [ ] Celery监控实现
- [ ] Redis监控实现
- [ ] API性能监控实现（可选）

---

## 👩‍💻 Frontend（全栈前端）任务清单

### 核心职责
1. **完善ReportPage** (优先级P0)
2. **实现导出功能** (优先级P0)
3. **UI优化** (优先级P1)

### 上午任务 (9:00-12:00) - ReportPage完善

#### 1️⃣ 实现信号展示组件 (3小时) - 优先级P0

**任务描述**:
创建痛点/竞品/机会展示组件

**新建文件**: `frontend/src/components/PainPointsList.tsx`

```typescript
/**
 * 痛点列表组件
 */
import { Card, Badge } from '@/components/ui';

interface PainPoint {
  text: string;
  score: number;
  frequency: number;
  sentiment: number;
  keywords: string[];
}

interface PainPointsListProps {
  painPoints: PainPoint[];
}

export default function PainPointsList({ painPoints }: PainPointsListProps) {
  return (
    <div className="pain-points-list">
      <h2 className="text-2xl font-bold mb-4">🎯 用户痛点</h2>
      <div className="space-y-4">
        {painPoints.map((pain, index) => (
          <Card key={index} className="p-4">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <p className="text-lg font-medium">{pain.text}</p>
                <div className="mt-2 flex gap-2">
                  {pain.keywords.map((keyword) => (
                    <Badge key={keyword} variant="secondary">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="ml-4 text-right">
                <div className="text-2xl font-bold text-red-500">
                  {pain.score}
                </div>
                <div className="text-sm text-muted-foreground">
                  提及 {pain.frequency} 次
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

**新建文件**: `frontend/src/components/CompetitorsList.tsx`

```typescript
/**
 * 竞品列表组件
 */
import { Card, Badge, ExternalLink } from '@/components/ui';

interface Competitor {
  name: string;
  mention_count: number;
  sentiment: number;
  features_mentioned: string[];
}

interface CompetitorsListProps {
  competitors: Competitor[];
}

export default function CompetitorsList({ competitors }: CompetitorsListProps) {
  return (
    <div className="competitors-list">
      <h2 className="text-2xl font-bold mb-4">🏢 竞品分析</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {competitors.map((competitor, index) => (
          <Card key={index} className="p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-xl font-semibold">{competitor.name}</h3>
              <Badge variant="outline">
                {competitor.mention_count} 提及
              </Badge>
            </div>
            {competitor.features_mentioned.length > 0 && (
              <div className="mt-2">
                <p className="text-sm text-muted-foreground mb-1">
                  主要功能:
                </p>
                <div className="flex flex-wrap gap-1">
                  {competitor.features_mentioned.map((feature) => (
                    <Badge key={feature} variant="secondary" size="sm">
                      {feature}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
```

**新建文件**: `frontend/src/components/OpportunitiesList.tsx`

```typescript
/**
 * 商业机会列表组件
 */
import { Card, Badge, TrendingUp } from '@/components/ui';

interface Opportunity {
  description: string;
  demand_signal: number;
  unmet_need: string;
  potential_users: number;
}

interface OpportunitiesListProps {
  opportunities: Opportunity[];
}

export default function OpportunitiesList({
  opportunities
}: OpportunitiesListProps) {
  return (
    <div className="opportunities-list">
      <h2 className="text-2xl font-bold mb-4">💡 商业机会</h2>
      <div className="space-y-4">
        {opportunities.map((opp, index) => (
          <Card key={index} className="p-4">
            <div className="flex items-start gap-4">
              <div className="flex-1">
                <p className="text-lg font-medium">{opp.description}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {opp.unmet_need}
                </p>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-1 text-green-500">
                  <TrendingUp className="w-5 h-5" />
                  <span className="text-xl font-bold">
                    {(opp.demand_signal * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-sm text-muted-foreground">
                  {opp.potential_users} 潜在用户
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

**修改文件**: `frontend/src/pages/ReportPage.tsx`

```typescript
/**
 * ReportPage - 完整实现
 */
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getAnalysisReport } from '@/api/analyze.api';
import type { AnalysisReport } from '@/types';

import PainPointsList from '@/components/PainPointsList';
import CompetitorsList from '@/components/CompetitorsList';
import OpportunitiesList from '@/components/OpportunitiesList';

export default function ReportPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const fetchReport = async () => {
      try {
        setLoading(true);
        const data = await getAnalysisReport(taskId);
        setReport(data);
      } catch (err) {
        setError('获取报告失败,请稍后重试');
        console.error('[Report Error]', err);
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [taskId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p>加载报告中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-500">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p>报告不存在</p>
        </div>
      </div>
    );
  }

  return (
    <div className="report-page container mx-auto py-8 px-4">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-4xl font-bold mb-2">分析报告</h1>
        <p className="text-muted-foreground">任务ID: {taskId}</p>
      </header>

      {/* Summary */}
      <section className="mb-8 bg-card rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-4">📊 概览</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-primary">
              {report.communities_analyzed}
            </div>
            <div className="text-sm text-muted-foreground">社区数</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-primary">
              {report.posts_analyzed}
            </div>
            <div className="text-sm text-muted-foreground">帖子数</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-primary">
              {report.signals_found}
            </div>
            <div className="text-sm text-muted-foreground">信号数</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-primary">
              {(report.cache_hit_rate * 100).toFixed(0)}%
            </div>
            <div className="text-sm text-muted-foreground">缓存命中</div>
          </div>
        </div>
      </section>

      {/* Pain Points */}
      <section className="mb-8">
        <PainPointsList painPoints={report.pain_points} />
      </section>

      {/* Competitors */}
      <section className="mb-8">
        <CompetitorsList competitors={report.competitors} />
      </section>

      {/* Opportunities */}
      <section className="mb-8">
        <OpportunitiesList opportunities={report.opportunities} />
      </section>
    </div>
  );
}
```

**验收标准**:
- [ ] PainPointsList组件实现
- [ ] CompetitorsList组件实现
- [ ] OpportunitiesList组件实现
- [ ] ReportPage集成所有组件
- [ ] 数据正确展示
- [ ] TypeScript 0 errors

---

### 下午任务 (14:00-18:00) - 导出功能 + UI优化

#### 2️⃣ 实现导出功能 (2小时) - 优先级P0

**任务描述**:
实现报告导出功能（JSON/CSV）

**新建文件**: `frontend/src/utils/export.ts`

```typescript
/**
 * 导出工具函数
 */
import type { AnalysisReport } from '@/types';

export function exportToJSON(report: AnalysisReport, taskId: string): void {
  const dataStr = JSON.stringify(report, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `reddit-signal-scanner-${taskId}.json`;
  link.click();

  URL.revokeObjectURL(url);
}

export function exportToCSV(report: AnalysisReport, taskId: string): void {
  // CSV Header
  let csv = 'Type,Text,Score,Details\n';

  // Pain Points
  report.pain_points.forEach((pain) => {
    csv += `Pain Point,"${pain.text}",${pain.score},"Frequency: ${pain.frequency}"\n`;
  });

  // Competitors
  report.competitors.forEach((comp) => {
    csv += `Competitor,"${comp.name}",${comp.mention_count},"Features: ${comp.features_mentioned.join(', ')}"\n`;
  });

  // Opportunities
  report.opportunities.forEach((opp) => {
    csv += `Opportunity,"${opp.description}",${(opp.demand_signal * 100).toFixed(0)},"Users: ${opp.potential_users}"\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `reddit-signal-scanner-${taskId}.csv`;
  link.click();

  URL.revokeObjectURL(url);
}
```

**修改文件**: `frontend/src/pages/ReportPage.tsx`

```typescript
import { exportToJSON, exportToCSV } from '@/utils/export';

// 在ReportPage组件中添加导出按钮
<header className="mb-8 flex justify-between items-center">
  <div>
    <h1 className="text-4xl font-bold mb-2">分析报告</h1>
    <p className="text-muted-foreground">任务ID: {taskId}</p>
  </div>
  <div className="flex gap-2">
    <button
      onClick={() => exportToJSON(report, taskId!)}
      className="btn btn-secondary"
    >
      导出 JSON
    </button>
    <button
      onClick={() => exportToCSV(report, taskId!)}
      className="btn btn-secondary"
    >
      导出 CSV
    </button>
  </div>
</header>
```

**验收标准**:
- [ ] JSON导出功能实现
- [ ] CSV导出功能实现
- [ ] 导出按钮集成到ReportPage
- [ ] 文件名包含task_id
- [ ] 导出数据完整准确

---

#### 3️⃣ UI优化 (2小时) - 优先级P1

**任务描述**:
优化ReportPage的UI和交互体验

**优化项**:
1. 响应式布局（移动端适配）
2. 加载状态动画优化
3. 错误处理优化（重试按钮）
4. 空状态处理
5. 骨架屏加载

**验收标准**:
- [ ] 移动端布局正常
- [ ] 加载动画流畅
- [ ] 错误处理完善
- [ ] 用户体验良好

---

## 🧪 端到端验收标准

### 验收流程（必须全部通过）

#### 阶段1: 代码质量验收 ✅

**Backend A验收**:
```bash
# 1. MyPy类型检查
cd backend
python -m mypy --strict app/services/signal_extraction.py
python -m mypy --strict app/services/signal_ranking.py
# 期望: Success: no issues found

# 2. 单元测试
python -m pytest tests/services/test_signal_extraction.py -v
python -m pytest tests/services/test_signal_ranking.py -v
# 期望: 所有测试通过,覆盖率>80%
```

**Backend B验收**:
```bash
# 1. Frontend测试修复
cd frontend
npm test -- --run
# 期望: 18/18通过 ✅

# 2. 认证测试
cd backend
python -m pytest tests/api/test_auth_complete.py -v
# 期望: 所有测试通过

# 3. Admin API测试
python -m pytest tests/api/test_admin.py -v
# 期望: 所有测试通过
```

**Frontend验收**:
```bash
# 1. TypeScript检查
cd frontend
npx tsc --noEmit
# 期望: 0 errors

# 2. 单元测试
npm test -- --run
# 期望: 所有测试通过
```

---

#### 阶段2: 服务启动验收 ✅

**验证所有服务正常运行**:
```bash
# 1. PostgreSQL
psql -h localhost -p 5432 -U postgres -d reddit_scanner -c "SELECT 1;"
# 期望: 返回1

# 2. Redis
redis-cli ping
# 期望: PONG

# 3. Backend
curl http://localhost:8006/docs
# 期望: 返回Swagger UI

# 4. Celery Worker
# 检查Worker日志显示ready

# 5. Frontend
curl http://localhost:3006
# 期望: 返回HTML
```

---

#### 阶段3: API功能验收 ✅

**测试完整分析流程**:
```bash
# 1. 注册用户
TOKEN=$(curl -s -X POST http://localhost:8006/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test-day8@example.com","password":"TestPass123"}' \
  | jq -r '.access_token')

# 2. 创建分析任务
TASK_ID=$(curl -s -X POST http://localhost:8006/api/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_description":"AI-powered note-taking app"}' \
  | jq -r '.task_id')

# 3. 等待任务完成（应该包含信号提取）
sleep 60

# 4. 获取报告
curl -s http://localhost:8006/api/report/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

# 期望输出包含:
# {
#   "pain_points": [...],  // 至少10个
#   "competitors": [...],  // 至少5个
#   "opportunities": [...], // 至少5个
#   "communities_analyzed": 20,
#   "posts_analyzed": 1500+
# }
```

---

#### 阶段4: 前端功能验收 ✅

**浏览器测试流程**:
1. ✅ 打开 `http://localhost:3006`
2. ✅ 输入产品描述: "AI-powered note-taking app"
3. ✅ 点击"开始 5 分钟分析"
4. ✅ 自动跳转到ProgressPage
5. ✅ 看到实时进度更新（0% → 100%）
6. ✅ 进度达到100%后自动跳转到ReportPage
7. ✅ 看到完整报告（痛点/竞品/机会）
8. ✅ 测试导出功能（JSON/CSV）

**验收标准**:
- [ ] 完整流程无报错
- [ ] 数据正确展示
- [ ] 导出功能可用
- [ ] UI响应流畅

---

#### 阶段5: 端到端验收 ✅

**完整流程验证**:
```bash
# 运行端到端测试脚本
cd backend
python scripts/test_end_to_end_day8.py

# 期望输出:
# ✅ 任务完成，耗时: 180秒
# ✅ 社区数: 20
# ✅ 帖子数: 1500
# ✅ 缓存命中率: 65%
# ✅ 痛点数: 15
# ✅ 竞品数: 8
# ✅ 机会数: 10
# ✅ 所有验收标准通过!
```

---

## 📊 Day 8 验收清单

### Backend A验收 ✅
- [ ] SignalExtractor类实现完成
- [ ] 痛点识别算法实现
- [ ] 竞品识别算法实现
- [ ] 机会识别算法实现
- [ ] SignalRanker类实现完成
- [ ] 多维度排序实现
- [ ] 集成到Celery任务
- [ ] 4步流水线完整可用
- [ ] 处理时间<270秒
- [ ] 信号提取准确率>75%
- [ ] MyPy --strict 0 errors
- [ ] 单元测试覆盖率>80%

### Backend B验收 ✅
- [ ] Frontend测试18/18通过 ✅
- [ ] 完整认证测试文件创建
- [ ] Admin Dashboard API实现
- [ ] 最近任务列表API实现
- [ ] 活跃用户列表API实现
- [ ] 监控数据采集实现
- [ ] MyPy --strict 0 errors
- [ ] 所有测试通过

### Frontend验收 ✅
- [ ] PainPointsList组件完成
- [ ] CompetitorsList组件完成
- [ ] OpportunitiesList组件完成
- [ ] ReportPage完整实现
- [ ] JSON导出功能实现
- [ ] CSV导出功能实现
- [ ] UI优化完成
- [ ] TypeScript 0 errors
- [ ] 单元测试通过

### 端到端验收 ✅
- [ ] 所有服务正常运行
- [ ] 完整流程可用（输入→报告）
- [ ] 信号提取功能验证
- [ ] 报告数据正确展示
- [ ] 导出功能正常
- [ ] 性能指标达标

---

## 📝 Day 8 成功标志

- ✅ **信号提取完成** - 痛点/竞品/机会算法实现
- ✅ **分析引擎完成** - 4步流水线全部工作
- ✅ **Admin后台完成** - Dashboard + 监控功能
- ✅ **ReportPage完成** - 完整报告展示 + 导出
- ✅ **Frontend测试修复** - 18/18测试通过
- ✅ **为Day 9铺平道路** - 集成测试和优化准备就绪

---

## 🚨 关键风险与缓解

### 风险1: 信号提取准确率不足
**缓解措施**:
- 使用多种正则模式匹配
- 引入频率阈值过滤噪音
- 人工验证前10个结果
- 迭代优化算法

### 风险2: Frontend测试修复影响开发进度
**缓解措施**:
- Backend B优先处理（阻塞性P0）
- 使用`data-testid`方案（最稳定）
- 完成后立即通知Frontend
- 并行开发ReportPage组件

### 风险3: 端到端性能不达标（>270秒）
**缓解措施**:
- 分步计时，定位瓶颈
- 优化Redis缓存策略
- 减少不必要的数据库查询
- 考虑异步并行处理

---

## 🔄 协作节点

### 早上9:00 - Day 8启动会（15分钟）
**议程**:
1. Backend A汇报信号提取算法设计
2. Backend B汇报Frontend测试修复方案
3. Frontend汇报ReportPage组件设计
4. 确认今日目标和验收标准

### 下午14:00 - 中间检查点（10分钟）
**议程**:
1. Backend A确认信号提取模块可用
2. Backend B确认Frontend测试全部通过 ✅
3. Frontend确认ReportPage布局完成
4. 讨论遇到的阻塞问题

### 晚上18:00 - Day 8验收会（30分钟）
**议程**:
1. 完整流程演示（输入→分析→报告→导出）
2. 逐项验收标准检查
3. 问题记录和技术债务
4. Day 9计划确认

---

## 📝 每日总结模板

```markdown
### Day 8 总结 (2025-10-13)

**计划任务**:
1. Backend A: 信号提取 + 排序
2. Backend B: Frontend测试修复 + Admin后台
3. Frontend: ReportPage完成 + 导出功能

**实际完成**:
- [ ] Backend A任务
- [ ] Backend B任务
- [ ] Frontend任务

**代码统计**:
- 新增文件: ___个
- 代码行数: ___行
- 测试文件: ___个

**质量指标**:
- MyPy: ✅/❌
- 测试通过率: ___%
- 覆盖率: ___%

**遇到问题**:
1. 问题描述
   - 解决方案
   - 用时: ___小时

**明日计划**:
1. 集成测试和优化
2. 性能调优
3. Bug修复

**风险提示**:
- ___
```

---

**Day 8 加油！分析引擎即将完成！🚀**
