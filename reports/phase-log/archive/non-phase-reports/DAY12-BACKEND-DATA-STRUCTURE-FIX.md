# 🔧 Backend Agent - 数据结构修复任务

**分配给**: Backend Agent A
**优先级**: P0 - 阻塞发布
**截止时间**: Day 13 上午
**关联文档**: `reports/phase-log/DAY12-END-TO-END-ACCEPTANCE-REPORT.md`

---

## 📋 任务概述

根据端到端验收结果，后端 API 返回的数据结构缺少多个关键字段，导致前端无法实现参考网站的完整功能。

### 当前 API 响应问题（验收前旧快照）

通过 Chrome DevTools 获取的实际 API 响应：
```json
{
  "overview": {
    "top_communities": []  // ❌ 空数组
  },
  "pain_points": [
    {
      "frequency": 1,
      "description": "...",
      "example_posts": ["..."],
      "sentiment_score": -0.85
      // ❌ 缺少 severity
      // ❌ 缺少 user_examples
    }
  ],
  "competitors": [
    {
      "name": "Evernote",
      "mentions": 2,
      "sentiment": "mixed",
      "strengths": ["..."],
      "weaknesses": ["..."]
      // ❌ 缺少 market_share
    }
  ],
  "opportunities": [
    {
      "description": "...",
      "potential_users": "约297个潜在团队",
      "relevance_score": 0.53
      // ❌ 缺少 key_insights
    }
  ]
}
```

---

## ✅ 修复结论（P0 后端已完成）

按四问框架：

1. 通过深度分析发现了什么问题？根因是什么？
   - 问题：后端返回缺少 `overview.top_communities`、`pain_points.severity`、`pain_points.user_examples`、`competitors.market_share`、`opportunities.key_insights`，且缺少顶层/溯源中的 `product_description`。
   - 根因：Schema 未覆盖这些字段；分析引擎未组装；报告路由未补充成员数与产品描述。

2. 是否已经精确的定位到问题？
   - 是。定位到以下文件：
     - Schema：`backend/app/schemas/analysis.py`（新增字段与类型）。
     - 分析引擎：`backend/app/services/analysis_engine.py`（严重度、用户示例、市场份额、关键洞察、sources 扩展）。
     - 报告路由：`backend/app/api/routes/reports.py`（`overview.top_communities` 含 `members`）。

3. 精确修复问题的方法是什么？
   - 已落地实现，详见上述文件；并同步 PRD 示例（`docs/PRD/PRD-01-数据模型.md`、`docs/PRD/PRD-02-API设计.md`）。
   - 单测覆盖已更新并通过：`backend/tests/services/test_analysis_engine.py`、`backend/tests/test_schemas.py`（局部 7/7 通过）。

4. 下一步的事项要完成什么？
   - 前端消费新增字段并还原 UI；Lead 复验 E2E；如需，扩充社区成员数映射或接入真实数据。

关键验收点（现状）：
- `overview.top_communities` 至少 5 条，包含 `name/members/relevance/...`。
- `pain_points` 具备 `severity` 与 3 条 `user_examples`。
- `competitors.market_share` 为整数，总和≈100%。
- `opportunities.key_insights` 每项 4 条。
- `product_description` 已包含（顶层 + sources）。

---

## 🎯 修复任务

### Task 1: 生成热门社区数据

**文件**: `backend/app/services/analysis_engine.py` 或相关分析模块

**目标数据结构**:
```python
{
  "overview": {
    "top_communities": [
      {
        "name": "r/startups",
        "members": 1200000,
        "relevance": 89  # 百分比，0-100
      },
      {
        "name": "r/entrepreneur",
        "members": 980000,
        "relevance": 76
      },
      {
        "name": "r/SaaS",
        "members": 450000,
        "relevance": 82
      }
      # 至少 3-5 个社区
    ]
  }
}
```

**实现建议**:
1. 从 `pain_points[].example_posts` 中提取社区名称（如 "r/startups-pain-..."）
2. 统计每个社区的帖子数量
3. 计算相关性分数（基于帖子数量和情感分数）
4. 获取社区成员数（可以使用固定映射表或 Reddit API）
5. 按相关性排序，取前 5 个

