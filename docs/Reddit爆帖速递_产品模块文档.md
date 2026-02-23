# Reddit爆帖速递 - 产品模块文档

**文档版本**: v2.2  
**创建日期**: 2026-01-28  
**最后更新**: 2026-01-28  
**模块定位**: 轻量级Reddit热帖检索入口  
**目标用户**: 跨境电商卖家、市场研究人员、产品经理

---

## 📋 目录

| 章节 | 内容 | 说明 |
|------|------|------|
| **🔒** | **口径与真相源** | 全局规则、术语定义 ⭐⭐⭐ |
| 一 | 产品概述 | 模块定位、核心价值、入口位置 |
| 二 | 功能模式设计 | 热点追踪、痛点挖掘、机会发现三大模式 |
| 三 | 用户体验流程 | 搜索页、结果页 UI 设计 |
| 四 | 技术架构 | 系统架构、缓存策略、限流策略、并发容量 |
| 五 | 数据结构定义 | 请求/响应结构 |
| 六 | 信号词库 | Rant/Opportunity/Discovery 信号词 |
| 七 | API 参数说明 | 搜索参数、单次消耗 |
| 八 | 部署清单 | 依赖服务、配置项、监控指标 |
| 九 | **范围与口径** | 数据覆盖、时间窗、语言、结果性质 ⭐ |
| 十 | **可信度与提示** | 可信度等级、证据门槛、LLM 降级 ⭐ |
| 十一 | **异常与降级** | 无结果、限流、API 异常处理 ⭐ |
| 十二 | **系统衔接** | 社区池反哺、深度分析入口、数据隔离 ⭐ |
| 十三 | **数据资产** | 证据复用、评论不落库、临时会话 ⭐⭐⭐ |
| 十四 | **合规限流** | 100 QPM 口径、10分钟窗口 ⭐⭐⭐ |
| 十五 | **安全权限** | 登录权限、频率限制、风控策略 ⭐ |
| 十六 | **指标验收** | 核心指标、性能指标、MVP 验收标准 ⭐ |
| 十七 | **LLM 报告生成** | Prompt 架构、三模式模板、字段归属表 ⭐⭐⭐ |
| 十八 | 迭代计划 | Phase 1-3 规划 |

> ⭐ 标记的为 v2.0 新增补充章节  
> ⭐⭐ 标记的为 v2.1 新增章节  
> ⭐⭐⭐ 标记的为 v2.2 重大修正（口径统一、数据策略、LLM 契约）

---

## 🔒 口径与真相源（Source of Truth）

> ⚠️ **本节为全局规则，所有章节设计必须遵守，如有冲突以此为准。**

| 维度 | 真相源 | 说明 |
|------|-------|------|
| **Reddit API 限额** | [Reddit Data API 官方文档](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) + r/redditdev 官方公告 | 当前口径：100 QPM / OAuth client id，10分钟滚动平均 |
| **推送协议** | 主系统 PRD-02（SSE） | 统一使用 SSE，除非有 ADR（架构决策记录）明确变更 |
| **数据表结构** | `docs/2025-12-14-database-architecture-atlas.md`（DB Atlas） | 表是否存在、字段定义以此为准 |
| **LLM 输出契约** | 本文档 §17.11《字段归属与计算方式》 | 统计值必须由代码计算，LLM 仅负责归纳/表达 |
| **证据帖子资产** | `evidence_posts` 表（主系统） | 爆帖速递不创建独立证据体系，复用主系统资产 |

### 关键术语定义

| 术语 | 定义 |
|------|------|
| **QPM** | Queries Per Minute = **API 请求次数**，不是用户查询次数。一次用户查询可能消耗 N 次 API calls。 |
| **证据帖子** | 经过筛选、与用户查询相关的 Reddit 帖子，统一存入 `evidence_posts` 表。 |
| **临时会话** | 存储在 Redis 的短期数据（TTL ≤ 30min），不落 PostgreSQL。 |

---

## 一、产品概述

### 1.1 模块定位

"Reddit爆帖速递"是一个面向用户的轻量级检索入口，让用户能够**快速查阅Reddit上最新、最火的讨论**，无需深入了解Reddit的社区结构，即可获得有价值的市场洞察。

### 1.2 核心价值

| 价值点 | 说明 |
|-------|------|
| **快速** | 1-2分钟内返回结果，满足即时决策需求 |
| **精准** | 智能解析用户意图，匹配最佳搜索模式 |
| **有证据** | 每个结论都附带Reddit原帖链接，可溯源验证 |
| **低门槛** | 用户无需了解Reddit，输入自然语言即可 |

### 1.3 入口位置

```
┌─────────────────────────────────────────────────────────────┐
│  Logo    首页    分类    [🔥 爆帖速递]    登录 / 注册       │
└─────────────────────────────────────────────────────────────┘
                              ↑
                    导航栏固定位置，登录前后均可见
                    
登录后：
┌─────────────────────────────────────────────────────────────┐
│  Logo    首页    分类    [🔥 爆帖速递]    用户头像 ▼        │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、功能模式设计

### 2.1 三大检索模式

根据用户的查询意图，系统自动匹配以下三种模式：

| 模式 | 适用场景 | 核心目标 |
|------|---------|---------|
| 🔥 **热点追踪** | "最近最火的AI工具讨论" | 发现趋势热点 |
| 💢 **痛点挖掘** | "Adobe在海外的口碑" | 挖掘产品缺陷 |
| 💡 **机会发现** | "有没有好用的XX工具" | 发现商业机会 |

---

### 2.2 模式一：热点追踪（Trending Mode）

#### 适用场景
- "最近Reddit上讨论最多的AI话题是什么？"
- "短剧在国外市场反响如何？"
- "非遗文化产品在国外有讨论吗？"

#### 搜索策略
```yaml
排序方式: top / hot
时间范围: week / month（默认随模式，见 9.2）
过滤条件: 
  - score >= 100（高赞帖）
  - num_comments >= 20（有讨论）
信号词库: 不需要，纯热度排序
```

#### 输出结构
```json
{
  "mode": "trending",
  "query": "AI工具",
  "summary": "过去一周，Reddit上关于AI工具的讨论主要集中在...",
  "top_posts": [
    {
      "rank": 1,
      "title": "Best AI Tools for Productivity in 2024",
      "score": 5200,
      "num_comments": 342,
      "subreddit": "r/ArtificialIntelligence",
      "reddit_url": "https://...",
      "top_comment": "..."
    }
  ],
  "trending_keywords": ["Cursor", "Claude", "v0", "Midjourney"],
  "hot_communities": ["r/ArtificialIntelligence", "r/ChatGPT", "r/LocalLLaMA"]
}
```

---

### 2.3 模式二：痛点挖掘（Rant Mode）

#### 适用场景
- "Adobe在海外的口碑如何？"
- "Salesforce有什么吐槽？"
- "iRobot扫地机器人的用户反馈"

#### 搜索策略
```yaml
排序方式: top（全时段热门）
时间范围: all（全时段，以获取足够样本）
过滤条件:
  - 帖子标题/正文必须包含至少1个吐槽信号词
  - num_comments >= 5（有讨论的帖子）

吐槽信号词库:
  - 统一读取 `backend/config/boom_post_keywords.yaml`
  - 下方示例仅说明结构，不参与运行，完整词库以配置文件为准
```

#### 输出结构
```json
{
  "mode": "rant",
  "query": "Adobe",
  "summary": "Adobe在Reddit上的口碑整体偏负面，用户最常吐槽的是...",
  "sentiment_overview": {
    "positive_ratio": 0.25,
    "negative_ratio": 0.60,
    "neutral_ratio": 0.15
  },
  "pain_points": [
    {
      "category": "定价策略",
      "mentions": 45,
      "sample_quotes": ["..."],
      "severity": "high"
    }
  ],
  "top_rants": [
    {
      "rank": 1,
      "title": "Why I'm finally leaving Adobe after 10 years",
      "score": 1200,
      "num_comments": 89,
      "rant_signals": ["leaving", "nightmare", "overpriced"],
      "reddit_url": "https://...",
      "top_comments": [...]
    }
  ],
  "communities": ["r/Adobe", "r/graphic_design", "r/Photography"]
}
```

#### 核心能力：逻辑缺陷识别

不只是找"骂人的帖子"，而是找**有逻辑分析的吐槽**：

```python
# 高质量吐槽的特征
quality_indicators = {
    "has_specific_feature": True,      # 提到具体功能模块
    "has_comparison": True,            # 有竞品对比
    "has_workaround": True,            # 提到临时解决方案
    "has_price_mention": True,         # 提到性价比
    "comment_agreement_ratio": 0.7     # 评论区70%+表示赞同
}
```

---

### 2.4 模式三：机会发现（Opportunity Mode）

#### 适用场景
- "有没有好用的AI视频剪辑工具？"
- "跨境电商有什么新趋势？"
- "有什么有趣的EDC产品？"

#### 搜索策略
```yaml
排序方式: relevance + top
时间范围: month / year
过滤条件:
  - 帖子类型为"求助/提问"
  - 评论区有"me too"共鸣信号

机会信号词库:
  求助类: ["is there a tool", "looking for", "need help finding", "anyone know"]
  推荐类: ["recommendation for", "alternative to", "best app for"]
  痛点类: ["I wish there was", "would pay for", "no good solution", "frustrating"]
  共鸣类: ["me too", "same here", "also looking", "following"]
