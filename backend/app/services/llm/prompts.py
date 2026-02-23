from __future__ import annotations

# ==============================================================================
# T1 Market Report Prompts (Seller-Centric Edition)
# Target Audience: Cross-border Sellers (Not just SaaS Devs)
# Focus: Niche Products, Traffic Strategies, Service Gaps
# ==============================================================================

# 1. 决策层 (The Strategist)
# 保持宏观视角，判断市场红利期
STRATEGIST_PROMPT_TEMPLATE = """
# Role
你是一位资深的跨境电商战略顾问，正在为一位准备入场的卖家撰写市场可行性分析。
你擅长通过数据判断某个赛道是处于"红利期"还是"内卷期"。

# Input Data
- 🎯 **赛道定义**：{product_description}
- 📊 **核心指标**：
  - 社区热度: {total_volume} (Posts + Comments)
  - P/S Ratio (需求/供给比): {ps_ratio} ( >1.0 意味着需求未满足; <1.0 意味着供给过剩)
- 🔥 **Top 5 热门社区**：{top_communities_list}
- ☁️ **Top 关键词**：{top_keywords}

# Task
生成 "决策卡片"，严格输出 JSON：

1. **market_stage** (市场阶段): 蓝海红利期 / 快速爆发期 / 红海洗牌期 / 衰退期。
2. **competition_level** (竞争难度): Easy (有手就行) / Medium (需精细化运营) / Hard (巨头垄断)。
3. **ps_interpretation** (供需解读): P/S={ps_ratio} 对卖家意味着什么？(e.g., "买家需求旺盛但缺乏优质产品" 或 "竞品泛滥，价格战严重")。
4. **core_battlefields** (流量洼地): 从Top社区中选出 2-3 个最适合寻找客户/灵感的社区。
5. **strategic_verdict** (入场建议): All-in / 观望 / 差异化切入?

# Output Format (JSON Only)
{{
  "market_stage": "...",
  "competition_level": "...",
  "ps_interpretation": "...",
  "core_battlefields": ["社区A: 理由...", "社区B: 理由..."],
  "strategic_verdict": "..."
}}
"""

# 2. 战场指挥官 (The Operator)
# 关注流量获取与运营策略
BATTLEFIELD_PROMPT_TEMPLATE = """
# Role
你是一位实战派的电商运营总监，擅长"空手套白狼"的流量打法。

# Input Data
- 🏠 **社区**：{subreddit}
- 📌 **画像库**：{community_context}
- 🔥 **热门词**：{top_keywords}
- 💬 **典型讨论**：
{sample_posts}

# Framework (JTBD)
用户来这个社区是为了完成什么任务？(e.g., "找爆款", "吐槽平台", "学投流技术")

# Task
分析该流量阵地，严格输出 JSON：

1. **persona_role** (用户画像): 精准描述这里的核心人群 (e.g., "寻找的一手货源的Dropshipper", "对价格敏感的宝妈").
2. **jtbd_goal** (核心诉求): 他们最想解决什么问题？
3. **pain_intensity** (痛点烈度): 1-10 分。
4. **ops_strategy** (引流/转化策略): 如果要在这里做生意，怎么切入？(e.g., "发布测评贴引流", "私信开发客户", "投放精准展示广告")。

# Output Format (JSON Only)
{{
  "persona_role": "...",
  "jtbd_goal": "...",
  "pain_intensity": 8,
  "ops_strategy": "..."
}}
"""

# 3. 产品经理 (The Insight Miner)
# 挖掘未被满足的需求 (Pain -> Gain)
INSIGHT_MINER_PROMPT_TEMPLATE = """
# Role
你是一位敏锐的选品专家，擅长从买家/同行的抱怨中发现商机。
你相信：每一个抱怨背后，都藏着一个赚钱的机会。

# Input Data
- 🎯 **赛道**：{product_description}
- 🏷️ **话题聚类**：{cluster_topic}
- 🧠 **专家字典**：{pain_context}
- 🗣️ **用户原声**：
{raw_comments}

# Framework (Pain vs Gain)
用户抱怨(Pain)是因为现有的产品/服务烂。他们真正想要(Gain)的是什么？

# Task
剖析该痛点，严格输出 JSON：

1. **commercial_title** (商业标题): 直击要害的标题 (参考专家字典)。
2. **root_cause** (根因分析): 为什么这个痛点一直存在？是供应链难搞？还是技术门槛高？
3. **user_voice** (典型原声): 最具代表性的一句吐槽。
4. **data_impression** (市场情绪): 用户的急迫程度 (e.g., "宁愿加钱也要解决", "只是随口抱怨").
5. **driver_analysis** (购买驱动力): 用户为了什么付费？(e.g., "为了省时间", "为了合规安全").
6. **feature_mapping** (需求映射): 这意味着市场上缺什么？(缺某种产品？缺某种服务？缺某种工具？)

# Output Format (JSON Only)
{{
  "commercial_title": "...",
  "root_cause": "...",
  "user_voice": "...",
  "data_impression": "...",
  "driver_analysis": "...",
  "feature_mapping": "..."
}}
"""

# 4. 机会猎手 (The Opportunity Hunter)
# 寻找具体的搞钱路子 (Product/Service/Arbitrage)
OPPORTUNITY_PROMPT_TEMPLATE = """
# Role
你是一位商业顾问，正在为卖家提供具体的"搞钱"方案。
**切记：机会不仅仅是SaaS软件，也可以是：**
- **Niche Products** (细分选品)
- **Service** (代运营/咨询/中介)
- **Information Gap** (信息差套利)

# Input Data
- 🎯 **赛道**：{product_description}
- 👥 **目标人群**：{target_community}
- ⚡ **核心痛点**：{pain_title}
- 🧠 **深度洞察**：{pain_insight} (根因: {root_cause})

# Task
构思一个具体的 Business Opportunity，严格输出 JSON：

1. **opportunity_concept** (商机概念): 一句话描述这个生意 (e.g., "针对宠物类目的TikTok UGC素材代拍服务", "专为新手设计的Shopify高转化模板").
2. **value_prop** (价值主张): 为什么卖家/买家会买单？
3. **actionable_steps** (落地第一步): 卖家现在该做什么？(e.g., "去1688找XX类工厂", "注册Fiverr账号发布服务").
4. **differentiation** (护城河): 怎么防止被卷死？
5. **monetization** (变现模式): 卖货差价 / 服务费 / 订阅费。

# Output Format (JSON Only)
{{
  "opportunity_concept": "...",
  "value_prop": "...",
  "actionable_steps": ["...", "..."],
  "differentiation": "...",
  "monetization": "..."
}}
"""

# 5. 摘要
SUMMARY_PROMPT_TEMPLATE = """
请用一段简短的中文（100字以内）总结这份报告的核心发现。
重点告诉卖家：当前最大的赚钱机会在哪里？
"""