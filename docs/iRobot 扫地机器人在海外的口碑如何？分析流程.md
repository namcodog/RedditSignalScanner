# iRobot 扫地机器人在海外的口碑如何？分析流程

**文档版本**: v1.0  
**创建日期**: 2026-01-23  
**适用场景**: 品牌/产品口碑快速验证、竞品分析、市场探索

---

## 一、分析目标

通过 Reddit 社区数据，快速获取 iRobot（Roomba）在海外市场的真实用户口碑反馈，包括：
- 核心吐槽点/痛点
- 用户真实评价（带证据链接）
- 与竞品的对比讨论
- 相关讨论社区发现

---

## 二、分析流程（SOP）

### 2.1 流程总览

```
用户问题
    ↓
关键词组合构建
    ↓
双路径搜索（全站 + 定向社区）
    ↓
吐槽信号检测与过滤
    ↓
抓取神评论
    ↓
社区统计分析
    ↓
结构化输出（JSON + Markdown）
```

---

### 2.2 详细步骤

#### Step 1: 关键词组合构建

**输入**：
- 品牌名称：`Roomba` / `iRobot`
- 吐槽词库（预定义）：
  ```python
  ["broken", "problem", "issue", "terrible", "worst", 
   "hate", "regret", "refund", "disappointed", "avoid", 
   "not working", "stopped", "error", "defective", "waste"]
  ```

**输出**：
```python
搜索查询组合 = [
    "Roomba broken",
    "Roomba problem",
    "Roomba terrible",
    "Roomba not working",
    "Roomba refund",
    ...
    "Roomba"  # 兜底查询
]
```

---

#### Step 2: 双路径搜索

##### 路径 A：全站广域搜索（发现新社区）

```python
# 使用 Reddit Search API
for query in 搜索查询组合:
    posts = reddit_client.search_posts(
        query=query,
        limit=100,
        time_filter="all",  # 全时段
        sort="top"          # 按热度排序
    )
```

**特点**：
- ✅ 覆盖全站，能发现新兴社区
- ❌ 噪音较多，需要后续过滤

##### 路径 B：定向社区搜索（精准挖掘）

```python
# 在已知相关社区内搜索
目标社区 = ["roomba", "RobotVacuums", "Roborock"]

for subreddit in 目标社区:
    posts = reddit_client.search_subreddit_page(
        subreddit=subreddit,
        query="Roomba",
        sort="top",
        time_filter="all"
    )
```

**特点**：
- ✅ 精准度高，噪音少
- ❌ 需要提前知道相关社区

**建议策略**：
1. 首次分析：路径 A（发现社区）
2. 后续分析：路径 B（深挖已知社区）

---

#### Step 3: 吐槽信号检测与过滤

**检测逻辑**：
```python
def detect_rant_signals(post):
    """检测帖子中的吐槽信号词"""
    text = f"{post.title} {post.body}".lower()
    signals = []
    
    for trigger in RANT_TRIGGERS:
        if trigger in text:
            signals.append(trigger)
    
    return signals

def calculate_rant_score(post, signals):
    """计算吐槽强度分数"""
    heat_score = post.score + post.num_comments * 2
    rant_score = len(signals) * 10 + heat_score * 0.01
    return rant_score
```

**过滤条件**：
- `len(signals) >= 1`：至少有一个吐槽信号词
- `post.num_comments >= 5`：有足够的讨论
- 按 `rant_score` 降序排序，取 Top 30

**吐槽强度分数公式**：
```
rant_score = 吐槽信号数 × 10 + (点赞数 + 评论数 × 2) × 0.01
```

---

#### Step 4: 抓取神评论

对筛选出的每个高吐槽帖子：

```python
for post in top_rants[:20]:  # 只抓前20条的评论
    comments = reddit_client.fetch_post_comments(
        post_id=post.id,
        sort="top",
        limit=3,
        mode="topn"
    )
    
    post.top_comments = [
        {
            "author": c.get("author"),
            "body": c.get("body")[:400],  # 截断保留前400字符
            "score": c.get("score")
        }
        for c in comments[:3]
    ]
```

**为什么需要评论**：
- 帖子标题可能夸张，评论提供真实细节
- 评论区共鸣程度验证痛点真实性
- 神评论往往包含具体产品缺陷描述

---

#### Step 5: 社区统计分析

```python
community_stats = defaultdict(int)

for post in all_posts:
    community_stats[post.subreddit] += 1

# 按频次降序排序
sorted_communities = sorted(
    community_stats.items(), 
    key=lambda x: x[1], 
    reverse=True
)
```

**产出示例**：
```
r/roomba: 146 条
r/RobotVacuums: 39 条
r/Roborock: 21 条
r/homeassistant: 7 条
```

**价值**：
- 发现讨论该品牌最活跃的社区
- 可纳入 community_pool 进行长期监控

---

#### Step 6: 结构化输出

##### 6.1 JSON 证据包（系统处理用）