```

#### 输出结构
```json
{
  "mode": "opportunity",
  "query": "AI视频剪辑工具",
  "summary": "用户普遍在寻找能够一键生成短视频的AI工具，目前市场上...",
  "unmet_needs": [
    {
      "need": "自动生成字幕并翻译成多语言",
      "mentions": 23,
      "me_too_count": 45,
      "current_workarounds": ["CapCut + 手动翻译", "Premiere + 第三方插件"],
      "opportunity_signal": "high"
    }
  ],
  "product_mentions": [
    {
      "name": "CapCut",
      "sentiment": "positive",
      "mentions": 34,
      "common_praise": ["免费", "简单"],
      "common_complaint": ["功能有限", "导出水印"]
    }
  ],
  "top_discovery_posts": [...],
  "communities": ["r/VideoEditing", "r/Filmmakers", "r/YouTubers"]
}
```

---

## 三、用户体验流程

### 3.1 主流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Reddit爆帖速递                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔍 输入你想了解的话题...                                    │
│  ___________________________________________________________│
│                                                             │
│  💡 快捷示例：                                               │
│  [安克品牌口碑] [AI工具推荐] [跨境电商趋势] [产品吐槽]        │
│                                                             │
│  📌 或选择模式：                                             │
│  ○ 🔥 热点追踪（看最近最火的讨论）                           │
│  ○ 💢 痛点挖掘（看产品/品牌的吐槽）                          │
│  ○ 💡 机会发现（看未满足的需求）                             │
│                                                             │
│                        [ 🚀 开始检索 ]                       │
└─────────────────────────────────────────────────────────────┘
```

### 3.1.1 中文关键词解析（LLM）

> 口径：Reddit 以英文为主，中文输入会先解析为英文关键词再检索。

流程（命中中文才触发）：
```
中文输入 → LLM 解析 → 英文关键词/社区 → Reddit 搜索
```

解析输出（JSON）：
```json
{
  "query_en": "robot vacuum",
  "keywords": ["Roomba", "robot vacuum"],
  "subreddits": ["RobotVacuums", "r/Roomba"]
}
```

回退规则：
- LLM 失败/返回空值：直接使用原始 query 搜索（不阻塞流程）。
- 缓存：同一中文 query 24 小时内复用解析结果。

### 3.2 结果页面

```
┌─────────────────────────────────────────────────────────────┐
│  ← 返回    Adobe 口碑分析    🔄 刷新                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 一句话洞察                                               │
│  ────────────────────────────────────────────────────────── │
│  Adobe在Reddit上口碑偏负面（60%吐槽），主要集中在定价贵、     │
│  订阅制不灵活、软件越来越臃肿三个方面。                       │
│                                                             │
│  🔥 核心吐槽点 Top 3                                         │
│  ────────────────────────────────────────────────────────── │
│  1. 💸 定价策略（45条讨论）                                  │
│     "每月$60对个人用户太贵了，而且取消订阅还要付违约金..."    │
│     🔗 查看原帖                                              │
│                                                             │
│  2. 🐌 性能问题（32条讨论）                                  │
│     "Premiere越更新越卡，我的M1 Max带不动了..."              │
│     🔗 查看原帖                                              │
│                                                             │
│  💬 神评论精选                                               │
│  ────────────────────────────────────────────────────────── │
│  [r/Adobe] "I switched to DaVinci Resolve and never looked  │
│  back. Free, powerful, and actually runs smoothly." (👍892)  │
│  🔗 https://reddit.com/...                                   │
│                                                             │
│  📍 相关社区                                                 │
│  ────────────────────────────────────────────────────────── │
│  r/Adobe (12k讨论) | r/graphic_design (8k) | r/Premiere (5k) │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、技术架构

### 4.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户请求                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway                                   │
│                  (认证 + 限流入口)                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    缓存层 (Redis)                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  缓存Key: "rant:{query}:{subreddits_hash}"               │    │
│  │  TTL: 1小时                                              │    │
│  │  命中 → 直接返回（<100ms）                               │    │
│  │  未命中 → 进入请求队列                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ (未命中)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    请求队列 (Rate Limiter)                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  限制: 900 requests / 10min（≈90 QPM）                  │    │
│  │  策略: 滑动窗口 + FIFO队列                               │    │
│  │  超限 → 排队等待 / 返回"繁忙，请稍后"                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Reddit API Client                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. search_posts()         - 搜索帖子                    │    │
│  │  2. search_subreddit_page() - 社区内搜索                 │    │
│  │  3. fetch_post_comments()  - 抓取评论                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    分析处理层                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. 模式识别（判断用户意图）                             │    │
│  │  2. 信号词检测（吐槽/推荐/热度）                         │    │
│  │  3. 帖子打分排序                                         │    │
│  │  4. 评论精选                                             │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 摘要层（可选）                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  输入: Top 10帖子 + 评论                                 │    │
│  │  输出: 一句话洞察 + 痛点聚类                             │    │
│  │  调用: 仅对复杂查询启用                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    返回结果 + 写入缓存                           │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4.2 缓存策略

#### 缓存Key设计
```python
def build_cache_key(query: str, mode: str, subreddits: list) -> str:
    """
    生成缓存Key
    格式: "reddit_hot:{mode}:{query_hash}:{subreddits_hash}"
    """
    import hashlib
    
    query_normalized = query.lower().strip()
    query_hash = hashlib.md5(query_normalized.encode()).hexdigest()[:8]
    subs_hash = hashlib.md5(",".join(sorted(subreddits)).encode()).hexdigest()[:8]
    
    return f"reddit_hot:{mode}:{query_hash}:{subs_hash}"

# 示例
# query="Adobe吐槽", mode="rant", subreddits=["Adobe", "graphic_design"]
# 生成: "reddit_hot:rant:a3f2c1d8:b7e4f9a2"
```

#### TTL策略
```yaml
热点追踪模式:
  TTL: 30分钟  # 热点变化较快
  
痛点挖掘模式:
  TTL: 2小时   # 口碑数据相对稳定
  
机会发现模式:
  TTL: 1小时   # 需求变化中等
```

#### 缓存预热
```python
# 对热门查询进行预热
HOT_QUERIES = [
    {"query": "AI工具", "mode": "trending"},
    {"query": "Adobe", "mode": "rant"},
    {"query": "跨境电商", "mode": "opportunity"},
]

async def warm_up_cache():
    """每小时预热热门查询"""
    for item in HOT_QUERIES:
        result = await search_reddit(item["query"], mode=item["mode"])
        await redis.setex(
            build_cache_key(item["query"], item["mode"], []),
            3600,
            json.dumps(result)
        )
```

---

### 4.3 限流策略

#### Reddit API 官方限制
```yaml
官方限制（Reddit Data API）:
  额度: 100 QPM / OAuth client id
  统计窗口: 10 minutes rolling average（支持短时 burst）
  监控Header: X-Ratelimit-Used / X-Ratelimit-Remaining / X-Ratelimit-Reset
  超限响应: HTTP 429
  单次数据量: 最多 100 条

重要说明:
  - QPM = API 请求次数（API calls），不是用户查询次数
  - 一次用户查询可能消耗 N 次 API calls（搜索 + 评论抓取）
  - 官方按 10 分钟窗口平均，允许短时 burst
```

#### 我们的限流实现
```python
import asyncio
from collections import deque
import time

