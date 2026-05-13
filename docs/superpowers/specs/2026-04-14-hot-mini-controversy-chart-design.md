# Design: hot mini 争议图表卡最小架构
Date: 2026-04-14
Branch: main

## Problem Statement

当前小程序首页的 `hot` 卡，用户需要读完多行文字才知道“这张卡为什么值得看”。这不符合 `hot` 的天然优势。

这次要解决的是：
- 让用户一眼看懂这条 `hot` 讨论在争什么
- 把 `hot` 从“信息卡”抬成“争议雷达”
- 只在小程序展示链加最小能力，不把主分析链整体重做

## Premise Challenges

- 挑战 1：不能把“情绪分析”理解成一定要先做全量精确 NLP 百分比。
  - 结论：`v1` 先做小程序可用的 `争议占比估算 + 观点摘要`，不是全仓评论标注系统改造。
- 挑战 2：不能为了小程序首页效果，把 `signal / breakdown` 一起拉进来。
  - 结论：第一版只做 `hot`。
- 挑战 3：不能新起一套接口或一套临时 JSON。
  - 结论：继续走现有 `mini snapshot -> miniRelease -> CluePreviewCard/详情页` 这条链。
- 挑战 4：不能让首页变成新一轮长篇阅读。
  - 结论：首页只放图表 + 1 行分歧点，支持/反对/中性观点保持极短。

## Options Considered

| 方案 | What | Effort | Risk | Best for |
|---|---|---:|---|---|
| A. 纯前端假图表 | 用现有 `flashpoint/fight_line` 手写映射出三柱图，不新增数据字段 | S | High | 只想做演示图，不在意真伪 |
| B. mini-only 争议摘要层 | 在 `mini_snapshot` 发布时，只给 `hot` 卡补一层 `controversy_chart` 字段，小程序直接展示 | M | Low | 追求最小可落地且不污染主链 |
| C. 全量评论标注接入 hot 发布链 | 把评论级 labeling 聚合正式接进 hot 产卡主链，再下发精确占比 | L | Med/High | 以后要做品牌舆情服务正式版 |

## Chosen Direction

选择 **B. mini-only 争议摘要层**。

原因：
- 它能直接服务小程序首页爆点表达。
- 它不需要重做 `hot` 主链，也不需要改 `signal/breakdown`。
- 它能保持当前发布链不变：
  - `published card`
  - `mini_snapshot`
  - `mini_release_cards`
  - `miniRelease`
  - `CluePreviewCard`
- 后面如果要升级成更真的评论聚合版，也能无痛替换字段生成逻辑，不会推翻前端。

## Minimal Architecture

### 1. 数据合同

只给 `hot` 卡新增一个可选字段：

```json
{
  "controversy_chart": {
    "support_ratio": 0.35,
    "oppose_ratio": 0.45,
    "neutral_ratio": 0.20,
    "support_point": "只是短期波动，先别慌",
    "oppose_point": "不是波动，是持续下滑",
    "neutral_point": "先看接下来几天的数据",
    "debate_focus": "到底是单日异常，还是长期转差",
    "dominant_side": "oppose",
    "confidence": "medium"
  }
}
```

约束：
- 只允许出现在 `lane=hot` 的卡片上
- `ratio` 三项总和必须为 `1.0`
- 首页只展示：
  - 三柱图
  - `debate_focus`
- 详情页再展示：
  - 支持观点
  - 反对观点
  - 中性观点

### 2. 数据生成位置

只放在 `mini snapshot` 发布阶段生成，不改小程序运行时。

```text
published hot card
    ↓
mini_snapshot adapter
    ↓
给 hot 卡补 controversy_chart
    ↓
latest.json / mini_release_cards
    ↓
miniRelease 云函数
    ↓
小程序首页 / 详情页
```

原因：
- 小程序不做实时分析
- 不新增云函数接口
- 不新增云端集合
- 回滚时只要回滚 release

### 3. 前端显示结构

#### 首页 hot 卡

首页不是“加信息”，而是“换信息顺序”。

当前 `hot` 卡结构：
- 标签行
- 标题
- 摘要长文
- 讨论热度
- 围观人群
- 为什么会火
- 高赞原话

改成：
- 标签行
- 标题
- 争议三柱图
- 分歧点
- 围观人群
- 为什么会火
- 支持派 / 反对派一句话
- 看详情

替换规则：
- `摘要长文` → `争议三柱图`
- `讨论热度主体文案` → `分歧点`
- `高赞原话` → `支持派 / 反对派一句话`
- `围观人群` 保留
- `为什么会火` 保留，但缩成一句

#### 首页 hot 卡线框

