# Design: hot 真实争议占比
Date: 2026-04-14
Branch: main

## Problem Statement

当前小程序首页 `hot` 卡已经有争议图，但比例并不来自真实评论样本，而是固定桶位近似值。结果是：

- 多张卡比例看起来差不多
- 首页有爆点，但缺少可信度
- 不能当成真实舆情结构使用

目标不是继续调图表样式，而是让 `hot` 争议图变成**小程序独立发布链里、基于真实 Reddit 评论样本的离线预计算结果**。

## Premise Challenges

- 这次只做 `hot`，不扩到 `signal / breakdown`。
- 这次不依赖 dev DB，不把小程序链绑到 `comments / comment_llm_labels`。
- 这次也不是前端实时分析。前端只展示，真实比例必须在 mini 发布前算好。
- 这次不改 `controversy_chart` schema，不开第二套协议。

## Existing Leverage

- `hot` 发布卡已经有稳定帖子锚点：
  - `source_link`
  - `signal_id`
- 现有 mini 发布链已经固定：
  - `backend/scripts/hotpost/push_mini_snapshot.py`
  - `backend/app/services/hotpost/mini_snapshot.py`
- 现有 Reddit 客户端已经能直接抓单帖评论：
  - `backend/app/services/infrastructure/reddit_client.py`
  - `fetch_post_comments(post_id, ...)`
- 小程序前端图表合同已存在：
  - `backend/app/schemas/hotpost_clues.py`
  - `hotpost-mini/hotpost-mini-app/src/services/clues.ts`

## Options Considered

### Option A: 继续用固定桶位，只调更多比例档位
- What: 不抓评论，只把比例模板做细一点
- Effort: S
- Risk: High
- Best for: 只想让界面“看起来不一样”
- Reject reason: 本质还是假的，不能解决模板感

### Option B: 依赖 dev DB 评论和标签表聚合
- What: 用现有 `comments / comment_llm_labels` 做真实比例
- Effort: M
- Risk: Medium
- Best for: 内部分析链
- Reject reason: 和“小程序独立线”边界冲突，用户已明确不要这条依赖

### Option C: mini 发布前直抓 Reddit 评论，离线一次性做 stance 汇总
- What: 对每张 `hot` 卡，依据 `source_link` 在发布前抓评论样本，用 LLM 一次性做 `support / oppose / neutral` 汇总，再写回 `controversy_chart`
- Effort: M
- Risk: Medium
- Best for: 小程序独立线、真实效果、最小改动
- Recommendation: 选这个

## Chosen Direction

选 **Option C**。

### 核心原则

1. 只做 `hot`
2. 小程序链独立，不依赖 dev DB
3. 评论样本在 mini 发布前直接抓 Reddit API
4. 真实比例在发布前离线算好，写入现有 `controversy_chart`
5. 样本不足时降级，不伪装
6. LLM 不做低价值逐条慢标，而是做高价值的“争议结构压缩”

## Data Flow

```text
published hot card
  -> source_link
  -> parse reddit post_id
  -> reddit_client.fetch_post_comments(post_id, mode=smart_shallow, limit=40~60)
  -> filter eligible comments
  -> single-card LLM stance summarizer
  -> support/oppose/neutral counts + representative points + debate_focus
  -> controversy_chart
  -> mini_snapshot / mini_release_cards
  -> mini app
```

## Why This Works

- 不需要依赖数据库已有评论覆盖率
- 不会把小程序发布链和内部分析库绑死
- 每张 `hot` 卡只需一次离线抓取 + 一次离线总结
- 前端 schema 不变，首页/详情页不用再重做协议
- Reddit 抓取不可控时，LLM 可以把有限样本压成更有产品价值的“分歧结构”，而不是只做浅层情绪分数

## Minimal Change Set

### New backend modules

- `backend/app/services/hotpost/hot_comment_sample.py`
  - 从 `source_link` 解析 `post_id`
  - 调 `reddit_client.fetch_post_comments(...)`
  - 过滤有效评论样本