class RedditRateLimiter:
    """
    Reddit API 限流器
    
    官方: 100 QPM per client_id，10分钟滚动平均
    我们: 900 requests / 10min（留 100 个 buffer）
    """
    
    def __init__(self, max_requests: int = 900, window_seconds: int = 600):
        """
        Args:
            max_requests: 10分钟窗口内最大请求数（官方约1000，我们留 buffer 用 900）
            window_seconds: 窗口大小（600秒 = 10分钟）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_timestamps: deque = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> float:
        """
        获取执行权限
        返回需要等待的秒数（0表示可立即执行）
        """
        async with self.lock:
            now = time.time()
            
            # 清理过期的请求记录（超过10分钟的）
            while self.request_timestamps and \
                  self.request_timestamps[0] < now - self.window_seconds:
                self.request_timestamps.popleft()
            
            # 检查是否超限
            if len(self.request_timestamps) >= self.max_requests:
                # 计算需要等待的时间
                oldest = self.request_timestamps[0]
                wait_time = oldest + self.window_seconds - now
                return max(0, wait_time)
            
            # 记录本次请求
            self.request_timestamps.append(now)
            return 0
    
    async def execute(self, coro):
        """执行一个协程，自动处理限流"""
        wait_time = await self.acquire()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            await self.acquire()
        return await coro
    
    def get_stats(self) -> dict:
        """获取当前限流状态（用于监控）"""
        return {
            "used_in_window": len(self.request_timestamps),
            "remaining": self.max_requests - len(self.request_timestamps),
            "window_seconds": self.window_seconds
        }

# 全局限流器实例（10分钟窗口，900请求上限）
rate_limiter = RedditRateLimiter(max_requests=900, window_seconds=600)
```

#### 用户等待提示
```python
async def handle_search_request(query: str, mode: str):
    """处理搜索请求，带用户友好的等待提示"""
    
    # 1. 检查缓存
    cache_key = build_cache_key(query, mode, [])
    cached = await redis.get(cache_key)
    if cached:
        return {"status": "success", "data": json.loads(cached), "from_cache": True}
    
    # 2. 检查队列状态
    queue_position = await get_queue_position()
    if queue_position > 0:
        estimated_wait = queue_position * 30  # 每个请求约30秒
        return {
            "status": "queued",
            "position": queue_position,
            "estimated_wait_seconds": estimated_wait,
            "message": f"当前排队第{queue_position}位，预计等待{estimated_wait}秒"
        }
    
    # 3. 执行搜索
    result = await rate_limiter.execute(
        search_reddit(query, mode)
    )
    
    # 4. 写入缓存
    await redis.setex(cache_key, 3600, json.dumps(result))
    
    return {"status": "success", "data": result, "from_cache": False}
```

---

### 4.4 多用户并发容量

#### 单 API Key 容量
```yaml
每次查询消耗:
  搜索请求: 3-9 次（取决于社区数量）
  评论请求: 10-20 次
  总计: 约 30 次 API calls / 用户查询

官方限制: 100 QPM（≈1000 / 10min，10 分钟滚动平均）
我们限制: 90 QPM（900 / 10min，留 buffer）

理论容量:
  无缓存: 3 次用户查询/分钟 = 180 次/小时
  70%缓存命中: ~10 次用户查询/分钟 = 600 次/小时
```

#### 容量规划
| 场景 | API Keys | 缓存命中率 | 并发用户 | 说明 |
|------|----------|-----------|---------|------|
| 内测阶段 | 1 个 | 无 | 2-3 人 | 需排队 |
| 小规模上线 | 1 个 | 70% | 10-15 人 | 常见查询复用缓存 |
| 正式运营 | 3 个 | 70% | 30-50 人 | 多Key轮换 |

#### 多 API Key 轮换
```python
class MultiKeyRotator:
    """多API Key轮换器"""
    
    def __init__(self, api_keys: list):
        self.api_keys = api_keys
        self.current_index = 0
        self.lock = asyncio.Lock()
    
    async def get_next_key(self) -> dict:
        async with self.lock:
            key = self.api_keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            return key

# 配置
api_keys = [
    {"client_id": "xxx1", "client_secret": "yyy1"},
    {"client_id": "xxx2", "client_secret": "yyy2"},
    {"client_id": "xxx3", "client_secret": "yyy3"},
]
key_rotator = MultiKeyRotator(api_keys)
```

---

## 五、数据结构定义

### 5.1 请求结构
```python
@dataclass
class HotPostSearchRequest:
    """爆帖速递搜索请求"""
    query: str                          # 用户输入的查询
    mode: Optional[str] = None          # 模式: trending/rant/opportunity（可选，系统自动判断）
    subreddits: Optional[List[str]] = None  # 指定社区（可选）
    time_filter: str = "month"          # 时间范围: week/month/year/all
    limit: int = 30                     # 返回帖子数量
```

### 5.2 响应结构
```python
@dataclass
class HotPostSearchResponse:
    """爆帖速递搜索响应"""
    
    # 元信息
    query: str
    mode: str                           # 实际使用的模式
    search_time: str                    # 搜索时间
    from_cache: bool                    # 是否来自缓存
    
    # 一句话洞察
    summary: str
    
    # 核心结果
    top_posts: List[HotPost]            # Top 帖子列表
    key_comments: List[KeyComment]      # 神评论精选
    
    # 聚合分析（根据模式不同）
    pain_points: Optional[List[PainPoint]] = None       # 痛点挖掘模式
    opportunities: Optional[List[Opportunity]] = None   # 机会发现模式
    trending_keywords: Optional[List[str]] = None       # 热点追踪模式
    
    # 延伸线索
    communities: List[CommunityInfo]    # 相关社区
    related_queries: List[str]          # 相关查询建议

@dataclass
class HotPost:
    """热帖数据结构"""
    rank: int
    id: str
    title: str
    body_preview: str                   # 正文预览（前300字符）
    score: int
    num_comments: int
    subreddit: str
    author: str
    reddit_url: str
    created_utc: float
    
    # 信号分析
    signals: List[str]                  # 检测到的信号词
    signal_score: float                 # 信号强度分
    
    # Top评论
    top_comments: List[Dict[str, Any]]

@dataclass
class PainPoint:
    """痛点数据结构"""
    category: str                       # 痛点类别
    description: str                    # 描述
    mentions: int                       # 提及次数
    severity: str                       # 严重程度: high/medium/low
    sample_quotes: List[str]            # 示例引用
    evidence_urls: List[str]            # 证据链接
```

---

## 六、信号词库

> 词库不硬编码，统一存放在 `backend/config/boom_post_keywords.yaml`  
> 本节示例仅用于展示结构与字段，不参与运行，真实词库以配置文件为准。

### 6.1 吐槽信号词（Rant Mode）
```python
RANT_SIGNALS = {
    "strong": [
        "worst purchase", "never again", "total waste"
    ],
    "medium": [
        "disappointed", "frustrating", "overpriced"
    ],
    "weak": [
        "could be better", "a bit slow", "not ideal"
    ]
}
```

### 6.2 机会信号词（Opportunity Mode）
```python
OPPORTUNITY_SIGNALS = {
    "seeking": [
        "looking for", "need a recommendation", "any recommendations"
    ],
    "unmet_need": [
        "i wish there was", "no good solution", "frustrating that"
    ],
    "resonance": [
        "me too", "same here", "following"
    ]
}
```

### 6.3 推荐信号词（Discovery Mode）
```python
DISCOVERY_SIGNALS = {
    "positive": [
        "highly recommend", "love this", "works great"
    ],
    "hidden_gem": [
        "underrated", "hidden gem", "slept on"
    ]
}
```

---

## 七、API 参数说明

### 7.0 接口路径
```
POST /api/hotpost/search          # 发起搜索（同步返回结果）
GET  /api/hotpost/result/{query_id}  # 获取缓存结果（用于刷新/复用）
POST /api/hotpost/deepdive        # 生成深挖 token（需登录）
```

### 7.1 搜索参数
```yaml
品牌关键词: 用户输入，经 LLM 或规则解析后的核心词
目标社区: 自动推荐或用户指定（最多5个）
时间范围: week / month / year / all（默认随模式，见 9.2）
每社区最多: 100-300 条帖子
每次API limit: 100 条
排序方式: 
  - 热点模式: top / hot
  - 痛点模式: top
  - 机会模式: relevance + top

过滤条件:
  最低点赞数: 10-100（根据模式调整）
  最低评论数: 5-20
  必须包含信号词: 是（痛点/机会模式）
  
评论抓取:
  每帖评论数: 3 条
  评论排序: top（按点赞数）
  实际抓取: 前20条帖子的评论
```

### 7.2 单次查询消耗
```yaml
典型场景（3个社区，Top 30帖子）:

搜索阶段:
  3 个社区 × 1-3 次分页 = 3-9 次请求

评论抓取:
  20 条帖子 × 1 次请求 = 20 次请求

总计: 23-29 次请求 ≈ 30 次请求
```

---

## 八、部署清单

### 8.1 依赖服务
```yaml
必须:
  - Redis（缓存 + 队列状态）
  - PostgreSQL（查询日志、用户偏好）
  
可选:
  - LLM API（如需 summary/key_takeaway 等归纳文本；未配置则按 11.4 降级输出）
```

### 8.2 配置项
```python
# .env 配置
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=yyy
REDDIT_USER_AGENT="RedditHotPost/1.0"

# 限流配置（与 10min 窗口一致）
RATE_LIMIT_MAX_REQUESTS=900
RATE_LIMIT_WINDOW_SECONDS=600

# 缓存配置
CACHE_TTL_TRENDING=1800      # 30分钟
CACHE_TTL_RANT=7200          # 2小时
CACHE_TTL_OPPORTUNITY=3600   # 1小时

# 中文关键词解析（LLM）
ENABLE_HOTPOST_QUERY_TRANSLATION=true
HOTPOST_QUERY_TRANSLATE_TTL_SECONDS=86400
HOTPOST_QUERY_TRANSLATE_MAX_TOKENS=200

# 多Key配置（可选）
REDDIT_API_KEYS='[{"client_id":"xxx1","secret":"yyy1"},{"client_id":"xxx2","secret":"yyy2"}]'
```

### 8.3 监控指标
```yaml
业务指标:
  - 日查询量
  - 查询类型分布（trending/rant/opportunity）
  - 热门查询词 Top 20
  - 缓存命中率

技术指标:
  - API 调用次数 / 分钟
  - 429 错误次数
  - 平均响应时间
  - 队列等待时长
```

---

## 九、范围与口径（Scope & Standards）

### 9.1 数据覆盖范围

| 维度 | 覆盖范围 | 说明 |
|------|---------|------|
| **内容类型** | 帖子（Posts）+ 评论（Comments） | 每个帖子抓取 Top 3 评论 |
| **帖子类型** | Self-posts + Link-posts | 均支持，优先展示有正文的帖子 |
| **NSFW 内容** | ❌ 不包含 | 默认过滤 `over_18=true` 的帖子和社区 |
| **删除/存档帖** | ❌ 不包含 | 只抓取可访问的公开帖子 |
| **私域社区** | ❌ 不包含 | 只覆盖公开（public）社区 |

### 9.2 时间窗口口径

| 参数值 | 含义 | 默认优先级 | 适用场景 |
|--------|------|-----------|---------|
| `week` | 最近 7 天 | ⭐ 热点追踪模式默认 | 追踪最新热点 |
| `month` | 最近 30 天 | ⭐ 机会发现模式默认 | 中等时间跨度 |
| `year` | 最近 365 天 | - | 长期趋势分析 |
| `all` | 全时段 | ⭐ 痛点挖掘模式默认 | 口碑累积分析 |

**默认值逻辑**:
```python
DEFAULT_TIME_FILTER = {
    "trending": "week",      # 热点追踪 → 最近一周
    "rant": "all",           # 痛点挖掘 → 全时段
    "opportunity": "month"   # 机会发现 → 最近一个月
}
```

### 9.3 语言与地区

| 维度 | 规则 | 说明 |
|------|------|------|
| **语言** | 仅英文 | 默认只搜索英文内容，非英文帖子不纳入结果 |
| **地区** | 不限制 | Reddit 无地区限制，但用户群以北美/欧洲为主 |
| **非英文社区** | 排除 | 如 `r/de`、`r/france` 等非英文社区不纳入默认搜索范围 |

**后续扩展**：支持多语言时，需新增 `language` 参数，并维护各语言的信号词库。

### 9.4 结果性质定义

> ⚠️ **重要声明**：本模块输出的是「**线索/证据预览**」，而非「**趋势/口碑结论**」。

| 属性 | 说明 |
|------|------|
| **结果性质** | 证据线索预览（Evidence Preview） |
| **非定论** | 不代表完整市场调研，仅为快速验证入口 |
| **需人工判断** | 用户需结合业务场景自行判断证据有效性 |
| **不可引用** | 结果不应直接用于正式报告，需经深度分析验证 |

**UI 提示语**：
```
⚠️ 以下结果为 Reddit 公开讨论的快速预览，仅供参考线索，不代表完整市场结论。
如需深度分析，请使用「市场洞察报告」功能。
```

---

## 十、可信度与提示规则（Confidence & Hints）

### 10.1 可信度等级定义

| 等级 | 条件 | 描述 | UI 展示 |
|------|------|------|---------|
| 🟢 **高可信** | 证据 ≥ 20 条，社区 ≥ 3 个 | 样本充足，结论可参考 | 正常展示 |
| 🟡 **中可信** | 证据 10-19 条 | 样本有限，仅供参考 | 展示 + 黄色提示 |
| 🔴 **低可信** | 证据 < 10 条 | 样本不足，结论不可靠 | 展示 + 红色警告 |
| ⚪ **无结果** | 证据 = 0 条 | 未找到相关讨论 | 空状态引导 |

### 10.2 证据数量门槛

```python
EVIDENCE_THRESHOLDS = {
    "high_confidence": 20,      # ≥20 条 → 高可信
    "medium_confidence": 10,    # 10-19 条 → 中可信
    "low_confidence": 1,        # 1-9 条 → 低可信
    "no_result": 0              # 0 条 → 无结果
}

def get_confidence_level(evidence_count: int) -> str:
    if evidence_count >= 20:
        return "high"
    elif evidence_count >= 10:
        return "medium"
    elif evidence_count >= 1:
        return "low"
    else:
        return "none"
```

### 10.3 可信度提示文案

```yaml
high:
  badge: "🟢 样本充足"
  message: null  # 无需额外提示

medium:
  badge: "🟡 样本有限"
  message: "当前结果基于 {count} 条讨论，建议结合其他渠道验证。"

low:
  badge: "🔴 样本不足"
  message: "仅找到 {count} 条相关讨论，结论可能不具代表性。建议更换关键词或扩大搜索范围。"

none:
  badge: null
  message: null  # 走无结果页面
```

### 10.4 LLM 摘要的可信度要求

| 条件 | LLM 摘要行为 |
|------|-------------|
| 高可信（≥20条） | ✅ 生成完整摘要 |
| 中可信（10-19条） | ⚠️ 生成摘要，但加前缀「基于有限样本」 |
| 低可信（<10条） | ❌ 不生成摘要，使用模板文案 |

---

## 十一、异常与降级体验（Error Handling & Fallback）

### 11.1 无结果场景

**触发条件**：`evidence_count == 0`

**UI 展示**：
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  😔 未找到相关讨论                                           │
│                                                             │
│  关于「{query}」的 Reddit 讨论较少，可能原因：               │
│  • 该话题在 Reddit 上讨论度较低                              │
│  • 关键词过于具体或拼写有误                                  │
│                                                             │
│  💡 建议尝试：                                               │
│  • 使用更通用的关键词                                        │
│  • 尝试英文品牌名/产品名                                     │
│  • 扩大时间范围                                              │
│                                                             │
│           [🔄 修改关键词重试]    [📋 反馈问题]              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 限流/排队场景

**触发条件**：请求进入排队队列

**UI 展示**：
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ⏳ 请求排队中                                               │
│                                                             │
│  当前系统繁忙，您的请求已加入队列。                          │
│                                                             │
│  📊 队列位置：第 {position} 位                               │
│  ⏱️ 预计等待：约 {wait_time} 秒                              │
│                                                             │
│  ┌──────────────────────────────────────┐                   │
│  │ ████████░░░░░░░░░░░░░░░░░░░░░░ 30%   │                   │
│  └──────────────────────────────────────┘                   │
│                                                             │
│  💡 小提示：热门查询会被缓存，换个关键词可能更快哦~          │
│                                                             │
│                        [❌ 取消请求]                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**SSE 推送**（与主系统 PRD-02 保持一致）：
```
event: queue_update
data: {"position":3,"estimated_wait_seconds":45,"status":"waiting"}

event: progress
data: {"position":1,"estimated_wait_seconds":10,"status":"processing"}

event: completed
data: {"query_id":"uuid-xxx","status":"success"}
```

> 📌 **协议选择说明**：统一使用 SSE，不使用 WebSocket。原因：与主系统保持一致，降低前端/网关复杂度。如需变更请提交 ADR。

### 11.3 Reddit API 异常

| 错误类型 | HTTP 状态码 | 用户提示 | 系统行为 |
|---------|------------|---------|---------|
| 限流 | 429 | "Reddit 服务繁忙，请稍后重试" | 指数退避重试（最多3次） |
| 服务不可用 | 5xx | "Reddit 服务暂时不可用" | 返回缓存结果（如有） |
| 认证失败 | 401/403 | "系统配置异常，请联系管理员" | 告警通知运维 |
| 超时 | Timeout | "请求超时，请重试" | 记录日志，返回部分结果 |

**降级策略**：
```python
async def search_with_fallback(query: str, mode: str):
    try:
        # 1. 尝试实时搜索
        return await search_reddit(query, mode)
    except RateLimitError:
        # 2. 尝试返回缓存（即使过期）
        stale_cache = await redis.get(cache_key)
        if stale_cache:
            return {
                "data": json.loads(stale_cache),
                "from_stale_cache": True,
                "warning": "数据可能不是最新的，请稍后刷新"
            }
        # 3. 无缓存，返回错误
        raise ServiceBusyError("Reddit 服务繁忙，请稍后重试")
    except RedditAPIError as e:
        # 4. 其他错误，记录并返回友好提示
        logger.error(f"Reddit API Error: {e}")
        raise ServiceError("Reddit 服务暂时不可用，请稍后重试")
```

### 11.4 LLM 降级策略

**无 LLM 时的降级输出**：

| 字段 | 有 LLM | 无 LLM 降级 |
|------|--------|------------|
| `summary` | LLM 生成的一句话洞察 | 模板文案：「找到 {count} 条相关讨论，涉及 {communities} 个社区」 |
| `pain_points` | LLM 归纳的痛点聚类 | 按信号词分组统计：「broken 相关 X 条，terrible 相关 Y 条」 |
| `key_insights` | LLM 推理的核心洞察 | 不输出该字段，或标记「需深度分析」 |

```python
def generate_fallback_summary(result: SearchResult) -> str:
    """无 LLM 时的降级摘要"""
    return (
        f"找到 {result.evidence_count} 条相关讨论，"
        f"来自 {len(result.communities)} 个社区。"
        f"高频信号词：{', '.join(result.top_signals[:3])}。"
    )
```

---

## 十二、与主系统衔接（System Integration）

### 12.1 模块定位声明

> 📌 **本模块是轻量级入口**，不是深度分析系统。
> - 不直接写入 `reports/` 或 `insights/` 目录
> - 不替代「市场洞察报告」功能
> - 可作为深度分析的「线索入口」

### 12.2 社区池反哺规则

**触发条件**：搜索结果中发现未在 `community_pool` 中的社区

**写入规则**：
```python
async def maybe_discover_community(
    subreddit: str,
    evidence_count: int,
    *,
    keywords: list[str],
    query: str | None,
    task_id: UUID | None = None,
):
    """
    将发现的社区写入 discovered_communities 表
    仅作为候选，不直接加入 community_pool
    """
    if evidence_count < 5:
        return  # 证据太少，不写入
    
    existing = await db.get_community(subreddit)
    if existing:
        return  # 已存在，跳过
    
    now = datetime.now(timezone.utc)
    await db.insert("discovered_communities", {
        "name": subreddit,
        "discovered_from_keywords": {            # 真实字段
            "source": "hotpost",
            "query": query,
            "keywords": keywords
        },
        "discovered_count": evidence_count,      # 真实字段
        "first_discovered_at": now,              # 真实字段
        "last_discovered_at": now,               # 真实字段
        "status": "pending",                     # 待评估
        "discovered_from_task_id": task_id       # 可为空
    })
```

**字段说明**：
| 字段 | 说明 |
|------|------|
| `discovered_from_keywords` | JSON，包含 `source/query/keywords`，统一归档发现来源 |
| `discovered_count` | 该社区在本次搜索中贡献的帖子数 |
| `first_discovered_at` | 首次发现时间 |
| `last_discovered_at` | 最近一次发现时间 |
| `status` | `pending` → 待评估，后续由 `CommunityEvaluator` 处理 |
| `discovered_from_task_id` | 关联任务（可为空） |

### 12.3 深度分析入口

**是否提供「深挖入口」**：✅ 是

**说明**：深挖报告由主系统生成（走 `/api/analyze` 主链路），本模块仅生成 `deepdive_token` 并写入 Redis 种子数据。

**触发条件**：结果可信度 ≥ 中（≥10条证据）

**UI 展示**：
```
┌─────────────────────────────────────────────────────────────┐
│  💡 需要更深入的分析？                                       │
│                                                             │
│  当前为快速预览结果。如需完整的市场洞察报告，包含：          │
│  • 痛点聚类分析                                              │
│  • 竞品对比                                                  │
│  • 用户画像                                                  │
│  • 趋势预测                                                  │
│                                                             │
│                    [📊 生成深度报告]                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**点击行为**：
1. 生成 `deepdive_token`，将种子数据写入 Redis 临时会话（TTL 30min）
2. 跳转到报告生成页面，自动填充 `product_desc` 和推荐社区
3. 用户确认后触发完整的 T1 报告生成流程

### 12.4 数据隔离原则

| 操作 | 本模块是否执行 | 说明 |
|------|---------------|------|
| 写入 `posts_raw` | ❌ 否 | 不污染主数据采集表 |
| 写入 `comments` | ❌ 否 | 评论正文不落库 |
| 写入 `reports/` 目录 | ❌ 否 | 本模块不生成报告文件 |
| 写入 `insights/` 目录 | ❌ 否 | |
| 写入 `evidence_posts` | ✅ 是 | 复用主系统证据表，`probe_source='hotpost'` |
| 写入 `discovered_communities` | ✅ 是 | 仅 pending 状态，不进入 community_pool、不触发抓取 |
| 写入 `hotpost_queries` | ✅ 是 | 查询元数据 |
| 写入 `hotpost_query_evidence_map` | ✅ 是 | 查询-证据映射 |
| Redis 临时缓存 | ✅ 是 | 评论正文、深挖会话（TTL 自动过期） |

---

## 十三、数据资产与入库（Data Assets）

> ⚠️ **核心原则：爆帖速递不创建独立证据资产体系，复用主系统 `evidence_posts` 表。**

### 13.1 入库策略

| 数据类型 | 是否入库 | 目标表/存储 | 说明 |
|---------|---------|------------|------|
| 查询记录 | ✅ 是 | `hotpost_queries` | 记录用户查询元数据 |
| 证据帖子 | ✅ 是 | `evidence_posts`（主系统） | 复用主系统资产，`probe_source='hotpost'` |
| 查询-证据映射 | ✅ 是 | `hotpost_query_evidence_map` | 记录查询用到了哪些证据 |
| **评论正文** | ❌ **不落库** | Redis 临时缓存 | 合规要求，详见 13.5 |
| 发现的社区 | ✅ 是 | `discovered_communities` | 仅写入 pending 状态，不进入 community_pool |
| 深挖会话 | ❌ 否 | Redis 临时会话 | TTL ≤ 30min，详见 13.6 |

### 13.2 查询元数据表（hotpost_queries）

```sql
CREATE TABLE hotpost_queries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 查询信息
    query           TEXT NOT NULL,                  -- 用户输入的查询
    mode            VARCHAR(20) NOT NULL,           -- trending/rant/opportunity
    time_filter     VARCHAR(10) NOT NULL,           -- week/month/year/all
    subreddits      TEXT[],                         -- 搜索的社区列表
    
    -- 用户信息
    user_id         UUID,                           -- 用户ID（可为空=未登录）
    session_id      VARCHAR(64),                    -- 会话ID
    ip_hash         VARCHAR(64),                    -- IP 哈希（脱敏）
    
    -- 结果统计（由代码计算，非 LLM）
    evidence_count  INT NOT NULL DEFAULT 0,         -- 证据数量
    community_count INT NOT NULL DEFAULT 0,         -- 涉及社区数
    confidence      VARCHAR(10),                    -- high/medium/low/none
    
    -- 性能指标
    from_cache      BOOLEAN NOT NULL DEFAULT FALSE, -- 是否来自缓存
    latency_ms      INT,                            -- 响应耗时（毫秒）
    api_calls       INT,                            -- Reddit API 调用次数
    
    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 索引
    INDEX idx_hotpost_query_created (created_at DESC),
    INDEX idx_hotpost_query_mode (mode),
    INDEX idx_hotpost_query_user (user_id)
);
```

### 13.3 查询-证据映射表（hotpost_query_evidence_map）

> 📌 **不新建证据帖子表**，仅记录查询与 `evidence_posts` 的关联关系。

```sql
CREATE TABLE hotpost_query_evidence_map (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id        UUID NOT NULL REFERENCES hotpost_queries(id) ON DELETE CASCADE,
    evidence_id     BIGINT NOT NULL REFERENCES evidence_posts(id),  -- 引用主系统证据表（int）
    
    -- 查询特定信息（同一证据在不同查询中可能有不同排名/分数）
    rank            INT,                            -- 在本次查询结果中的排名
    signal_score    FLOAT,                          -- 信号强度分（本次计算）
    signals         TEXT[],                         -- 检测到的信号词
    
    -- 评论引用（仅存引用，不存正文）
    top_comment_refs JSONB,                         -- [{comment_fullname, permalink, score}]
    
    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 索引
    INDEX idx_map_query (query_id),
    INDEX idx_map_evidence (evidence_id),
    UNIQUE idx_map_unique (query_id, evidence_id)
);
```

### 13.4 证据帖子写入主系统（evidence_posts）

```python
# 写入 evidence_posts 时的 probe_source 标记
async def save_evidence_to_main_system(post_data: dict, query_id: str, query_text: str):
    """
    将证据帖子写入主系统 evidence_posts 表
    如果已存在则更新，不重复插入
    """
    # 以 (probe_source + source_query_hash + source_post_id) 为唯一键去重
    source_query = normalize_query(query_text)  # lower + strip + collapse spaces
    source_query_hash = sha256(source_query.encode()).hexdigest()
    existing = await db.get_evidence_by_unique_key(
        probe_source="hotpost",
        source_query_hash=source_query_hash,
        source_post_id=post_data["id"],
    )
    
    if existing:
        # 已存在：仅建立映射关系
        evidence_id = existing.id
    else:
        # 不存在：写入主系统
        evidence_id = await db.insert("evidence_posts", {
            "probe_source": "hotpost",
            "source_query": source_query,
            "source_query_hash": source_query_hash,
            "source_post_id": post_data["id"],
            "subreddit": post_data["subreddit"],
            "title": post_data["title"],
            "summary": post_data.get("selftext", "")[:2000] or None,
            "score": post_data["score"],
            "num_comments": post_data["num_comments"],
            "post_created_at": datetime.fromtimestamp(
                post_data["created_utc"], tz=timezone.utc
            ),
            "evidence_score": int(post_data.get("signal_score", 0)),
        })
    
    # 建立映射关系
    await db.insert("hotpost_query_evidence_map", {
        "query_id": query_id,
        "evidence_id": evidence_id,
        "rank": post_data["rank"],
        "signal_score": post_data["signal_score"],
        "signals": post_data["signals"]
    })

# URL 不入库：前端展示时可使用 https://reddit.com/comments/{source_post_id}
```

### 13.5 评论数据策略（合规要求）

> ⚠️ **评论正文不落 PostgreSQL，仅做临时缓存。**

#### 合规背景
根据 [Reddit API Terms](https://www.reddit.com/wiki/api)：
- 必须在合理时间内删除已删除/编辑的用户内容
- 官方建议：持有用户内容不超过 48 小时

#### 我们的做法
```yaml
评论正文:
  存储位置: Redis 临时缓存
  TTL: 2 小时（远低于 48 小时建议）
  用途: 前端展示 + LLM 输入
  落库: ❌ 不落 PostgreSQL

评论引用:
  存储位置: hotpost_query_evidence_map.top_comment_refs
  内容: 仅 comment_fullname（t1_xxx） + permalink + score（无正文）
  用途: 可溯源、可重新拉取
```

#### Redis 缓存结构
```python
# Key: hotpost:comments:{query_id}
# TTL: 7200 秒（2小时）
# Value: 
{
    "evidence_id_1": [
        {"comment_fullname": "t1_abc123", "author": "u/xxx", "body": "评论正文...", "score": 123},
        {"comment_fullname": "t1_def456", "author": "u/yyy", "body": "评论正文...", "score": 89}
    ],
    "evidence_id_2": [...]
}
```

### 13.6 临时会话存储（深挖入口）

> 📌 **不使用 PostgreSQL "临时表"，用 Redis 临时会话。**

#### 用途
用户点击"生成深度报告"时，需要把当前查询的种子数据传递给主系统报告生成流程。

#### 存储结构
```yaml
存储位置: Redis
Key: hotpost:deepdive:{token}
TTL: 30 分钟
Value:
  query_id: "uuid-xxx"                    # 原查询ID
  seed_posts: ["post_id_1", "post_id_2"]  # 种子帖子（仅ID，不含正文）
  seed_subreddits: ["r/xxx", "r/yyy"]     # 推荐社区
  product_desc_suggestion: "..."           # 预填产品描述
  created_at: "2026-01-28T17:30:00Z"
  user_id: "uuid-user" or null
```

#### 使用流程
```python
# 1. 用户点击"生成深度报告"
token = generate_token()
await redis.setex(
    f"hotpost:deepdive:{token}",
    1800,  # 30分钟
    json.dumps({
        "query_id": query_id,
        "seed_posts": [p["id"] for p in top_posts[:20]],
        "seed_subreddits": list(communities),
        "product_desc_suggestion": query
    })
)
# 返回 token 给前端

# 2. 前端跳转到报告生成页，带上 token
# /report/generate?deepdive_token=xxx

# 3. 报告生成页从 Redis 读取种子数据，预填表单
session = await redis.get(f"hotpost:deepdive:{token}")
```

### 13.7 数据保留周期

| 存储 | 数据 | 保留周期 | 清理策略 |
|-----|------|---------|---------|
| PostgreSQL | `hotpost_queries` | 90 天 | 定时任务每周清理 |
| PostgreSQL | `hotpost_query_evidence_map` | 90 天 | 随 query 级联删除 |
| PostgreSQL | `evidence_posts`（主系统） | 永久 | 由主系统管理 |
| Redis | 评论缓存 | 2 小时 | TTL 自动过期 |
| Redis | 深挖会话 | 30 分钟 | TTL 自动过期 |

**清理脚本**：
```sql
-- 每周运行一次
DELETE FROM hotpost_queries 
WHERE created_at < NOW() - INTERVAL '90 days';

-- 映射表通过外键级联删除
```

---

## 十四、合规与限流（Compliance & Rate Limiting）

### 14.1 Reddit API 官方限额

根据 [Reddit Data API 官方文档](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki):

| 限制项 | 官方值 | 我们的策略 |
|-------|-------|-----------|
| **请求频率** | 100 QPM / OAuth client id（10分钟滚动平均） | 90 QPM（900/10min，留 buffer） |
| **统计窗口** | 10 分钟滚动平均（支持短时 burst） | 同官方，使用 600 秒窗口 |
| **监控 Header** | X-Ratelimit-Used / Remaining / Reset | 解析 header 动态调整 |
| **User-Agent** | 必须包含应用名和版本 | `RedditHotPost/1.0 by /u/xxx` |
| **数据使用** | 不得违反 Reddit TOS，需处理删除内容 | 评论正文不落库，仅临时缓存 |

### 14.2 本模块限流策略与官方一致性

```yaml
官方限制: 
  额度: 100 QPM / client_id
  窗口: 10 minutes rolling average
  
本模块限制:
  额度: 90 QPM（等效 900 / 10min）
  窗口: 600 seconds（与官方一致）
  Buffer: 10% 预留

一致性: ✅ 
说明: 
  - 使用 10 分钟窗口，贴近官方统计逻辑
  - 留 10% buffer 以防时间窗口边界、网络延迟等问题
  - 动态读取 X-Ratelimit-* header 进行自适应调整

QPM 定义:
  QPM = API 请求次数（API calls per minute）
  一次用户查询可能消耗 N 次 API calls
  用户查询容量 ≈ QPM / 30（平均每查询 30 次 API call）
```

### 14.3 多 API Key 轮换合规性

> ⚠️ **合规风险说明**

根据 Reddit API Terms，以下行为可能违规：
- 使用多个账号/应用来规避限流
- 自动化批量注册应用以获取更多配额

**我们的做法**：
1. 每个 API Key 对应一个**真实的业务场景**（如 production / staging / analytics）
2. Key 轮换是为了**故障隔离**，而非规避限流
3. 总请求量不超过合理业务需求
4. 需在 Reddit 应用描述中如实说明用途

**配置要求**：
```python
# 每个 Key 的用途必须明确
API_KEYS = [
    {"client_id": "xxx1", "purpose": "production", "description": "Main production app"},
    {"client_id": "xxx2", "purpose": "staging", "description": "Staging/testing environment"},
]

# 日志记录 Key 使用情况，便于审计
logger.info(f"Using API Key for {key['purpose']}")
```

---

## 十五、安全与权限（Security & Access Control）

### 15.1 登录/未登录可用范围

| 功能 | 未登录 | 已登录 |
|------|-------|-------|
| 搜索查询 | ✅ 可用（有限制） | ✅ 可用 |
| 查看结果 | ✅ 可用 | ✅ 可用 |
| 查看评论 | ✅ 可用 | ✅ 可用 |
| 每日查询次数 | 10 次/IP | 50 次/用户 |
| 历史记录 | ❌ 不可用 | ✅ 可用 |
| 收藏功能 | ❌ 不可用 | ✅ 可用 |
| 深度报告入口 | ❌ 不可用 | ✅ 可用 |

### 15.2 频率限制（用户级）

```python
USER_RATE_LIMITS = {
    "anonymous": {
        "max_queries_per_day": 10,
        "max_queries_per_hour": 5,
        "cooldown_after_limit": 3600  # 触发限制后等待1小时
    },
    "authenticated": {
        "max_queries_per_day": 50,
        "max_queries_per_hour": 20,
        "cooldown_after_limit": 1800  # 触发限制后等待30分钟
    },
    "premium": {
        "max_queries_per_day": 200,
        "max_queries_per_hour": 50,
        "cooldown_after_limit": 600
    }
}
```

### 15.3 滥用风控策略

| 风险场景 | 检测规则 | 处置措施 |
|---------|---------|---------|
| 高频请求 | 同一 IP 1分钟内 > 10 次 | 触发 CAPTCHA |
| 批量爬取 | 同一用户 5分钟内 > 30 次 | 临时封禁 1 小时 |
| 恶意关键词 | 查询包含敏感词 | 记录日志，不返回结果 |
| 异常模式 | 短时间内大量不同 IP 查询相同关键词 | 人工审核 |

**实现示例**：
```python
async def check_abuse(user_id: str, ip: str, query: str) -> bool:
    """检查是否存在滥用行为"""
    
    # 1. 检查 IP 频率
    ip_count = await redis.incr(f"abuse:ip:{ip}:minute", ex=60)
    if ip_count > 10:
        await trigger_captcha(ip)
        return True
    
    # 2. 检查用户频率
    user_count = await redis.incr(f"abuse:user:{user_id}:5min", ex=300)
    if user_count > 30:
        await temp_ban_user(user_id, duration=3600)
        return True
    
    # 3. 检查敏感词
    if contains_sensitive_words(query):
        logger.warning(f"Sensitive query detected: {query}")
        return True
    
    return False
```

### 15.4 数据脱敏

| 数据类型 | 脱敏规则 |
|---------|---------|
| IP 地址 | 存储哈希值，不存储原始 IP |
| 用户 ID | 仅记录内部 ID，不关联外部信息 |
| 查询内容 | 原样存储，用于分析热门查询 |
| Reddit 用户名 | 原样展示（公开信息） |

---

## 十六、指标与验收（Metrics & Acceptance）

### 16.1 核心业务指标

| 指标 | 定义 | 目标值 | 计算公式 |
|------|------|-------|---------|
| **命中率** | 有结果的查询比例 | ≥ 80% | `有结果查询数 / 总查询数` |
| **高可信率** | 高可信结果比例 | ≥ 50% | `高可信查询数 / 有结果查询数` |
| **缓存命中率** | 缓存命中比例 | ≥ 60% | `缓存命中数 / 总查询数` |
| **空结果率** | 无结果查询比例 | ≤ 20% | `无结果查询数 / 总查询数` |

### 16.2 性能指标

| 指标 | 定义 | 目标值（P95） |
|------|------|-------------|
| **缓存命中响应时间** | 从请求到返回 | ≤ 200ms |
| **缓存未命中响应时间** | 从请求到返回 | ≤ 30s |
| **平均等待时间** | 排队等待时间 | ≤ 60s |
| **API 错误率** | Reddit API 调用失败比例 | ≤ 5% |

### 16.3 MVP 验收标准

| 序号 | 验收项 | 标准 | 验证方式 |
|------|-------|------|---------|
| 1 | 基础查询功能 | 输入关键词，返回 Top 10 帖子 | 功能测试 |
| 2 | 三种模式切换 | 支持 trending/rant/opportunity 模式 | 功能测试 |
| 3 | 缓存命中响应 | ≤ 200ms | 性能测试 |
| 4 | 非缓存响应 | ≤ 30s | 性能测试 |
| 5 | 最小证据数 | 每次查询至少返回 1 条帖子（有结果时） | 功能测试 |
| 6 | 错误处理 | 429/5xx 有友好提示 | 异常测试 |
| 7 | 限流生效 | 超过 90 QPM（≈900/10min）时排队 | 压力测试 |
| 8 | 稳定性 | 连续运行 24 小时无崩溃 | 稳定性测试 |

### 16.4 监控告警阈值

| 指标 | 告警阈值 | 级别 |
|------|---------|------|
| 空结果率 | > 30% （持续 1 小时） | P2 |
| API 错误率 | > 10% （持续 10 分钟） | P1 |
| 平均响应时间 | > 60s （持续 5 分钟） | P1 |
| 队列积压 | > 20 个请求 | P2 |
| Redis 连接失败 | 任意 | P0 |

---

## 十七、LLM 报告生成架构（Report Generation）

### 17.1 整体架构：共用底座 + 模式专用模块

```
┌─────────────────────────────────────────────────────────────┐
│                    基础底座（共用）                          │
│  ─────────────────────────────────────────────────────────  │
│  • 角色定义（市场洞察分析师）                                │
│  • 证据溯源规则（每个结论必须有 URL）                        │
│  • 可信度规则（≥20条/10-19条/<10条）                        │
│  • 输出格式规范（JSON Schema）                              │
│  • 禁止编造规则                                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ 🔥 热点模块   │   │ 💢 痛点模块   │   │ 💡 机会模块   │
│ trending.py   │   │ rant.py       │   │ opportunity.py│
├───────────────┤   ├───────────────┤   ├───────────────┤
│ • 热度排序    │   │ • 情绪分析    │   │ • 需求识别    │
│ • 趋势判断    │   │ • 痛点聚类    │   │ • 共鸣统计    │
│ • 关键词提取  │   │ • 竞品提及    │   │ • 方案对比    │
│ • 专用Schema  │   │ • 专用Schema  │   │ • 专用Schema  │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 17.2 数据流程

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. Reddit API 搜索                                                  │
│     └── 获取帖子 + 评论原始数据                                      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. 数据处理 → JSON                                                  │
│     └── 清洗、过滤、结构化为 JSON 字符串                             │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. 拼接 Prompt                                                      │
│     └── 基础规则 + 模式专用规则 + JSON 数据                          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. 调用 LLM API（OpenRouter）                                       │
│     └── 发送拼接好的 Prompt，获取结构化响应                          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. 解析 & 返回                                                      │
│     └── 解析 JSON 响应，校验格式，返回前端                           │
└─────────────────────────────────────────────────────────────────────┘
```

**代码示例**：
```python
import json
from openai import OpenAI

# 1. 数据处理成 JSON
posts_json = json.dumps(posts_data, ensure_ascii=False)
comments_json = json.dumps(comments_data, ensure_ascii=False)

# 2. 拼接 Prompt
prompt = RANT_PROMPT.format(
    query="Adobe",
    posts_json=posts_json,        # JSON 数据嵌入 Prompt
    comments_json=comments_json
)

# 3. 调用 LLM API（OpenRouter）
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

response = client.chat.completions.create(
    model="x-ai/grok-3-mini-beta",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)

# 4. 解析响应
report = json.loads(response.choices[0].message.content)
```

### 17.3 OpenRouter API 配置

```python
# .env 配置
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
OPENROUTER_MODEL=x-ai/grok-3-mini-beta    # 默认模型
OPENROUTER_FALLBACK_MODEL=anthropic/claude-3-haiku  # 降级模型

# 模型选择策略
LLM_CONFIG = {
    "primary": {
        "model": "x-ai/grok-3-mini-beta",
        "max_tokens": 4096,
        "temperature": 0.3  # 低温度，保证输出稳定
    },
    "fallback": {
        "model": "anthropic/claude-3-haiku",
        "max_tokens": 4096,
        "temperature": 0.3
    }
}
```

### 17.4 共用底座 Prompt（Base Rules）

```python
BASE_RULES = """
## 通用规则（所有模式必须遵守）

