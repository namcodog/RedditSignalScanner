# Phase 427 - 产品合同 / 系统合同统一与全面审计

## 背景

- 当前产品方向已经重新对齐到新的口径：
  - `开放提问 = 产品默认主链`
  - 默认优先级 = 冲 `Full A`
  - `topic_profile` 只是首页标准展示 / 黄金样板 / 加速路径
- 但仓库里的实现明显有历史漂移，已经不完全符合这个口径。
- 本轮目标不是继续修页面文案，而是先把“产品合同”和“系统合同”收成同一套真相，再给出达成目标的详细计划。

## 统一后的产品合同

1. 用户在当前 DB 已收录社区范围内提正常问题，系统默认应该先冲 `Full A`。
2. `Full A` 是默认优先追求的结果，不是 profile 专属特权。
3. 首页 6 张标准卡是黄金路径，负责更稳定、更快地展示 `Full A` 上限。
4. `B_trimmed / C_scouting / X_blocked` 是没打到 `Full A` 时的降级结果，不是默认预期。
5. 降级也必须有价值：要能给结论、证据和下一步动作，不能只交拦截说明。

## 统一后的系统合同

1. `topic_profile_id` 可选，不能成为系统会不会答的准入证。
2. 开放输入默认先走主链检索、召回、补量和分级，不预设为“弱报告”。
3. `A/B/C/X` 的判定应由证据硬度决定，而不是由有没有 `topic_profile` 决定。
4. `X_blocked` 只留给真正越界、严重跑偏或几乎无证据的问题。
5. 标准展示轨和开放主链都必须有正式验收用例。

## 审计结论

### 1. 首页标准卡还不是 `topic_profile` 黄金入口

- 文件：[InputPage.tsx](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/pages/InputPage.tsx)
- 当前 6 张卡点击后只会把描述填进输入框。
- 创建任务时只提交 `product_description`，没有传 `topic_profile_id`。
- 页面文案也明确写着“这些卡片只帮你快速起草，不会生成示例报告”。

结论：
- 首页标准卡和 `topic_profile` 体系现在是脱钩的。
- 这不符合“标准卡 = 黄金样板”的产品合同。

### 2. 输入页卡片数据源不是 `topic_profile`

- 文件：[guidance.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/api/routes/guidance.py)
- `/guidance/input` 当前先读 `example_library`，不足时回退 `_FALLBACK_EXAMPLES`。
- `topic_profiles.yaml` 当前只有 4 个 profile，和首页 6 张卡并不一一对应。

结论：
- 现在首页标准卡其实更像“示例文案池”，而不是“标准题黄金入口”。

### 3. API 层合同其实是对的

- 文件：[analyze.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/api/v1/endpoints/analyze.py)
- 文件：[task.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/schemas/task.py)
- `topic_profile_id` 是可选参数。
- 默认规则符合 SOP：
  - 有 `topic_profile_id` -> `audit_level = gold`
  - 无 `topic_profile_id` -> `audit_level = lab`

结论：
- 合同漂移不在 API 入口，而在后面的主链实现。

### 4. 主链代码把开放题错误拉进了硬门禁

- 文件：[analysis_engine.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/analysis/analysis_engine.py)
- 文件：[quality.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/facts_v2/quality.py)
- 当前无 `topic_profile` 的任务也会走：
  - `quality_check_facts_v2(... skip_topic_check=False)`
  - fallback 英文 token topic check
  - `topic_mismatch / range_mismatch -> X_blocked`

而 SOP 文件 [2025-12-13-facts-v2-落地SOP.md](/Users/hujia/Desktop/RedditSignalScanner/docs/sop/2025-12-13-facts-v2-落地SOP.md) 明确写的是：
- 仅在存在 `topic_profile` 时启用完整 facts_v2 质量门禁

结论：
- 这是当前最大的合同漂移点。
- 正常开放题会被误杀成 `X_blocked`。

### 5. 系统本来就具备开放题能力，但被门禁和交付截断了

- 文件：[analysis_engine.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/analysis/analysis_engine.py)
- 无 `topic_profile` 时，系统本来就会做：
  - 社区池过滤
  - topic relevant community 检索
  - 动态发现社区
  - 样本不足自动补量

结论：
- 当前问题不是“系统不会答开放题”。
- 真问题是：开放题能力已经有一半实现，但后半段被错误门禁和弱交付破坏了。

### 6. `X_blocked` 的后端和前端都在降产品分

- 文件：[analysis_rendering.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/analysis/analysis_rendering.py)
- 文件：[product-surface.ts](/Users/hujia/Desktop/RedditSignalScanner/frontend/src/lib/product-surface.ts)

当前行为：
- 后端对 `X_blocked` 只输出“报告拦截 + 原因 + 建议”
- 前端把 `X_blocked` 渲染成“线索预览 / 先看方向”的 شبه结果页

结论：
- 这不是好降级，而是“真实交付失败被 UI 包装”。
- 用户会直接感到“看不懂的废话”。

## 达成合同目标的详细计划

### Phase 31: 合同整改计划

1. 入口层
   - 把首页 6 张卡从“示例起草”改成真正的 `topic_profile` 黄金入口。
   - 卡片数据结构改为：`title / prompt / tags / topic_profile_id / route_intent`。
   - 允许保留自由输入，但要和标准卡明确分轨。

2. 提交层
   - 标准卡提交时显式带 `topic_profile_id`。
   - 自由输入不带 profile，但前端和后端都要用“默认冲 Full A”的口径。

3. 门禁层
   - 纠正 `facts_v2` 合同：
     - profile 黄金题 -> 保留完整门禁
     - 开放题 -> 不再轻易被 fallback topic mismatch 打成 `X_blocked`
   - 把 `X_blocked` 缩到真正越界、真空结果、严重跑偏。

4. 交付层
   - `B_trimmed / C_scouting / X_blocked` 都必须有结构化价值交付：
     - 当前能下的结论
     - 已经抓到的证据
     - 为什么还没到 Full A
     - 下一步怎么放大

5. 验收层
   - 新增两条正式验收主线：
     - 首页标准卡黄金路径验收
     - 无 profile 的正常开放题验收

### Phase 32: 合同修复实施顺序

1. 先修首页标准卡与 `topic_profile` 接线
2. 再修开放输入主链的门禁和分级
3. 再修 `X_blocked / C_scouting` 的报告交付
4. 最后补正式回归和真实样本验收

### Phase 33: 新合同验收标准

1. 首页 6 张卡都能稳定命中黄金路径
2. 开放输入在当前 DB 社区覆盖范围内，默认能产出接近 `Full A` 的价值报告
3. `X_blocked` 只出现在真正越界/无证据场景
4. B/C/X 都不再是“废话页”

## 这轮价值

- 把“产品方向对，但实现很乱”的问题正式拆清了。
- 这轮最大的产出不是一句判断，而是一套可以直接往下执行的合同：
  - 产品该承诺什么
  - 系统该怎么兑现
  - 当前代码偏在什么地方
  - 应该按什么顺序修
