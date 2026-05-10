# CEO Review: Reddit 社区情报系统 — Phase 0 社区发现价值验证

日期：2026-05-07
来源：Claude Code office-hours → plan-ceo-review
分支：feat/hotpost-cluster-aware-recall
状态：当前执行口径已降级为 Phase 0；旧 v1 / Web / UserTrack / API 方案只作为后续假设，不是当前执行入口

---

## 前提挑战

1. **这是对的问题吗？** 对。主项目空白检索框已被证伪（要求实时搜索引擎+研究员+数据工程，Reddit API 不支持）。Hotpost 证明定时采集+发布模型可行。数据库+分析引擎已有但未被产品化。

2. **有没有更简单的方案？** 有。先做 Phase 0 只读脚本验证，不建 Web、不建 API、不建 UserTrack、不决策最终入口形态。Web 端、小程序入口或后台支撑层，都必须等 Phase 0 证明推荐结果有价值后再判断。

3. **如果什么都不做？** Hotpost 继续出卡，分析引擎继续沉睡。用户继续在 Reddit 上盲目找社区。痛点仍在。

---

## 方案愿景

从"帮用户分析 Reddit"转向"帮用户在 Reddit 上做成事"。

Phase 0 先验证一个最小判断：用户告诉系统一个赛道和关键词后，系统能不能基于 Hotpost 已发布卡 + community_pool，给出比空白搜索框更可解释、更有惊喜感的社区推荐。

---

## 范围决策表

### Phase 0（当前执行）— 只读切片验证

| 项 | 工作量 | 决策 | 原因 |
|---|---|---|---|
| HotpostCommunityActivityProvider（只读聚合） | S | ✅ 做 | 从 load_published_cards() 聚合社区活跃度 |
| phase0_preview.py（无登录推荐脚本） | S | ✅ 做 | 输入 name+keywords → 输出推荐+理由 |
| 三个固定 Fixture 验收 | S | ✅ 做 | 宠物用品 / AI工具 / 跨境电商 |
| 复用已有 community_discovery + community_ranker | — | ✅ 复用 | 不新建第三套打分器 |

### Phase 0 明确不做

| 项 | 决策 | 原因 |
|---|---|---|
| 建数据库表 | ❌ | 不改已有 schema |
| 加 API 端点 | ❌ | 先验证价值再建 API |
| 改前端 | ❌ | 先验证价值再建 UI |
| 用户登录/UserTrack | ❌ | 无登录 preview 先跑通 |
| LLM 推荐理由 | ❌ | 规则模板即可 |
| 建新打分服务 | ❌ | 复用已有 community_discovery + community_ranker |

### Phase 1+（Phase 0 通过后才做）

| 项 | 决策 | 原因 |
|---|---|---|
| 第二层（社区DNA） | ⏸ 延期 | 等第一层验证 |
| 第三层（内容策略） | ⏸ 延期 | 等前两层验证 |
| 用户系统 + Web/小程序入口 | ⏸ 延期 | Phase 0 先决定入口形态 |
| 空白检索框 + 实时搜索 | ❌ 已判死刑 | — |

---

## "对的社区"定义：四维打分模型

| 维度 | 含义 | 数据来源 | 权重 |
|---|---|---|---|
| 相关性 | 和用户赛道匹配度 | community_pool.categories + description_keywords | ⭐⭐⭐ |
| 活跃度 | 社区是否活着 | community_pool.daily_posts + quality_score + Hotpost 命中频率 | ⭐⭐⭐ |
| 长尾性 | 用户自己找不到 | 排除赛道 Top10 社区 | ⭐⭐ |
| 价值密度 | 讨论质量 | Hotpost 出卡数 + gate 通过率 | ⭐⭐ |

---

## Phase 0 验证流程

```
输入 fixture：
  name="宠物用品"
  keywords=["狗窝", "狗粮", "宠物清洁", "dog bed"]

只读聚合：
  load_published_cards()
  community_pool
  supply_discovery_v2.yaml

输出推荐：
  🎯 核心战场：直接相关且高频的社区
  🔍 长尾金矿：用户不一定知道，但 Hotpost / 社区池有证据的社区
  📊 来源说明：每条理由可追溯到已发布卡或 community_pool 字段
```

---

## 技术依赖链（Phase 0）

```
Hotpost 已发布卡（只读）
  ↓
HotpostCommunityActivityProvider（只读聚合）
  ↓
phase0_preview.py（脚本输出 JSON / Markdown）
  ↓
三个固定 fixture 决策门
```

底座不变：collect → gate → review / publish → snapshot 继续独立运行。Phase 0 不写 DB、不改 Hotpost pipeline、不改小程序。

---

## 验收标准

- 三个 fixture 全部能跑出推荐结果：宠物用品 / AI 工具 / 跨境电商
- 推荐列表 ≥40% 是非头部社区，能体现"长尾发现"
- 每条推荐附带人能看懂的理由
- 推荐理由必须可追溯到 Hotpost 卡片数据或 community_pool 字段
- 输出一份 Phase 0 评估报告，明确是否进入 Phase 1

---

## 已接受范围

当前已接受范围只有 Phase 0：只读社区发现价值验证。当前唯一执行计划是 `docs/superpowers/plans/2026-05-07-reddit-community-intelligence-phase0-plan.md`。

## 延期内容

UserTrack、API、Web 页面、小程序入口改造、Layer 2（社区DNA）、Layer 3（内容策略）、行为学习、推送通知 → 全部延期到 Phase 0 决策门之后。