### 1. 证据溯源规则
- 每个结论必须附带原帖 URL
- 引用必须是原文，不可改写或编造
- 格式：[帖子标题](URL) + 原文引用

### 2. 可信度判断规则
| 证据数量 | 可信度等级 | 输出行为 |
|---------|-----------|---------|
| ≥20 条 | high | 可以给出预览级结论（仍非定论） |
| 10-19 条 | medium | 结论前加"基于有限样本" |
| <10 条 | low | 仅列举证据，不给结论性洞察 |

### 3. 禁止编造规则
- 不可编造帖子/评论内容
- 不可编造统计数字
- 不可引入外部知识（仅基于输入数据）
- 如果数据不足，请说明“样本有限，仅供预览”

### 4. 措辞规范
- 使用"用户普遍认为"而非"事实是"
- 使用"根据讨论显示"而非"确定"
- 使用"约 X%"而非精确百分比（除非有准确统计）

### 5. 输出格式规范
- 必须输出合法 JSON
- 严格遵守给定的 JSON Schema
- 所有 URL 必须是完整的 https://reddit.com/... 格式
"""
```

---

### 17.5 🔥 热点追踪 Prompt（Trending Mode）

```python
TRENDING_PROMPT = BASE_RULES + """
# 角色
你是一个市场趋势分析师，负责分析 Reddit 上的热点讨论趋势。

