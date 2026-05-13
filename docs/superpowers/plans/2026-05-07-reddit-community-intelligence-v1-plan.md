# Implementation Plan: Reddit 社区情报系统 v1.0 — Layer 1 社区发现

> 状态：历史版本，已被 `docs/superpowers/plans/2026-05-07-reddit-community-intelligence-phase0-plan.md` 取代。禁止把本文作为当前执行计划；本文只用于追溯曾经被审计否决的 Web / UserTrack / API 全量方案。

日期：2026-05-07
前置：CEO Review + Eng Review 已确认
目标：Web 端 v1.0，用户配置赛道 → 系统推荐社区

---

## 总览

| 阶段 | 内容 | 预估 |
|---|---|---|
| Phase 1 | 数据底座 — CommunityActivitySummary + UserTrack | 后端 |
| Phase 2 | 推荐引擎 — CommunityScoringService | 后端 |
| Phase 3 | API — Track CRUD + Recommendation | 后端 |
| Phase 4 | Web 前端 — 赛道配置 + 推荐结果 | 前端 |
| Phase 5 | 联调验收 | 全栈 |

---

## Phase 1：数据底座

### Task 1.1 — 建 UserTrack 模型

**文件**：`backend/app/models/user_track.py`

```
UserTrack 表：
  - id: UUID PK
  - user_id: FK → users.id
  - name: str（赛道名称，如"宠物用品"）
  - keywords: JSONB（关键词列表，如["狗窝","狗粮","宠物清洁"]）
  - created_at / updated_at
```

**验证**：pytest 验证模型可创建、可查询、user_id 外键约束正确。

### Task 1.2 — 建 CommunityActivitySummary 视图

**文件**：`backend/app/services/hotpost/community_activity_summary.py`

```
从 published_cards 聚合：
  - subreddit_name
  - card_count（总出卡数）
  - last_card_at（最近出卡时间）
  - hot_count / signal_count / breakdown_count（按 lane 分布）

每天 collect 后刷新。
```

**验证**：查询视图返回正确的社区活跃度数据。

### Task 1.3 — 补充 community_pool 活跃度字段

**方案**：不修改 community_pool 表结构。在 CommunityScoringService 里 JOIN CommunityActivitySummary 做评分。避免对已有表加字段的迁移风险。

---

## Phase 2：推荐引擎

### Task 2.1 — CommunityScoringService

**文件**：`backend/app/services/community/community_scoring.py`

```
class CommunityScoringService:
    def score_communities(track_keywords: list[str]) -> list[ScoredCommunity]:
        # 1. 从 community_pool 查所有活跃社区
        # 2. 对每个社区计算四维分数
        #    - relevance: categories + description_keywords 语义匹配
        #    - activity: CommunityActivitySummary.card_count + community_pool.daily_posts
        #    - long_tail: 排除 track_keywords 直接命中的头部社区
        #    - value_density: card_count / 社区规模
        # 3. 加权排序 → TOP 15
        # 4. 生成推荐理由（规则模板，非 LLM）
        #    - "该社区最近30天有{X}条关于{keywords}的讨论"
        #    - "该社区{daily_posts}日发帖量，讨论活跃"
        #    - "该社区在Hotpost出过{X}张精选卡，内容质量高"
```

**依赖**：community_pool + CommunityActivitySummary + supply_discovery_v2 YAML

**验证**：单元测试覆盖正常路径 + 空 categories、僵尸社区、无 Hotpost 数据、空关键词等边界。

---

## Phase 3：API

### Task 3.1 — Track CRUD API

**路由**：`/api/v1/tracks`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/v1/tracks | 创建赛道（name + keywords） |
| GET | /api/v1/tracks | 列出当前用户的赛道 |
| PUT | /api/v1/tracks/{id} | 修改赛道 |
| DELETE | /api/v1/tracks/{id} | 删除赛道 |

**认证**：复用已有 auth 中间件，`current_user` 依赖注入。

### Task 3.2 — Recommendation API

**路由**：`/api/v1/recommendations`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/recommendations?track_id=X | 返回该赛道的社区推荐列表 |

