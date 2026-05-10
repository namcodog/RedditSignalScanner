# Eng Review: Reddit 社区情报系统 v1.0 — Layer 1

> 状态：历史审查记录，保留当时判断和错误供追溯；已被 Phase 0 只读切片方案取代。禁止把本文中的 UserTrack / Web / API / CommunityScoringService 作为当前执行依据。

日期：2026-05-07
状态：审查完成 — DONE_WITH_CONCERNS

---

## Step 0：范围挑战

### 1. 现有代码杠杆

| 子问题 | 已有代码 | 能直接用？ |
|---|---|---|
| 用户注册/登录 | `User` 模型 + `auth.py` + `LoginPage` + `RegisterPage` | ✅ 完全复用，不做任何修改 |
| 社区元数据 | `community_pool` 模型 | ✅ 直接查询 |
| 社区活跃度 | Hotpost 产出 | ⚠️ 需新建聚合查询 |
| 社区发现链 | `discovered_community` 模型 | ✅ 并入推荐池 |
| 关键词匹配 | `analysis_engine` 函数 | ✅ 复用逻辑 |
| 前端框架 + 登录体系 | React + TS + Vite + LoginPage + 路由守卫 | ✅ 新页面挂同一条 auth 链路 |

**结论**：不是新建系统，是在现有底座上加一层"信号分发层"。最大工作量在融合引擎和 Web 前端。

### 2. 最小变更集

```
必须新建：
  - CommunityScoringService（四维打分融合层）
  - UserTrack 模型（用户-赛道关联）
  - Track CRUD API（/api/tracks）
  - Recommendation API（/api/recommendations）
  - Web 前端（赛道配置页 + 推荐结果页，挂已有 auth 链路）

必须修改：
  - community_pool 模型：加 Hotpost 活跃度字段（或单独建聚合表）

不碰：
  - 用户系统（User 模型 + auth.py + 前端登录注册页面，完全复用）
  - Hotpost pipeline（独立运行）
  - 小程序（后端 API 留接口即可）
  - analysis_engine（只读数，不改）
  - crawl 系统
```

### 3. 复杂度检查

| 组件 | 类型 | 复杂度 |
|---|---|---|
| UserTrack 模型 | 1 个新表 | 低 |
| CommunityScoringService | 1 个新 Service（约 200 行） | 中 |
| Track API | 标准 CRUD（4 个端点） | 低 |
| Recommendation API | 1 个 GET 端点 | 低 |
| Web 前端 | 2 个新页面 + 1 个组件 | 中 |

**总计**：~5 个新文件后端 + ~5 个新文件前端。不超过 8 文件/2 服务阈值。✅

### 4. 完整性检查

v1.0 是 **完整实现**，不走捷径：
- 用户系统完整（注册/登录/session）
- 推荐引擎完整（四维打分 + 理由生成）
- 前端交互完整（配置 + 浏览 + 标记反馈）

AI 辅助下成本可控。不做半成品。

---

## 一、架构审查

### 整体架构

```
┌──────────────────────────────────────────────────────┐
│                     Web 前端 (React)                   │
│  LoginPage → TrackConfigPage → RecommendationPage     │
└──────────────────────┬───────────────────────────────┘
                       │ REST API
┌──────────────────────┴───────────────────────────────┐
│                   API Layer (/api/v1)                  │
│  auth router (已有)  track router (新)  rec router (新) │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────────┐
│                Service Layer (新)                      │
│  CommunityScoringService                              │
│  ├── RelevanceScorer (community_pool categories)      │
│  ├── ActivityScorer (Hotpost hit count + daily_posts) │
│  ├── LongTailScorer (exclude top-N communities)       │
│  └── ValueDensityScorer (card throughput)             │
└──────┬──────────────────────┬────────────────────────┘
       │                      │
┌──────┴──────┐    ┌─────────┴──────────┐
│ community_  │    │ Hotpost 聚合视图    │
│ pool (已有) │    │ (新建——查询已发布   │
│             │    │  卡的社区分布)      │
└─────────────┘    └────────────────────┘
```

### 依赖关系

```
CommunityScoringService 依赖：
  → community_pool 表（只读）                    ✅ 已有
  → Hotpost published_cards（只读，需要新查询）  ⚠️ 新建
  → supply_discovery_v2 YAML（只读）             ✅ 已有

TrackService 依赖：
  → User 表（只读）                              ✅ 已有
  → UserTrack 表（读写）                         ⚠️ 新建

无循环依赖。所有新组件单向依赖已有组件。
```

### 数据流

```
用户配置赛道"宠物用品"
  → TrackService 存入 UserTrack
  → CommunityScoringService 被调用
    → RelevanceScorer: 匹配 community_pool.categories 和 description_keywords
    → ActivityScorer: 查 community_pool.daily_posts + Hotpost 命中次数
    → LongTailScorer: 排除 r/dogs, r/Pets 等头部社区
    → ValueDensityScorer: 该社区在 Hotpost 的出卡数
  → 四维加权 → 排序 → TOP N
  → 推荐理由生成（LLM 将 scoring 理由转自然语言）
  → API 返回 → Web 端渲染
```

### 生产环境故障场景