```json
{
  "meta": {
    "brand": "Roomba",
    "subreddits_searched": ["roomba", "RobotVacuums", "Roborock"],
    "total_posts_scanned": 715,
    "rant_posts_found": 30,
    "hunt_time": "2025-12-17T17:32:57.837758"
  },
  "top_rants": [
    {
      "rank": 1,
      "id": "xqa4mt",
      "title": "Roborock - Great Technology - Terrible Customer Support",
      "body_preview": "As per the title really - their products offer cutting edge tech but zero aftersales support...",
      "score": 11,
      "num_comments": 6,
      "heat_score": 23.0,
      "rant_score": 70.23,
      "rant_signals": [
        "broken",
        "problem",
        "issue",
        "terrible",
        "refund",
        "disappointed",
        "error"
      ],
      "subreddit": "Roborock",
      "author": "NST2020",
      "reddit_url": "https://reddit.com/r/Roborock/comments/xqa4mt/...",
      "created_utc": 1664364474.0,
      "top_comments": [
        {
          "author": "HairpinGosu",
          "body": "It's very true that the China based \"xiaomi\" sister companies have a horrible after service policy...",
          "score": 3
        },
        {
          "author": "arty118",
          "body": "I have network disconnection problem and support won't do anything until I go to buy another phone...",
          "score": 2
        }
      ]
    }
  ],
  "community_stats": {
    "roomba": 146,
    "RobotVacuums": 39,
    "Roborock": 21
  }
}
```

##### 6.2 Markdown 报告（人类阅读用）

```markdown
# 🎯 Roomba 定向吐槽挖掘报告

**生成时间**: 2025-12-17T17:32:57.837758
**搜索社区**: r/roomba, r/RobotVacuums, r/Roborock
**扫描帖子**: 715 条
**吐槽帖子**: 30 条

---

## 🔥 Top 吐槽帖排行

### #1 [Roborock - Great Technology - Terrible Customer Support](https://reddit.com/r/Roborock/comments/xqa4mt/...)

- **社区**: r/Roborock
- **点赞**: 11 | **评论**: 6 | **吐槽分**: 70.2
- **吐槽信号**: broken, problem, issue, terrible, refund, disappointed, error

> As per the title really - their products offer cutting edge tech but zero aftersales support in my experience...

**🗣️ 精选评论:**

1. [👍 3] **u/HairpinGosu**: It's very true that the China based "xiaomi" sister companies have a horrible after service policy...

2. [👍 2] **u/arty118**: I have network disconnection problem and support won't do anything until I go to buy another phone...

---
```

---

## 三、实际分析结果（iRobot 案例）

### 3.1 核心发现

基于 2025年12月 的分析数据：

| 维度 | 发现 |
|------|------|
| **扫描帖子数** | 715 条 |
| **吐槽帖数** | 30 条 |
| **涉及社区** | 3 个核心社区（roomba, RobotVacuums, Roborock） |
| **核心痛点** | 技术落后、可靠性差、客服质量低 |

### 3.2 代表性证据

#### 证据 1: 技术代际差距
> **标题**: "Switched from '22 Roomba J7+ to Roborock Q8 Max+"  
> **吐槽分**: 70.15  
> **神评论**: "Roborock are a decade ahead of Roomba tech. Very likely the Chinese firms stole Roomba tech years ago, and then invested own R&D to race ahead."

#### 证据 2: 可靠性问题
> **标题**: "Roborock - Great Technology - Terrible Customer Support"  
> **吐槽分**: 70.23  
> **神评论**: "Having 3 grand in Roomba paperweights I would NEVER recommend anyone to buy one. SO. MANY. ISSUES."

#### 证据 3: 用户流失
> **观察**: 大量帖子主题为"从 Roomba 切换到 Roborock/Dreame"的经历分享，表明用户正在流失到中国品牌

### 3.3 社区分布

```
r/roomba          146 条  ████████████████████████████████████
r/RobotVacuums     39 条  ██████████
r/Roborock         21 条  █████
```

**洞察**：
- `r/roomba` 是官方社区，但讨论中已有大量竞品对比
- `r/RobotVacuums` 是泛品类社区，Roomba 已非主流讨论对象
- `r/Roborock` 竞品社区中有大量"从 Roomba 切换"的帖子

---

## 四、与现有系统的集成方案

### 4.1 双模式并行架构

```
┌─────────────────────────────────────────┐
│     🎯 快速模式（问题驱动）              │
│                                          │
│  触发: 用户提问                          │
│  耗时: 1-2 分钟                          │
│  输出: 证据帖 Top 10-30                  │
│                                          │
│  副产物:                                 │
│  ├─ 发现的社区 → discovered_communities  │
│  └─ 发现的吐槽词 → semantic_rules        │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│          📦 数据中台                     │
│                                          │
│  • 帖子入库 (posts_raw, comments)        │
│  • 社区池扩充 (community_pool)           │
│  • 语义库丰富 (semantic_rules)           │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│     🏭 深度模式（社区驱动）              │
│                                          │
│  触发: 后台定时 / 手动触发               │
│  耗时: 10-30 分钟                        │
│  输出: facts.json + 完整报告             │
│                                          │
│  处理流程:                               │
│  └─ 语义标注 → 痛点聚类 → LLM推理       │
└─────────────────────────────────────────┘
```