```text
[近期爆帖] [🔥 正在火] [今天]                     [收藏]

Sam Altman 家遭枪击这帖火了，大家在吵这到底是治安事件，还是反 AI 情绪外溢

┌────────────────────────────────────┐
│ 支持  35%   反对  45%   中性  20% │
│   ▇▇▇        ▇▇▇▇        ▇▇       │
└────────────────────────────────────┘

分歧点：这到底只是个体安全事件，还是反 AI 情绪已经开始外溢到现实

👤 围观人群：关注 AI 行业风险、平台舆情和科技人物安全的人

为什么会火：讨论已经不只是在聊案件本身，而是在争论反 AI 情绪会不会继续外溢。

支持派：先看治安因素，不要过度政治化。
反对派：这已经不只是治安，背后就是反 AI 情绪。

                                                     看详情 →
```

#### 首页 hot 卡视觉约束

- 不推翻当前奶油底、圆角、细金线风格
- 图表区不做黑底、不做重阴影、不做信息屏感
- 三柱图使用现有语义色：
  - 支持：绿色
  - 反对：红色
  - 中性：灰金色
- `分歧点` 继续沿用当前 `why-now` 那种浅底 + 左金线样式
- `支持派 / 反对派` 不做大卡，改成两条短行，避免首页重新变重

#### 首页 hot 卡交互约束

- 点击整张卡仍然进详情
- 三柱图本身不单独可点，避免把首页变成操作面板
- 收藏按钮位置不变
- 首屏只需要让用户“看懂分裂”，不要求在首页完成全部阅读

#### 详情页 hot 卡

在现有 `HotValidateBlock` 上方或下方新增一个 `争议雷达` 区块：

- 三柱图
- 支持观点
- 反对观点
- 中性观点
- 分歧点

#### 详情页 hot 卡新增区块结构

```text
争议雷达

[支持 35%] [反对 45%] [中性 20%]
  ▇▇▇         ▇▇▇▇         ▇▇

支持派在说什么
只是短期波动，先别慌。

反对派在说什么
不是波动，是持续下滑。

中立派在等什么
先看接下来几天的数据。

分歧点
到底是单日异常，还是长期转差。
```

详情页目的不是更花，而是把首页“看懂冲突”这件事补全。

## UI Implementation Notes

- 首页只增加 1 个新模块：`HotControversyPreview`
- 详情页只增加 1 个新模块：`HotControversyBlock`
- 这两个模块共用同一份 `controversy_chart` 数据，不重复组装
- 样式优先复用：
  - `clue-why-now`
  - `detail-item`
  - `detail-item-title`
  - `clue-signal-badge`
- 不新增第二套主题色系统

## Minimal Change Set

推荐只动这 6 个点：

1. `backend/app/services/hotpost/mini_snapshot.py`
   - 给 `hot` 卡注入 `controversy_chart`
2. `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`
   - 补 snapshot 字段合同测试
3. `hotpost-mini/hotpost-mini-app/src/services/clues.ts`
   - 增加 `controversy_chart` 类型
4. `hotpost-mini/hotpost-mini-app/src/components/CluePreviewCard.tsx`
   - 首页 `hot` 卡渲染图表
5. `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-sections.tsx`
   - 详情页 `hot` 图表区块
6. `hotpost-mini/hotpost-mini-app/src/styles/clues.scss`
   - 图表样式

如果要继续压缩范围，第一轮甚至可以不做详情页，只做首页 `hot` 卡。

## Ratio Generation Strategy

第一版不接全量评论标注系统，走 `估算版`：

- 输入材料：
  - `title`
  - `summary_line`
  - `why_now`
  - `detail.flashpoint`
  - `detail.fight_line`
  - `quotes`
- 输出：
  - `support_ratio`
  - `oppose_ratio`
  - `neutral_ratio`
  - 3 条极短观点
  - 1 条分歧点

口径要求：
- 结果用于“小程序争议读秒”，不是法务级舆情统计
- 比例按 `5%` 或 `10%` 粒度输出，避免假精度
- `confidence=low` 时可只显示“分歧明显”，不显示具体百分比

## Success Criteria

- 首页 `hot` 卡无需长阅读，用户一眼能看到：
  - 有没有分歧
  - 哪一边更占上风
  - 双方在吵什么
- 非 `hot` 卡完全不受影响
- 小程序不新增运行时请求
- 发布与回滚仍然沿用当前 `snapshot-first` 链

## Risks

- 风险 1：比例看起来太像真统计
  - 规避：第一版明确用粗粒度比例 + `confidence`
- 风险 2：首页重新变复杂
  - 规避：首页只放图，不展开三段长说明
- 风险 3：把 `hot` 特性扩散到其他 lane
  - 规避：字段和组件都只对 `lane=hot` 生效

## NOT in Scope

- 不给 `signal` 做争议图
- 不给 `breakdown` 复用同一模板
- 不接全量评论 NLP 标注主链
- 不做新的小程序接口或新的云数据库集合
- 不在小程序端实时算比例