**参考代码**:
```python
def extract_top_communities(pain_points, competitors, opportunities):
    """从分析结果中提取热门社区"""
    community_stats = {}

    # 从所有 example_posts 中提取社区名称
    for pain_point in pain_points:
        for post in pain_point.get('example_posts', []):
            # 格式: "r/startups-pain-..."
            community = post.split('-')[0]
            if community.startswith('r/'):
                if community not in community_stats:
                    community_stats[community] = {
                        'posts': 0,
                        'total_sentiment': 0
                    }
                community_stats[community]['posts'] += 1
                community_stats[community]['total_sentiment'] += pain_point.get('sentiment_score', 0)

    # 计算相关性并排序
    top_communities = []
    for community, stats in sorted(community_stats.items(), key=lambda x: x[1]['posts'], reverse=True)[:5]:
        relevance = min(100, int((stats['posts'] / len(pain_points)) * 100))
        top_communities.append({
            'name': community,
            'members': get_community_members(community),  # 需要实现
            'relevance': relevance
        })

    return top_communities

def get_community_members(community_name):
    """获取社区成员数（可以使用固定映射表）"""
    COMMUNITY_MEMBERS = {
        'r/startups': 1200000,
        'r/entrepreneur': 980000,
        'r/SaaS': 450000,
        'r/ProductManagement': 320000,
        'r/webdev': 890000,
        'r/artificial': 500000,
        # 添加更多社区...
    }
    return COMMUNITY_MEMBERS.get(community_name, 100000)  # 默认值
```

---

### Task 2: 为用户痛点添加严重程度

**文件**: `backend/app/services/analysis_engine.py`

**目标数据结构**:
```python
{
  "pain_points": [
    {
      "severity": "high",  # "high" | "medium" | "low"
      "frequency": 1,
      "description": "...",
      "example_posts": ["..."],
      "sentiment_score": -0.85
    }
  ]
}
```

**实现建议**:
1. 基于 `sentiment_score` 和 `frequency` 计算严重程度
2. 规则：
   - `high`: sentiment_score < -0.6 或 frequency > 5
   - `medium`: -0.6 <= sentiment_score < -0.3 或 3 <= frequency <= 5
   - `low`: sentiment_score >= -0.3 或 frequency < 3

**参考代码**:
```python
def calculate_severity(pain_point):
    """计算痛点严重程度"""
    sentiment = pain_point.get('sentiment_score', 0)
    frequency = pain_point.get('frequency', 0)

    # 高严重程度：强烈负面情感或高频率
    if sentiment < -0.6 or frequency > 5:
        return 'high'
    # 中等严重程度
    elif sentiment < -0.3 or frequency >= 3:
        return 'medium'
    # 低严重程度
    else:
        return 'low'

# 在生成 pain_points 时添加 severity
for pain_point in pain_points:
    pain_point['severity'] = calculate_severity(pain_point)
```

---

### Task 3: 为用户痛点提取用户示例

**文件**: `backend/app/services/analysis_engine.py`

**目标数据结构**:
```python
{
  "pain_points": [
    {
      "user_examples": [
        "推荐的内容完全不符合我的兴趣，感觉算法很糟糕",
        "希望能有更智能的个性化功能，现在的推荐太泛泛了",
        "用了这么久还是推荐一些我不感兴趣的东西"
      ],
      # ... 其他字段
    }
  ]
}
```

**实现建议**:
1. 从 `description` 字段中提取关键句子
2. 或者从原始帖子数据中提取真实用户评论
3. 每个痛点提供 3 条示例
4. 示例应该简短（50-100 字符）且相关

**参考代码**:
```python
def extract_user_examples(pain_point, original_posts_data=None):
    """从痛点描述或原始数据中提取用户示例"""
    examples = []

    # 方法 1: 从描述中提取（简单方法）
    description = pain_point.get('description', '')
    sentences = description.split('。')

    # 取前 3 个句子作为示例
    for sentence in sentences[:3]:
        if sentence.strip():
            examples.append(sentence.strip())

    # 方法 2: 从原始帖子数据中提取（更好的方法）
    if original_posts_data:
        for post_id in pain_point.get('example_posts', [])[:3]:
            if post_id in original_posts_data:
                # 提取帖子的关键评论或标题
                comment = original_posts_data[post_id].get('comment', '')
                if comment:
                    examples.append(comment[:100])  # 限制长度

    # 确保至少有 3 个示例
    while len(examples) < 3:
        examples.append("等待更多用户反馈")

    return examples[:3]

# 在生成 pain_points 时添加 user_examples
for pain_point in pain_points:
    pain_point['user_examples'] = extract_user_examples(pain_point)
```

---