# 输入数据
- 查询主题: {query}
- 时间范围: {time_filter}
- 帖子数据: 
```json
{posts_json}
```
- 评论数据:
```json
{comments_json}
```

# 分析任务
1. **识别热点话题**：从帖子中归纳出 3-5 个核心讨论话题
2. **判断时间趋势**：每个话题是"新兴🆕"、"持续热门"还是"下降中↓"
3. **提取关键词**：识别高频出现的产品名、概念、术语（5-10个）
4. **社区分布**：统计讨论主要发生在哪些社区

# 输出规则
- 每个话题必须附带 2-3 个证据帖子（含完整URL）
- 趋势判断基于帖子发布时间分布
- 如果证据不足，在 key_takeaway 中说明“样本有限，仅供预览”
- heat_score = score + num_comments * 2

# 输出格式（严格遵守此 JSON Schema）
{
  "summary": "string - 一句话概括本周热点（50字以内）",
  "confidence": "high | medium | low",
  "evidence_count": "number - 总证据数",
  "topics": [
    {
      "rank": "number - 排名1-5",
      "topic": "string - 话题名称",
      "heat_score": "number - 热度分",
      "time_trend": "新兴🆕 | 持续热门 | 下降中↓",
      "key_takeaway": "string - 核心观点（一句话）",
      "evidence": [
        {
          "title": "string - 原帖标题",
          "score": "number",
          "comments": "number",
          "subreddit": "string - r/xxx",
          "url": "string - 完整URL",
          "key_quote": "string - 关键引用（来自正文或评论）"
        }
      ]
    }
  ],
  "trending_keywords": ["string - 关键词数组"],
  "community_distribution": {
    "r/xxx": "string - 百分比"
  }
}
"""
```

---

### 17.6 💢 痛点挖掘 Prompt（Rant Mode）

```python
RANT_PROMPT = BASE_RULES + """
# 角色
你是一个品牌口碑分析师，负责从 Reddit 吐槽帖中提炼产品/品牌的核心痛点。