**响应格式**：
```json
{
  "track_id": "...",
  "track_name": "宠物用品",
  "recommendations": [
    {
      "community_name": "r/BuyItForLife",
      "score": 0.85,
      "categories": ["core_battlefield", "long_tail_gold"],
      "reason": "该社区最近30天有12条关于狗窝耐用性的讨论，讨论质量高",
      "stats": {
        "daily_posts": 45,
        "card_count": 8,
        "subscribers": 2300000
      }
    }
  ]
}
```

**验证**：API 测试覆盖正常 + track_id 不存在、无匹配社区、空赛道。

---

## Phase 4：Web 前端

### Task 4.1 — 赛道配置页 TrackConfigPage

**路由**：`/tracks`

```
页面布局：
  ┌────────────────────────────────────────┐
  │  我的赛道                                │
  │                                        │
  │  [+ 添加赛道]                           │
  │                                        │
  │  ┌──────────────────────────────────┐  │
  │  │ 🐕 宠物用品                      │  │
  │  │ 关键词：狗窝, 狗粮, 宠物清洁      │  │
  │  │ [编辑] [删除]                    │  │
  │  └──────────────────────────────────┘  │
  │                                        │
  │  ┌──────────────────────────────────┐  │
  │  │ 🤖 AI 工具                       │  │
  │  │ 关键词：LLM, Agent, RAG          │  │
  │  │ [编辑] [删除]                    │  │
  │  └──────────────────────────────────┘  │
  └────────────────────────────────────────┘
```

**交互**：点击赛道卡片 → 跳转到推荐结果页。点击 [+ 添加赛道] → 弹窗输入赛道名称和关键词。

### Task 4.2 — 推荐结果页 RecommendationPage

**路由**：`/tracks/:trackId`

```
页面布局：
  ┌────────────────────────────────────────┐
  │  ← 返回    宠物用品 · 社区推荐           │
  │                                        │
  │  🎯 核心战场                            │
  │  ┌──────────────────────────────────┐  │
  │  │ r/dogs                           │  │
  │  │ 日发帖量 120 · 已出卡 15 张       │  │
  │  │ 该社区是你赛道的直接相关社区       │  │
  │  └──────────────────────────────────┘  │
  │                                        │
  │  🔍 长尾金矿                            │
  │  ┌──────────────────────────────────┐  │
  │  │ r/BuyItForLife                   │  │
  │  │ 日发帖量 45 · 已出卡 8 张         │  │
  │  │ 最近30天有12条关于狗窝耐用性的讨论  │  │
  │  │ [👎 不感兴趣]                     │  │
  │  └──────────────────────────────────┘  │
  │  ┌──────────────────────────────────┐  │
  │  │ r/VacuumCleaners                 │  │
  │  │ 日发帖量 30 · 已出卡 3 张         │  │
  │  │ 该社区热议宠物毛发清洁问题         │  │
  │  │ [👎 不感兴趣]                     │  │
  │  └──────────────────────────────────┘  │
  └────────────────────────────────────────┘
```

### Task 4.3 — 路由注册

**文件**：`frontend/src/router/routes.ts`

新增两条路由，挂在已有 auth guard 下。

---

## Phase 5：联调验收

### Task 5.1 — 后端冒烟测试

```bash
# 创建赛道
curl -X POST /api/v1/tracks -H "Auth: ..." \
  -d '{"name":"宠物用品","keywords":["狗窝","狗粮","宠物清洁"]}'

# 获取推荐
curl /api/v1/recommendations?track_id=XXX

# 验证：返回推荐列表包含长尾社区（非头部）
```

### Task 5.2 — 前端冒烟测试

- 登录 → 看到赛道配置页
- 添加赛道 → 跳转到推荐页 → 看到推荐列表
- 标记"不感兴趣" → 该社区从列表中移除

### Task 5.3 — 回归验证

```bash
make test-backend    # 已有测试不破
make test-frontend   # 已有测试不破
make boundary-status # 小程序子仓干净
```

---

## 依赖关系

```
Phase 1 (数据底座) ──→ Phase 2 (推荐引擎) ──→ Phase 3 (API)
                                                    │
Phase 4 (前端) ─────────────────────────────────────┘
                                                    │
Phase 5 (联调) ←────────────────────────────────────┘
```

Phase 1 和 Phase 4 前端的赛道配置页可以并行开发（API 接口已定义好契约）。
