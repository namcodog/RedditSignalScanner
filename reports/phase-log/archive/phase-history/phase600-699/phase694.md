# phase694

## 本轮完成
- 按 `signal-ops` 和 `breakdown-ops` 跑完了一轮真实运营，不再停留在 dry-run。
- 重新执行 `daily_collect`，成功补回新候选：
  - `ai-automation = 8`
  - `ecommerce-sellers = 8`
  - `business-growth-ops = 8`
- 新增并发布 4 张 `signal` 卡：
  - `card-cand-ai-automation-1sestcy-validate`
  - `card-cand-ai-automation-1sfnauw-validate`
  - `card-cand-business-growth-ops-1sd2za0-validate`
  - `card-cand-business-growth-ops-1sf9732-validate`
- 对这 4 张草稿做了人工收稿，重点清掉：
  - Reddit 转述腔
  - 论坛原话直抄
  - 后台/工程黑话
  - 句子拗口不顺
- `breakdown` 工作流也已真实跑完：
  - `materialize = 0`
  - `overlap = 0`
- 清理了遗留坏草稿和伪信号候选：
  - 删除 `draft-group-ai-automation-94bfe667d1`
  - 删除 `cand-ai-automation-1sas9s3`

## 结果
- `published: 50 -> 54`
- `drafts: 1 -> 0`
- `candidates: 24 -> 23`
- 当前没有待审草稿堆积，队列已清干净。

## 运营判断
- 这轮补卡不是硬凑数量，而是只发了方向和读感都过线的卡。
- 本轮新增 4 张里，方向最稳的是：
  - 监管环境下 AI 接入权限收窄
  - 安全模型邀请制发布边界
  - AI SEO 的合规/品牌风险
  - 网红投放从“找谁”转向“该不该自己做”
- `breakdown` 当前没有新 suggestion 成熟到值得 materialize，这个结论是正常的，不是工作流坏了。

## 当前状态
- hotpost 主链已进入稳态运营：
  - 能 collect
  - 能 seed / review / publish signal
  - 能 materialize / overlap 审查 breakdown
  - 队列里没有遗留坏 draft