- `backend/app/services/hotpost/hot_controversy_llm.py`
  - 接收单张卡的评论样本
  - 返回：
    - `support_ratio`
    - `oppose_ratio`
    - `neutral_ratio`
    - `support_point`
    - `oppose_point`
    - `neutral_point`
    - `debate_focus`
    - `dominant_side`
    - `confidence`

### Existing files to update

- `backend/app/services/hotpost/hot_controversy_chart.py`
  - 从固定桶位近似值，改为优先调用真实离线结果
  - 只保留“样本不足时的低置信降级”，不再回退固定模板

- `backend/app/services/hotpost/mini_snapshot.py`
  - 在 `_sanitize_card_for_snapshot` / 发布路径中接入真实争议图生成

- `backend/scripts/hotpost/push_mini_snapshot.py`
  - 增加开关：
    - 默认启用真实 `hot` 争议图生成
    - 允许 `--skip-hot-controversy-refresh` 做快速跳过

### Audit fields to persist

这些字段允许只写进发布产物内部，不要求前端展示，但必须可追：

- `controversy_meta.post_id`
- `controversy_meta.sample_size`
- `controversy_meta.sampled_at`
- `controversy_meta.fetch_status`
- `controversy_meta.llm_summary_version`

## Comment Sample Contract

### Sample source

- 来源：Reddit API
- 锚点：`source_link`
- 抓取器：`reddit_client.fetch_post_comments`

### Sample size

- 目标：`20~40` 条有效评论
- 请求上限：`40`
- 最低门槛：`12`

### Fetch budget

- 每张 `hot` 卡只抓一次
- 默认参数：
  - `mode="smart_shallow"`
  - `limit=40`
  - `depth=2`
- 必须有总超时
- 单张卡抓取失败不能拖慢整次 mini 发布

### Comment eligibility

- 去掉：
  - 纯链接
  - 纯表情
  - 过短噪音
  - 明显重复
- 保留：
  - 高分主评论
  - 少量低分反对声音
  - 少量新评论，避免只看高赞回音室

## LLM Role

LLM 不做前端实时分析，也不做逐条慢标注导库，更不负责“脑补比例”。

这次 LLM 只做一件事：

- 对**单张 `hot` 卡的一批评论样本**做一次性 stance 汇总

### LLM value amplification

这次要主动放大 LLM 的价值，不把它浪费在低价值分类上。

LLM 必须重点做好这 4 件事：

1. **立场归并**
   - 把语气不同、表达不同、但本质相同的评论归并成同一派
2. **分歧点提炼**
   - 用一句话说清这帖到底在吵什么
3. **代表观点抽取**
   - 给支持 / 反对 / 中性各留一句最典型的话
4. **置信度判断**
   - 样本少、观点散、噪音重时，主动给 `confidence=low`

输出必须是结构化 JSON：

- `support_comments`
- `oppose_comments`
- `neutral_comments`
- `support_point`
- `oppose_point`
- `neutral_point`
- `debate_focus`
- `confidence_reason`
- `sample_quality`

然后 ratio 由代码按计数算：

- `support_ratio = support_comments / total`
- `oppose_ratio = oppose_comments / total`
- `neutral_ratio = neutral_comments / total`

这样比“每条评论单独调 LLM”更轻，也更适合 mini 发布链，而且能把有限样本压成真正有产品价值的争议结构。

## Controversy Chart Generation

保持现有 schema：

- `support_ratio`
- `oppose_ratio`
- `neutral_ratio`
- `support_point`
- `oppose_point`
- `neutral_point`
- `debate_focus`
- `dominant_side`
- `confidence`

### Confidence rules

- `high`
  - 有效样本 `>= 24`
  - 主导方占比 `>= 0.15` 高于第二名
- `medium`
  - 有效样本 `>= 12`
- `low`
  - 有效样本 `< 12`
  - 或抓取失败
  - 或 LLM 结构化结果不通过

### Low confidence behavior

- 允许出图
- 但比例必须来自真实样本，不能再回退固定桶位
- 允许前端后续弱化显示，但这次不要求改前端逻辑

### Failure behavior

以下任一情况，统一进入真实低置信降级：

- `source_link` 解析不出 `post_id`
- Reddit 评论抓取失败
- 有效评论 `< 12`
- LLM 结构化输出不通过

降级规则：

