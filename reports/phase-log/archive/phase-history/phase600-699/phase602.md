# Phase 602 - Hotpost rant 咖啡机泛抱怨链路深诊断与中文解读收口

## 目标

- 回答当前小程序 `rant` 页面是不是在展示后端完整结果。
- 以 `大家最常吐槽咖啡机什么?` 为例，把“英文原贴搬运、分析很浅、下一步缺失”拆成可执行根因。
- 只修 `rant`，不误伤 `trending`。

## 发现

### 1. 前端不是在原样展示后端整包结果

当前小程序详情页会先经过两层收缩：

1. `hotpost-detail-cache.ts`
   - 只保留一份压缩后的 `HotpostResult`
2. `friction/helpers.ts + sections.tsx`
   - 再把后端字段投影成页面块

所以页面上看到的浅，不只是主观感觉，确实有字段丢失和表达顺序问题。

### 2. 这次“分析浅”不只是前端问题，后端真结果之前也确实跑偏

对 query：

- `大家最常吐槽咖啡机什么?`

最初 live 真结果里出现：

- `query_parts = ["coffee machine complaints", "coffee machine maintenance"]`
- `keywords = ["coffee", "machine", "maintenance"]`

这说明：

- `fast LLM` 把泛吐槽问题缩窄成了 `maintenance`
- 检索自然会偏到清洗/维护/低维护

更关键的是：

- 新写的“泛吐槽别缩窄”规则，之前只在新生成 query 上生效
- 命中旧 `hotpost:query_translate:*` cache 时，老窄 query 仍会被原样放出来

所以主因不是一句“推理模型不行”，而是：

1. fast 结构化有方差
2. cache 绕过新规则
3. 前端又把有限信息投得更薄

### 3. 代表帖子和用户原话之前不够像中文判断

之前页面的问题有三层：

- `代表帖子`
  - 中文解释没有站在第一屏
  - 用户第一眼还是被英文标题和英文摘要压住
- `用户原话`
  - generic product complaint 的解释不够具体
- `下一步`
  - 当 `pain_points` 没立起来时，容易只剩追问词，没有动作建议

## 已完成修复

### 1. 旧 query 缓存也纳入泛吐槽规范化

文件：

- `backend/app/services/hotpost/query_resolver.py`

已改成：

- 命中旧 query translate cache 时
- 仍然执行 `generic rant discovery` 规范化
- 不再让老缓存把：
  - `coffee machine maintenance complaints`
  重新带回链路

同时补回：

- `complaints` 这个泛吐槽锚点到 `keywords`

### 2. generic product complaint 的帖子中文解读补强

文件：

- `backend/app/services/hotpost/response_bundle.py`

新增了 generic：

- `trust gap`
- `value gap`
- `effort gap`

的帖子级中文解读。

现在代表帖子会优先给出：

- 这帖主要在讲什么
- 抱怨点集中在哪

而不是只给：

- `直接命中: coffee, machine`
- `社区语境待验证`

### 3. generic product complaint 的原话中文解释补强

文件：

- `backend/app/services/hotpost/quality_contract.py`

新增了：

- `scam / misleading / support told me`
- `underwhelming / waste of money / too weak`
- `maintenance / cleaning / hassle / learning curve`

这几类原话的中文判断。

### 4. 前端先展示中文判断，再展示英文原文

文件：

- `hotpost-mini/hotpost-mini-app/src/pages/friction/sections.tsx`

已改成：

- `代表帖子`：先展示 `这帖主要在说什么`
- 再展示：
  - `原帖标题`
  - `原帖摘要`
- `用户原话`：先展示 `这句话说明了什么`
- 再展示英文原话

也就是说，页面现在先给用户中文价值，再给原始 Reddit 证据。

## 验证

### 定向测试

```bash
cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest \
  tests/services/hotpost/test_hotpost_query_resolver.py \
  tests/services/hotpost/test_hotpost_response_bundle.py \
  tests/services/hotpost/test_hotpost_quality_contract.py -q
```

结果：

- `41 passed`

### 小程序编译

```bash
npm --prefix hotpost-mini/hotpost-mini-app run build:weapp
```

结果：

- `Compiled successfully`

### rant live 复验

query：

- `大家最常吐槽咖啡机什么?`

关键结果：

- `status = completed`
- `from_cache = false`
- `mode_state = standard`
- `query_parts = ["coffee machine complaints", "coffee machine"]`
- `keywords = ["coffee", "machine"]`
- `subreddits = ["r/coffee", "r/espresso", "r/superautomatic"]`
- `pain_points` 已恢复：
  - `为什么人看了不买`
  - `为什么人看了不信`
- `recommended_actions` 已恢复两条中文动作建议

代表帖子现在已经能直接给中文判断，例如：

- `帖子直接指控 HiBrew H13 咖啡机为“SCAM”，并提供客服虚假承诺功能的具体细节，是“虚假宣传”痛点的核心证据。`
- `用户新购咖啡机后，发现做出的咖啡味道淡，直接提出了“性能不符预期”的具体问题。`

### trending 烟雾验证

query：

- `shopify chargeback evidence response workflow`

结果：

- `status = degraded`
- `from_cache = false`
- `mode_state = preview`

说明这轮改动没有把 `trending` 主链带坏。

## 结论

这次问题已经可以明确回答：

1. 前端之前不是在展示后端完整结果
   - 是压缩版 + 投影版
2. “分析浅”不只是推理 LLM 不行
   - 主因是：
     - 泛吐槽 query 被 fast 缩窄
     - 旧 cache 绕过新规则
     - 前端先展示英文原贴而不是中文判断
3. 现在这条咖啡机 query 已经回到可验收状态
   - 已经有：
     - 中文 summary
     - 中文 pain_points
     - 中文帖子解读
     - 中文原话解释
     - 中文下一步动作

## 下一步

1. 让用户去小程序只验这轮真实页面结果。
2. 如果页面上仍是“英文压过中文”，继续收前端投影，不回头动算法。
3. 如果页面价值已经对了，再继续压 generic 帖子的排序纯度。