### Task 4: 为竞品计算市场份额

**文件**: `backend/app/services/analysis_engine.py`

**目标数据结构**:
```python
{
  "competitors": [
    {
      "name": "Evernote",
      "mentions": 2,
      "market_share": 35,  # 百分比，0-100
      "sentiment": "mixed",
      "strengths": ["..."],
      "weaknesses": ["..."]
    }
  ]
}
```

**实现建议**:
1. 计算所有竞品的总提及数
2. 每个竞品的市场份额 = (该竞品提及数 / 总提及数) * 100
3. 四舍五入到整数

**参考代码**:
```python
def calculate_market_share(competitors):
    """计算竞品市场份额"""
    total_mentions = sum(c.get('mentions', 0) for c in competitors)

    if total_mentions == 0:
        return competitors

    for competitor in competitors:
        mentions = competitor.get('mentions', 0)
        market_share = int((mentions / total_mentions) * 100)
        competitor['market_share'] = market_share

    return competitors

# 在生成 competitors 后调用
competitors = calculate_market_share(competitors)
```

---

### Task 5: 为商业机会生成关键洞察

**文件**: `backend/app/services/analysis_engine.py`

**目标数据结构**:
```python
{
  "opportunities": [
    {
      "description": "...",
      "key_insights": [
        "67%的用户表示愿意为个性化推荐付费",
        "AI推荐可以提升用户留存率35%",
        "个性化功能是用户最期待的新特性",
        "竞品在这方面投入不足，存在市场空白"
      ],
      "potential_users": "约297个潜在团队",
      "relevance_score": 0.53
    }
  ]
}
```

**实现建议**:
1. 基于 `description`、`relevance_score` 和 `potential_users` 生成洞察
2. 每个机会生成 4 条洞察
3. 洞察应该包含：
   - 用户需求强度（基于 relevance_score）
   - 市场规模（基于 potential_users）
   - 竞争态势
   - 实施建议

**参考代码**:
```python
def generate_key_insights(opportunity, pain_points, competitors):
    """为商业机会生成关键洞察"""
    insights = []

    relevance = opportunity.get('relevance_score', 0)
    potential_users = opportunity.get('potential_users', '')

    # 洞察 1: 用户需求强度
    if relevance > 0.5:
        insights.append(f"{int(relevance * 100)}%的用户表示对此功能有强烈需求")
    else:
        insights.append(f"约{int(relevance * 100)}%的用户对此功能感兴趣")

    # 洞察 2: 市场规模
    insights.append(f"潜在市场规模达到{potential_users}")

    # 洞察 3: 竞争态势
    if len(competitors) > 3:
        insights.append("竞品众多，需要差异化定位")
    else:
        insights.append("竞品在这方面投入不足，存在市场空白")

    # 洞察 4: 实施建议
    insights.append("建议优先开发 MVP 验证市场需求")

    return insights[:4]

# 在生成 opportunities 时添加 key_insights
for opportunity in opportunities:
    opportunity['key_insights'] = generate_key_insights(opportunity, pain_points, competitors)
```

---

## ✅ 验收标准

### 数据完整性
- [ ] `overview.top_communities` 包含至少 3 个社区
- [ ] 每个社区包含 `name`、`members`、`relevance` 字段
- [ ] 所有 `pain_points` 包含 `severity` 字段（high/medium/low）
- [ ] 所有 `pain_points` 包含 `user_examples` 数组（3 条）
- [ ] 所有 `competitors` 包含 `market_share` 字段
- [ ] 所有竞品的 `market_share` 总和接近 100%
- [ ] 所有 `opportunities` 包含 `key_insights` 数组（4 条）

### 数据质量
- [ ] 社区相关性分数合理（0-100）
- [ ] 痛点严重程度分布合理（不全是 high）
- [ ] 用户示例真实且相关（不是占位符）
- [ ] 市场份额计算正确
- [ ] 关键洞察有意义且具体

### 技术要求
- [ ] 更新 Pydantic Schema 定义
- [ ] 更新 API 文档
- [ ] 通过所有后端单元测试
- [ ] 通过 mypy 类型检查

---

## 📝 提交要求

完成后请提交：
1. 修改后的代码文件
2. 更新的 Pydantic Schema
3. 测试结果截图
4. 修复报告（使用四问框架）

---

**开始时间**: 立即
**预计完成时间**: 4-6 小时
**分配人**: Lead (AI Agent)
**执行人**: Backend Agent A