- `confidence = low`
- 比例仍然只允许来自真实样本
- 禁止回退旧模板桶位

## Tests

### Unit tests

- `backend/tests/services/hotpost/test_hot_comment_sample.py`
  - `source_link -> post_id` 解析正确
  - 评论过滤后样本量正确
  - 去重 / 去噪有效

- `backend/tests/services/hotpost/test_hot_controversy_llm.py`
  - LLM 输出结构校验
  - ratio 计数正确
  - `dominant_side` 正确
  - `confidence` 分级正确

### Integration tests

- `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`
  - `hot` 卡 snapshot 中 `controversy_chart` 满足新合同
  - 不再断言固定桶位

## Success Criteria

1. `hot` 图表比例来自真实 Reddit 评论样本，而不是模板桶位
2. 同一批 `hot` 卡比例组合明显拉开，不再大量重复
3. `support / oppose / neutral` 与代表观点一致
4. 小程序首页和详情页继续吃同一份 `controversy_chart`
5. 整条链只依赖 mini 发布前离线步骤，不依赖 dev DB
6. LLM 的价值必须体现在：
   - 同义立场归并
   - 分歧点提炼
   - 代表观点抽取
   - 低置信识别

## Acceptance Contract

这是新的固定合同，覆盖旧版 “dev DB 评论聚合” 口径。

### A. 独立线边界

1. 实现必须只围绕小程序发布链展开：
   - `push_mini_snapshot.py`
   - `mini_snapshot.py`
   - `mini_release_cards`
2. 不依赖 dev DB。
3. 不要求 `comments / comment_llm_labels` 参与。

### A2. 工程口子

1. 每张 `hot` 卡评论抓取只能发生一次
2. 必须使用固定抓取预算：
   - `mode="smart_shallow"`
   - `limit=40`
   - `depth=2`
3. 必须有总超时，不能拖垮整次 mini 发布
4. 发布产物里必须留下可追字段：
   - `post_id`
   - `sample_size`
   - `sampled_at`
   - `fetch_status`
   - `llm_summary_version`

### B. 数据真实性

1. `support_ratio + oppose_ratio + neutral_ratio = 1.0`，允许误差 `±0.01`
2. `dominant_side` 必须等于最高占比一方
3. `support_point / oppose_point / neutral_point / debate_focus` 必须来自该帖真实评论样本
4. 不允许回退固定桶位：
   - `35 / 35 / 30`
   - `35 / 40 / 25`
   - `40 / 35 / 25`
   - `35 / 45 / 20`

### C. 样本量门槛

1. 单张 `hot` 卡目标有效评论样本：`20~40`
2. 单张 `hot` 卡最低门槛：`12`
3. 少于 `12` 条：
   - `confidence = low`
   - 仍只能输出真实样本聚合结果，不能伪造强分布

### C2. LLM 价值合同

1. LLM 必须做“争议结构压缩”，不是只做简单情绪打分
2. 输出里必须同时包含：
   - 三类计数
   - 三类代表观点
   - `debate_focus`
   - `sample_quality`
   - `confidence_reason`
3. 如果评论表达是反讽、半支持半反对、或多种说法指向同一立场，LLM 必须负责归并，不允许简单按字面情绪切碎
4. 如果样本噪音过高，LLM 必须主动降 `confidence`

### D. 小程序展示合同

1. 前端继续使用现有 `controversy_chart` schema
2. 首页 `hot` 卡必须继续显示：
   - 支持占比
   - 反对占比
   - 中性占比
3. 首页与详情页语义必须一致

### E. 差异性验收

抽样最近 `10` 张 `hot` 卡：

1. 至少 `8` 张卡来自真实抓取评论样本
2. 至少 `6` 张卡的比例组合彼此不同
3. 如果仍大面积重复旧模板分布，视为失败

### F. 测试合同

必须补齐并通过：

1. `backend/tests/services/hotpost/test_hot_comment_sample.py`
2. `backend/tests/services/hotpost/test_hot_controversy_llm.py`
3. `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`

## NOT in Scope

- `signal / breakdown`
- 前端 schema 改造
- 实时情绪分析
- 依赖 dev DB 的评论聚合
- 品牌舆情后台