# 输入数据
- 品牌/产品: {query}
- 帖子数据（均为包含吐槽信号的帖子）:
```json
{posts_json}
```
- 评论数据:
```json
{comments_json}
```

# 分析任务
1. **情绪分布**：统计正面/中立/负面讨论的大致比例
2. **痛点聚类**：归纳 Top 5 核心痛点类别（如：定价、性能、客服...）
3. **严重程度**：评估每个痛点的严重程度
4. **竞品提及**：识别用户主动提到的替代方案/竞品
5. **迁移意向**：判断用户是"已离开"、"考虑离开"还是"无奈留守"
6. **神评论**：挑选最犀利的 3 条评论

# 严重程度判断标准
- critical：大量提及 + 导致用户离开
- high：频繁提及 + 情绪强烈
- medium：偶尔提及 + 情绪中等
- low：少量提及 + 可容忍

# 输出规则
- 每个痛点必须有 2-3 个证据帖子（含URL和原文引用）
- 竞品必须是用户主动提及的，不要自行推测
- business_implication 需基于痛点推导具体商业机会

# 输出格式（严格遵守此 JSON Schema）
{
  "summary": "string - 一句话概括品牌口碑（50字以内）",
  "confidence": "high | medium | low",
  "evidence_count": "number",
  "sentiment_overview": {
    "positive": "number - 0-1之间",
    "neutral": "number - 0-1之间",
    "negative": "number - 0-1之间"
  },
  "pain_points": [
    {
      "rank": "number - 1-5",
      "category": "string - 如'💰 定价过高'，带emoji",
      "severity": "critical | high | medium | low",
      "mentions": "number - 提及次数",
      "user_voice": "string - 典型用户原话",
      "business_implication": "string - 商业机会含义",
      "evidence": [
        {
          "title": "string",
          "score": "number",
          "url": "string",
          "key_quote": "string - 关键原文引用"
        }
      ]
    }
  ],
  "competitor_mentions": [
    {
      "name": "string - 竞品名",
      "sentiment": "positive | neutral | negative",
      "mentions": "number",
      "typical_context": "string - 用户提及的典型场景",
      "sample_quote": "string - 用户原话"
    }
  ],
  "migration_intent": {
    "already_left": "string - 百分比",
    "considering": "string - 百分比",
    "staying_reluctantly": "string - 百分比"
  },
  "top_quotes": [
    {
      "quote": "string - 神评论原文",
      "score": "number",
      "subreddit": "string",
      "url": "string"
    }
  ]
}
"""
```

---

### 17.7 💡 机会发现 Prompt（Opportunity Mode）

```python
OPPORTUNITY_PROMPT = BASE_RULES + """
# 角色
你是一个商业机会挖掘分析师，负责从 Reddit 求助帖/推荐帖中识别未被满足的市场需求。