| 故障 | 影响 | 降级策略 |
|---|---|---|
| community_pool 查询慢 | 推荐延迟高 | 加 Redis 缓存（社区元数据变化慢） |
| Hotpost 数据不可用 | ActivityScorer 无数据 | 降级为只用 daily_posts，标记"活跃度数据可能不完整" |
| LLM 理由生成超时 | 推荐无理由 | 返回模板理由（"该社区有 X 条相关讨论"） |
| 用户赛道为空 | 推荐无输入 | 返回热门社区作为默认推荐 |

### 安全

- 认证：复用已有 `auth.py` 的 JWT/session 机制
- 授权：推荐结果仅返回当前用户的赛道相关社区（不看其他用户数据）
- API 边界：所有新端点走同一认证中间件

---

## 二、代码质量审查

### 需要关注的点

1. **community_pool 的老数据问题**：部分社区的 `daily_posts` / `quality_score` 可能过时。v1.0 权重应偏 Hotpost 活跃度（新数据），community_pool 元数据做辅助匹配。

2. **CommunityScoringService 不要太聪明**：四维打分是加权求和，不是 ML 模型。v1.0 用简单规则，不做推荐系统优化。v1.1 再考虑行为学习。

3. **不要建 `community_scores` 表**：社区评分应该每次实时计算（数据量小，几百个社区），不要提前物化。物化会引入"评分与最新数据不同步"的 bug。

---

## 三、测试覆盖审查

### 新代码路径追踪

```
CommunityScoringService.score_communities(track_keywords)
  │
  ├── fetch_communities() → community_pool 查询
  │   ├── [+] 正常返回社区列表
  │   ├── [缺口] 空结果（用户赛道太偏门）
  │   └── [缺口] 数据库连接失败
  │
  ├── score_relevance(community, keywords)
  │   ├── [+] 匹配到 categories
  │   ├── [+] 匹配到 description_keywords
  │   └── [缺口] categories 为空 JSONB
  │
  ├── score_activity(community)
  │   ├── [+] 正常返回 daily_posts + hotpost_hit_count
  │   ├── [缺口] hotpost 数据源不可用 → 降级
  │   └── [缺口] daily_posts 为 0（僵尸社区）
  │
  ├── score_long_tail(community, top_communities)
  │   └── [+] 头部社区被正确降权
  │
  ├── score_value_density(community)
  │   └── [缺口] 该社区从未在 Hotpost 出过卡 → 默认为 0
  │
  └── generate_reason(community, scores)
      ├── [+] 正常生成推荐理由
      └── [缺口] LLM 不可用 → 降级为模板理由

Track CRUD API
  │
  ├── POST /api/tracks → 创建赛道
  │   ├── [+] 正常创建
  │   ├── [缺口] 关键词为空
  │   └── [缺口] 重复赛道（幂等处理）
  │
  └── GET /api/recommendations?track_id=X
      ├── [+] 正常返回推荐
      ├── [缺口] track_id 不存在
      └── [缺口] 该赛道无匹配社区 → 返回空列表 + 提示
```

### 补充测试到方案中

| 测试文件 | 测试内容 | 类型 |
|---|---|---|
| `test_community_scoring.py` | 四维打分正常+边界（空 categories, 僵尸社区, 降级路径） | 单元 |
| `test_track_api.py` | CRUD 正常+边界（空关键词, 重复, 不存在） | 单元 |
| `test_recommendation_api.py` | 推荐正常+边界（空结果, 降级） | 单元 |
| `test_track_config_e2e.py` | Web 端：注册 → 配置赛道 → 看到推荐 | E2E |

---

## 四、性能审查

| 关注点 | 评估 | 措施 |
|---|---|---|
| community_pool 查询 | 几百条数据，单次 <50ms | 无需优化 |
| Hotpost 聚合查询 | 需要 JOIN published_cards | 建一个 `community_activity_summary` 视图或物化表，每天 collect 后刷新一次 |
| LLM 理由生成 | 每条推荐 1 次 LLM 调用 | v1.0 不实时调 LLM——用规则模板生成理由（"该社区最近 30 天有 X 条关于 Y 的讨论"），v1.1 再考虑 LLM |
| 前端渲染 | 推荐列表 <20 条 | 无性能问题 |
| 推荐刷新频率 | 用户改赛道时实时计算 | 无需缓存 |

---

## 完成状态：DONE_WITH_CONCERNS

### Concern 1：Hotpost 聚合数据不可直接查询

当前 Hotpost 的社区活跃度信息散落在 `published_cards` 和 `supply_discovery_v2.yaml` 里，没有统一的"社区活跃度"查询入口。需要建一个聚合视图或轻量汇总表。

**缓解**：每天 collect 后自动刷新 `community_activity_summary`，社区推荐引擎读这个表。

### Concern 2：community_pool 老数据风险

部分社区的 `daily_posts` 可能严重过时。v1.0 的 ActivityScorer 应优先使用 Hotpost 命中数据（新鲜），community_pool.daily_posts 仅作为无 Hotpost 数据时的 fallback。

### Concern 3：LLM 理由生成的成本和延迟

如果每条推荐调 LLM 生成理由，20 条推荐 = 20 次 LLM 调用。v1.0 先用规则模板，把"本社区最近 X 天有 Y 条关于 Z 的讨论"这种硬数据渲染成自然语言，不需要 LLM。
