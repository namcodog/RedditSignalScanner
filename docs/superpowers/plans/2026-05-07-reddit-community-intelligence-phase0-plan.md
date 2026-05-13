# Phase 0 Plan: 社区发现价值验证（最细只读切片）

日期：2026-05-07
前置：CEO Review（方向成立）+ 用户审查（执行计划降级）
目标：用最小只读切片证明："Hotpost 广度数据 + 社区池 = 比空白搜索框更好的社区发现"

---

## 原则

- 不建新表、不建新 API、不建新前端页面
- 不改 Hotpost pipeline、不改小程序、不改已有 auth
- 只读已有数据源，输出可验收的结果
- 一个 preview 脚本跑完全部 fixture 验证

---

## Step 1：锁边界

**不碰的文件清单**（明确写入）：
- Hotpost pipeline（collect/gate/review/publish/snapshot）
- 小程序（hotpost-mini/）
- 用户系统（User 模型 + auth.py + 前端 auth）
- 数据库表结构（不建表、不加字段、不跑 migration）

**仓库状态基线**：
- 记录当前 `git status --short | wc -l` 作为基线
- 记录 `make boundary-status` 当前输出
- Phase 0 默认只新增 2 个 Python 文件；三个 fixture 写在 preview 脚本内作为固定 case，不单独新增 fixture 文件
- 决策门输出可以写 1 份评估报告；除报告外，不删不改已有系统文件

---

## Step 2：只读数据 Provider

**文件**：`backend/app/services/hotpost/hotpost_community_activity.py`

```
HotpostCommunityActivityProvider（只读，无 DB 写入）：
  - 调用 load_published_cards() 读取当前 release 的所有已发布卡
  - 按社区聚合：subreddit → {card_count, latest_card_at, lanes}
  - 按 community_pool.name_key 做 JOIN，补上 tier/categories/daily_posts/quality_score
  - 同时读 supply_discovery_v2.yaml 的社区配置（已收录的 scope/pack 映射）
  - 输出：一个按 community_name 索引的聚合 dict
```

**依赖**：`card_payload_store.load_published_cards()` + `community_pool` 表 + `supply_discovery_v2.yaml`

**不建表、不写 DB。**

---

## Step 3：无登录推荐 Preview

**文件**：`backend/scripts/community/phase0_preview.py`

输入：
```json
{
  "name": "宠物用品",
  "keywords": ["狗窝", "狗粮", "宠物清洁", "dog bed", "dog food"]
}
```

处理流程：
```
1. 调 HotpostCommunityActivityProvider 拿全量社区活跃数据
2. 对每个社区做四维打分（复用已有 community_ranker / community_discovery 的匹配逻辑，不新建打分器）：
   - relevance: community_pool.categories + description_keywords vs keywords 语义匹配
   - activity: Hotpost card_count + community_pool.daily_posts
   - long_tail: 排除 keywords 直接命中的头部社区
   - value_density: card_count / community_pool.daily_posts 比值
3. 加权排序
4. 生成推荐理由（纯规则模板，不用 LLM）
```

输出（JSON 到 stdout，Markdown 到文件）：
```
🎯 核心战场（关键词直接命中，高频社区）
  r/dogs          | 日帖120 | 已出卡15 | 理由：直接相关社区，讨论活跃
  r/Pets          | 日帖80  | 已出卡8  | 理由：直接相关社区

🔍 长尾金矿（关键词未直接命中，但有高相关讨论）
  r/BuyItForLife  | 日帖45  | 已出卡8  | 理由：近30天有12条讨论涉及狗窝耐用性
  r/VacuumCleaners| 日帖30  | 已出卡3  | 理由：社区热议宠物毛发清洁，话题持续升温
  r/NewParents    | 日帖55  | 已出卡2  | 理由：讨论宠物与婴儿共存的安全问题

📊 来源说明
  已发布卡: release-XXXXXXXX (card_count=678)
  community_pool: 当前库内社区数 XXX
  supply_discovery_v2: 覆盖 3 scope, XX 个社区
```

---

## Step 4：固定 Fixture 验收

**验收 Fixture 1：宠物用品**
```
输入：keywords=["狗窝","狗粮","宠物清洁","dog bed"]
验收标准：
  - 推荐列表包含 ≥3 个非头部社区（不是 r/dogs, r/Pets, r/puppy101）
  - 每条推荐有明确理由（不能只有"算法推荐"）
  - 推荐理由引用了 Hotpost 卡片数据或 community_pool 字段
```

**验收 Fixture 2：AI 工具**
```
输入：keywords=["LLM","Agent","RAG","Claude","AI coding"]
验收标准：
  - 推荐列表包含 ≥3 个非头部社区（不是 r/OpenAI, r/ClaudeAI, r/singularity）
  - 至少 1 条推荐来自 supply_discovery_v2 收录的社区
```

**验收 Fixture 3：跨境电商**
```
输入：keywords=["Shopify","Etsy","Amazon FBA","独立站"]
验收标准：
  - 推荐包含卖家验证层社区（如 r/AmazonSeller, r/EtsySellers）
  - 推荐包含消费者需求层社区（如 r/BuyItForLife, r/Frugal）
  - 两层的社区被明显区分（不能把卖家社区混在消费者社区里）
```

---

## Step 5：决策门

Phase 0 完成后，输出一份评估报告，回答：

1. 三个 Fixture 是否全部通过验收标准？
2. 推荐结果是否有"惊喜感"（用户自己想不到的社区比例）？
3. 推荐理由是否可解释、可追溯？
4. 当前数据厚度是否足够支撑真实用户使用？

**决策**：
- 如果通过 → 再开 Phase 1 方案审查，重新判断入口形态（小程序主入口 / Web / 后台支撑层）和是否需要 UserTrack / API / 页面
- 如果不通过 → 先补数据（扩大社区池、优化匹配逻辑），再复跑 Phase 0

---

## 不做什么（明确拒绝）

- ❌ 不建数据库表
- ❌ 不加 API 端点
- ❌ 不改前端
- ❌ 不建新打分服务（复用已有 community_discovery / community_ranker）
- ❌ 不涉及用户登录
- ❌ 不跑 LLM（推荐理由用规则模板）