# 输入数据
- 需求领域: {query}
- 帖子数据（包含求助/推荐/抱怨等帖子）:
```json
{posts_json}
```
- 评论数据:
```json
{comments_json}
```

# 分析任务
1. **需求识别**：归纳 Top 5 未被满足的核心需求
2. **需求强度**：统计每个需求的"me too"共鸣数量
3. **付费意愿**：识别用户是否表达愿意付费
4. **现有方案**：用户目前在用什么凑合方案，痛点是什么
5. **现有工具评价**：市面上被提及的工具，用户怎么评价
6. **用户画像**：推测主要需求者是谁
7. **市场机会**：总结市场空白和建议

# 共鸣信号识别
"me too" 统计基于这些表达：
- "same here", "me too", "+1", "也在找", "following"
- "exactly this", "this is what I need", "I have the same problem"

# 付费意愿判断
- high：明确说"would pay $X"、"worth paying for"
- medium：暗示愿意付费"if there was a tool..."
- low：只是询问，无付费意向

# 输出规则
- 需求必须来自用户原话，不要自行臆测
- 现有工具评价必须来自用户讨论
- market_opportunity 需具体可落地

# 输出格式（严格遵守此 JSON Schema）
{
  "summary": "string - 一句话概括需求洞察（50字以内）",
  "confidence": "high | medium | low",
  "evidence_count": "number",
  "unmet_needs": [
    {
      "rank": "number - 1-5",
      "need": "string - 如'🎯 自动生成字幕'，带emoji",
      "demand_signal": "strong | medium | weak",
      "me_too_count": "number - 共鸣评论数",
      "willingness_to_pay": "high | medium | low",
      "pay_evidence": "string | null - 用户付费意愿原话",
      "current_workarounds": [
        {
          "solution": "string - 当前凑合方案",
          "pain": "string - 方案的痛点"
        }
      ],
      "opportunity_insight": "string - 商业机会洞察",
      "evidence": [
        {
          "title": "string",
          "score": "number",
          "me_too_comments": "number",
          "url": "string"
        }
      ]
    }
  ],
  "existing_tools": [
    {
      "name": "string",
      "sentiment": "positive | mixed | negative",
      "mentions": "number",
      "praised_for": ["string - 优点数组"],
      "criticized_for": ["string - 缺点数组"]
    }
  ],
  "user_segments": [
    {
      "segment": "string - 用户群体",
      "percentage": "string",
      "core_need": "string",
      "price_sensitivity": "高 | 中 | 低"
    }
  ],
  "market_opportunity": {
    "gap": "string - 市场空白描述",
    "target_user": "string - 目标用户",
    "pricing_hint": "string - 定价建议",
    "gtm_channel": "string - 推广渠道建议"
  }
}
"""
```

---

### 17.8 三个模式的差异对比

| 维度 | 🔥 热点追踪 | 💢 痛点挖掘 | 💡 机会发现 |
|------|-----------|-----------|-----------|
| **核心任务** | 发现趋势话题 | 归类负面反馈 | 识别未满足需求 |
| **分析重点** | 时间趋势、热度 | 情绪、严重性 | 需求强度、付费意愿 |
| **关键输出** | topics + keywords | pain_points + competitors | unmet_needs + market_gap |
| **证据筛选** | 按热度排序 | 按吐槽信号筛选 | 按求助/共鸣信号筛选 |
| **商业价值** | 知道行业动态 | 知道竞品弱点 | 知道市场空白 |

---

### 17.9 证据溯源机制

#### 洞察 + 证据双层结构
```
┌─────────────────────────────────────────────────────────────┐
│  📊 洞察层（LLM 生成）                                       │
│  ─────────────────────────────────────                      │
│  人话总结 → 可展开查看证据原帖                               │
├─────────────────────────────────────────────────────────────┤
│  📎 证据层（原始数据）                                       │
│  ─────────────────────────────────────                      │
│  Reddit 原帖链接 + 评论摘录                                  │
└─────────────────────────────────────────────────────────────┘
```

#### 每个洞察必须可展开
```json
{
  "insight": "用户普遍认为 Adobe 定价过高",
  "confidence": "high",
  "evidence_count": 45,
  "evidence_sources": [
    {
      "post_id": "abc123",
      "title": "Why I'm leaving Adobe",
      "url": "https://reddit.com/r/Adobe/comments/abc123",
      "quote": "每月 $60 对个人用户太贵了",
      "score": 2300,
      "relevance_reason": "直接讨论定价问题"
    }
  ]
}
```

#### UI 交互示例
```
┌─────────────────────────────────────────────────────────────┐
│  💰 痛点 #1: 定价过高                                        │
│  ─────────────────────────────────────                      │
│  用户普遍认为 Adobe 定价过高，尤其是对个人创作者。           │
│                                                              │
│  📎 基于 45 条讨论    [展开证据 ▼]                           │
├─────────────────────────────────────────────────────────────┤
│  [展开后]                                                    │
│                                                              │
│  🔗 "Why I'm finally leaving Adobe after 10 years"          │
│     👍 2.3k | 💬 234 | r/Adobe                               │
│     "每月 $60 对个人用户太贵了..."                           │
│     [查看原帖 →]                                             │
│                                                              │
│  🔗 "Adobe's pricing is officially insane"                   │
│     👍 1.8k | 💬 156 | r/graphic_design                      │
│     "我付的 Creative Cloud 比车险还贵..."                    │
│     [查看原帖 →]                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 17.10 LLM 调用实现

#### 完整代码示例
```python
import json
import os
from openai import OpenAI
from typing import Literal

# 初始化 OpenRouter 客户端
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def generate_report(
    query: str,
    mode: Literal["trending", "rant", "opportunity"],
    posts_data: list,
    comments_data: list,
    time_filter: str = "month"
) -> dict:
    """
    生成 LLM 报告
    
    Args:
        query: 用户查询
        mode: 模式（trending/rant/opportunity）
        posts_data: 帖子数据列表
        comments_data: 评论数据列表
        time_filter: 时间范围
    
    Returns:
        结构化报告字典
    """
    # 1. 数据转 JSON
    posts_json = json.dumps(posts_data, ensure_ascii=False, indent=2)
    comments_json = json.dumps(comments_data, ensure_ascii=False, indent=2)
    
    # 2. 选择对应的 Prompt
    prompt_map = {
        "trending": TRENDING_PROMPT,
        "rant": RANT_PROMPT,
        "opportunity": OPPORTUNITY_PROMPT
    }
    prompt_template = prompt_map[mode]
    
    # 3. 拼接 Prompt
    prompt = prompt_template.format(
        query=query,
        time_filter=time_filter,
        posts_json=posts_json,
        comments_json=comments_json
    )
    
    # 4. 调用 LLM
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-3-mini-beta"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=4096,
            temperature=0.3
        )
        
        # 5. 解析响应
        report = json.loads(response.choices[0].message.content)
        return {"status": "success", "data": report}
        
    except Exception as e:
        # 6. 降级处理
        return {
            "status": "fallback",
            "data": generate_fallback_report(query, mode, posts_data),
            "error": str(e)
        }

def generate_fallback_report(query: str, mode: str, posts_data: list) -> dict:
    """无 LLM 时的降级报告"""
    return {
        "summary": f"找到 {len(posts_data)} 条关于「{query}」的讨论",
        "confidence": "low",
        "evidence_count": len(posts_data),
        "note": "LLM 服务不可用，仅展示原始数据",
        "raw_posts": posts_data[:10]  # 只返回前 10 条
    }
```

#### 配置文件
```python
# .env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
OPENROUTER_MODEL=x-ai/grok-3-mini-beta
OPENROUTER_FALLBACK_MODEL=anthropic/claude-3-haiku
OPENROUTER_MAX_TOKENS=4096
OPENROUTER_TEMPERATURE=0.3
```

---

### 17.11 字段归属与计算方式（LLM 输出契约）

> ⚠️ **核心规则：所有统计值由代码计算，LLM 仅负责归纳/表达。**

#### 字段归属表

| 字段 | 归属 | 计算方式 |
|------|------|---------|
| `evidence_count` | **Code** | `len(evidence_posts)` |
| `community_distribution` | **Code** | `subreddit 频次 / 总数` |
| `sentiment_overview` | **Code** | 基于逐条 `sentiment_label` 聚合 |
| `migration_intent` 百分比 | **Code** | 基于逐条 `intent_label` 聚合 |
| `mentions` (各类) | **Code** | 被归类到该类的证据条数 |
| `heat_score` | **Code** | `score + num_comments * 2` |
| `me_too_count` | **Code** | 评论中匹配共鸣关键词的数量 |
| `demand_signal` | **Code** | 基于 `me_too_count` 阈值（≥30=strong，10-29=medium，<10=weak） |
| `confidence` | **Code** | 基于 evidence_count 判断（≥20=high，10-19=medium，<10=low） |
| `summary` | **LLM** | 自然语言归纳 |
| `key_takeaway` | **LLM** | 每个话题/痛点的核心观点 |
| `topics[].topic` | **LLM** | 话题名称归纳 |
| `pain_points[].category` | **LLM** | 痛点类别归纳 |
| `pain_points[].user_voice` | **LLM** | 典型用户原话选取 |
| `pain_points[].business_implication` | **LLM** | 商业机会推导 |
| `competitor_mentions[].typical_context` | **LLM** | 竞品提及场景归纳 |
| `competitor_mentions[].mentions` | **Code** | 竞品名称命中次数（正则/字典匹配） |
| `market_opportunity.gap` | **LLM** | 市场空白描述 |
| `user_segments[].percentage` | **Code** | 若无可计算依据，填 `"unknown"` |
| `evidence[].key_quote` | **LLM** | 关键引用选取 |

#### 17.11.1 轻量标签生成规则（Code 侧）

> ⚠️ 本模块走“轻量规则”，不引入重模型；若规则无法判定，统一回退为 `neutral/unknown`。
> 词库统一读取：`backend/config/boom_post_keywords.yaml`

**情绪标签（sentiment_label）**  
- rant 模式：命中 `RANT_SIGNALS.strong/medium` → `negative`  
- opportunity/trending 模式：默认 `neutral`（除非命中明确正向词）  
- 如无命中 → `neutral`

**迁移意向（intent_label）**  
```yaml
already_left: ["switching from", "left", "leaving", "never again"]
considering:  ["thinking of", "considering", "might switch", "should I switch"]
staying_reluctantly: default
```

**痛点类别（category_tag）**  
用于 `count_mentions_by_category` 的规则库（示例，可后续扩展）：
```yaml
pricing:      ["price", "pricing", "expensive", "subscription", "fee"]
performance:  ["slow", "lag", "crash", "freeze"]
reliability:  ["broken", "not working", "defective", "error"]
support:      ["support", "customer service", "refund"]
ux:           ["ui", "ux", "workflow", "interface"]
other:        []
```

**共鸣计数（me_too_count）**  
- 从 Redis 评论缓存中统计 `OPPORTUNITY_SIGNALS.resonance` 命中次数  
- 若评论缓存缺失，`me_too_count = 0`

#### 实现模式

```python
async def build_final_response(query_id: str, llm_output: dict, posts_data: list) -> dict:
    """
    后端构建最终响应：
    - 统计值由代码计算
    - LLM 输出仅提供归纳内容
    - 合并后返回前端
    """
    
    # 1. 代码计算统计值
    evidence_count = len(posts_data)
    
    community_counts = Counter(p["subreddit"] for p in posts_data)
    community_distribution = {
        sub: f"{count/evidence_count*100:.0f}%"
        for sub, count in community_counts.most_common(5)
    }
    
    sentiment_counts = Counter(p.get("sentiment_label", "neutral") for p in posts_data)
    sentiment_overview = {
        "positive": sentiment_counts.get("positive", 0) / evidence_count,
        "neutral": sentiment_counts.get("neutral", 0) / evidence_count,
        "negative": sentiment_counts.get("negative", 0) / evidence_count
    }
    
    confidence = (
        "high" if evidence_count >= 20 
        else "medium" if evidence_count >= 10 
        else "low"
    )
    
    # 2. 合并 LLM 输出（覆盖 LLM 可能错算的统计值）
    final_response = {
        **llm_output,  # LLM 的归纳内容
        # 以下字段强制由代码覆盖
        "evidence_count": evidence_count,
        "community_distribution": community_distribution,
        "sentiment_overview": sentiment_overview,
        "confidence": confidence,
        "query_id": query_id
    }
    
    # 3. 校验 LLM 输出的 mentions 等（可选：记录差异日志）
    for pain_point in final_response.get("pain_points", []):
        actual_mentions = count_mentions_by_category(posts_data, pain_point["category"])
        if pain_point.get("mentions") != actual_mentions:
            logger.warning(f"LLM mentions mismatch: {pain_point['mentions']} vs {actual_mentions}")
            pain_point["mentions"] = actual_mentions  # 强制覆盖
    
    return final_response
```

#### Prompt 调整建议

由于统计值由代码计算，Prompt 中可以简化 LLM 的任务：

```python
# 可选：从 LLM Schema 中移除统计字段
# 让 LLM 只输出结构化洞察 + 证据引用
SIMPLIFIED_RANT_PROMPT = """
# LLM 只负责：
1. 归纳痛点类别（category）
2. 选取典型用户原话（user_voice）
3. 推导商业含义（business_implication）
4. 选取关键引用（key_quote）