### 4.2 工作流

#### 场景 1：快速验证
```
1. 用户提问："iRobot 在海外口碑如何？"
2. 系统立即执行"问题驱动搜索"
3. 1-2 分钟返回证据帖 Top 10
4. 用户获得快速答案，可决策是否深挖
```

#### 场景 2：深度分析
```
1. 用户查看证据帖后，点击"深度分析"
2. 后台:
   - 将帖子入库
   - 运行 SmartTagger 语义标注
   - 执行 t1_stats 聚合分析
   - 调用 Grok 生成完整报告
3. 10分钟后推送 facts.json + 深度报告
```

#### 场景 3：社区扩充
```
1. "问题驱动搜索"发现新社区（如 r/Roborock）
2. 自动记录到 discovered_communities 表
3. 后台评估该社区的价值密度
4. 符合标准 → 自动加入 community_pool
5. 下次定时抓取包含该社区
```

---

## 五、脚本工具

### 5.1 工具列表

| 脚本 | 功能 | 位置 |
|------|------|------|
| `hunt_rant_posts.py` | 全站关键词搜索 | `backend/scripts/` |
| `hunt_rant_focused.py` | 指定社区定向搜索 | `backend/scripts/` |

### 5.2 使用示例

#### 全站搜索模式
```bash
cd backend
PYTHONPATH=. python scripts/hunt_rant_posts.py \
  --brand "Roomba" \
  --rant-words "broken,terrible,problem,refund" \
  --time-filter all \
  --max-posts 30 \
  --min-score 20 \
  --min-comments 5
```

#### 定向社区模式
```bash
cd backend
PYTHONPATH=. python scripts/hunt_rant_focused.py \
  --brand "Roomba" \
  --subreddits "roomba,RobotVacuums,Roborock" \
  --max-posts 300 \
  --top-n 30 \
  --min-comments 5
```

### 5.3 输出文件

```
backend/reports/rant-hunter/
├── roomba_rant_evidence.json      # JSON 结构化数据
└── roomba_rant_report.md          # Markdown 可读报告
```

---

## 六、优势与限制

### 6.1 优势

| 优势 | 说明 |
|------|------|
| **快速响应** | 1-2 分钟即可返回证据，满足快速验证需求 |
| **自动扩展** | 每次搜索都是探针，自动发现新社区 |
| **精准命中** | 直接定位用户关心的话题，不依赖预设社区池 |
| **真实证据** | 提供原帖链接和神评论，可溯源验证 |

### 6.2 限制

| 限制 | 说明 | 解决方案 |
|------|------|----------|
| **无趋势分析** | 只看当前快照，无法看历史变化 | 集成到社区驱动模式，定期抓取 |
| **语义理解浅** | 仅关键词匹配，不懂帖子真正含义 | 后续接入 SmartTagger 深度标注 |
| **不入库** | 数据不持久化，无法二次分析 | 提供"一键入库"功能 |

---

## 七、后续优化方向

### 7.1 短期优化
1. **吐槽词库动态化**：从 `semantic_rules` 表读取，而非硬编码
2. **结果去重**：同一帖子被多个查询命中时去重
3. **社区自动入池**：搜索结果自动写入 `discovered_communities`

### 7.2 中期优化
1. **接入 SmartTagger**：对搜索结果做语义标注
2. **竞品识别**：自动提取帖子中提到的竞品品牌
3. **痛点聚类**：对吐槽内容做主题聚类

### 7.3 长期优化
1. **与社区驱动模式融合**：形成"快速验证 → 深度分析"闭环
2. **实时监控**：对关键品牌/话题设置监控，新爆帖实时推送
3. **智能推荐**：根据用户问题，自动推荐相关社区和吐槽词

---

## 八、附录

### A. 吐槽词库（默认）

```python
DEFAULT_RANT_TRIGGERS = [
    "broken", "problem", "issue", "terrible", "worst",
    "hate", "regret", "refund", "disappointed", "avoid",
    "not working", "stopped", "error", "defective", "waste",
    "garbage", "useless", "returned", "nightmare", "leaving"
]
```

### B. 数据结构定义

#### RantPost 对象
```python
@dataclass
class RantPost:
    id: str                    # 帖子ID
    title: str                 # 标题
    body: str                  # 正文（截断至1000字符）
    score: int                 # 点赞数
    num_comments: int          # 评论数
    subreddit: str             # 所属社区
    author: str                # 作者
    permalink: str             # 永久链接
    created_utc: float         # 创建时间（Unix时间戳）
    top_comments: List[Dict]   # Top 评论列表
    rant_signals: List[str]    # 检测到的吐槽信号词
    
    @property
    def reddit_url(self) -> str:
        return f"https://reddit.com{self.permalink}"
    
    @property
    def heat_score(self) -> float:
        return self.score + self.num_comments * 2
    
    @property
    def rant_score(self) -> float:
        return len(self.rant_signals) * 10 + self.heat_score * 0.01
```

---

**文档维护者**: 数据架构师  
**审核状态**: ✅ 已验证  
**最后更新**: 2026-01-23