# LLM 不负责（由代码计算）：
- mentions 数量
- 情绪分布百分比
- evidence_count
- confidence 等级
"""
```

---

## 十八、迭代计划

### Phase 1：MVP（2周）
- [x] 痛点挖掘模式（基于现有脚本）
- [ ] 基础UI（搜索框 + 结果列表）
- [ ] Redis 缓存集成
- [ ] 基础限流

### Phase 2：完善（2周）
- [ ] 热点追踪模式
- [ ] 机会发现模式
- [ ] 模式自动识别
- [ ] LLM 摘要生成

### Phase 3：优化（持续）
- [ ] 多 API Key 轮换
- [ ] 缓存预热
- [ ] 个性化推荐
- [ ] 收藏 & 历史记录

---

**文档维护者**: 产品团队  
**最后更新**: 2026-01-28

---

## 📝 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| **v2.2** | 2026-01-28 | 🔧 **重大修正**：① 新增《口径与真相源》全局规则 ② API限额统一为100 QPM + 10分钟窗口 ③ 评论正文不落库（合规要求） ④ 复用evidence_posts（不建独立证据体系） ⑤ 临时表改Redis会话 ⑥ WebSocket改SSE ⑦ 新增字段归属表（统计值由代码算） |
| v2.1 | 2026-01-28 | 新增 LLM 报告生成架构章节：Prompt 设计、三模式独立模板、数据流程、OpenRouter 配置、证据溯源机制 |
| v2.0 | 2026-01-28 | 新增 A-H 补充章节：范围口径、可信度、异常降级、系统衔接、数据资产、合规限流、安全权限、指标验收 |
| v1.0 | 2026-01-28 | 初始版本：产品概述、三大模式、技术架构、缓存限流策略 |
