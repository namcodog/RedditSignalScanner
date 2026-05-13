# Phase 453 - live 数据噪音治理第一轮硬收口（PayPal）

## 发现了什么？

- `Full A` 漂移的第一源头不是前端，而是 live 数据入口太宽：
  - 之前只保证“在支付赛道里”，没有保证“就在 PayPal 这道题里”
  - 同赛道但失焦的帖子会混进来，把 pain / opportunity / battlefield 一起带歪
- 第二个源头是 structured fallback 自己会补模板量：
  - 战场会补到 4 张，即使后两张已经开始泛化
  - 驱动力不足 3 条时会补 `驱动力 3` 这种占位词
- 这会导致两个直接后果：
  - live 数据变脏，PayPal 被 Stripe 泛噪音和通用支付讨论稀释
  - 即使首轮 `A_full`，结果也离你要的 `100 分` 有差距

## 是否需要修复？

- 需要，而且这轮已经把“数据噪音第一刀”打进去了。

## 精确修复方法？

### 1. 在分析入口加题眼过滤

- 更新：
  - `backend/app/services/analysis/analysis_engine.py`
- 新增：
  - `_build_query_focus_groups()`
  - `_apply_query_focus_filter()`
- 规则：
  - 对 PayPal 这类窄题，帖子必须命中品牌或命中至少两次题眼信号（手续费 / 冻结 / 回款拖延）
  - 先把泛支付帖挡在信号提取前面，避免污染后续 pain / opportunity

### 2. 收紧 structured fallback 的模板噪音

- 更新：
  - `backend/app/services/report/structured_report_fallback.py`
- 修复点：
  - 战场不再为了“凑够 4 张”继续补失焦条目
  - duplicate battlefield 会按社区归一化后去重
  - generic driver title / description 不再保留 `驱动力 3` 这类占位符
  - 缺 driver 时改为从 pain 反推业务化驱动力

### 3. 测试先行，锁住这次合同

- 更新：
  - `backend/tests/services/analysis/test_analysis_engine.py`
  - `backend/tests/services/report/test_structured_report_fallback.py`
- 新增回归：
  - PayPal 题眼过滤会保留真实回款拖延帖、踢掉泛工具噪音帖
  - battlefields 去重
  - drivers 不再退回占位词

### 4. 真实 live 复验

- 清理并预检：
  - `make test-e2e-live-report-cleanup-apply`
  - `make test-e2e-live-report-preflight`
- 真实 live：
  - `task_id = 08a4f531-3d98-4111-ad89-5939985e1bfe`
  - 首轮 `A_full`
  - 结果页：`http://127.0.0.1:3006/report/08a4f531-3d98-4111-ad89-5939985e1bfe`

## 验证

- `pytest backend/tests/services/analysis/test_analysis_engine.py -q -k 'query_focus_filter or translate_pain_signal or translate_opportunity_signal or build_source_examples'`
  - `7 passed`
- `pytest backend/tests/services/report/test_structured_report_fallback.py -q`
  - `15 passed`
- `python -m py_compile backend/app/services/analysis/analysis_engine.py`
- `python -m py_compile backend/app/services/report/structured_report_fallback.py`

## 当前收口效果

- PayPal live 样本量从之前的宽泛覆盖，收到了更聚焦的 `56 帖 / 50 评论`
- pain 已经回到题眼线上：
  - `钱显示收到了，但可用余额到账太慢`
  - `退款后手续费照扣，利润被一点点吃掉`
  - `PayPal交付后逆转扣款`
- opportunities 也稳定回到业务机会：
  - `多平台收款插件配置助手`
  - `国际收款账户开通助手`
- drivers 不再出现 `驱动力 3`
- battlefields 不再继续靠模板硬补失焦条目

## 还没到 100 分的地方

- `evidence_chain` 这层结构仍是空，需要继续补成“标题、证据、前端点击”完全同源
- markdown 正文仍有少量表达层毛边，这已经更像第二阶段：不是 live 数据噪音本身，而是 narrative/renderer 的锋利度问题

## 下一步系统性的计划是什么？

1. 把 `evidence_chain` 补成可点击、可对位、不卡前端的真合同。
2. 再做一轮 PayPal live 复验，确认这条链路不是一次性结果。
3. 把这套“题眼过滤 + fallback 去模板化”的规则写成 SOP，推广到其余标准卡。

## 这次执行的价值是什么？

- 这轮的价值不是“文案更顺了”，而是把 live 数据噪音第一次真正按硬门槛收住了。
- 现在 PayPal 这条 `Full A`，已经不再主要被泛支付帖子和模板兜底拖着走，而是开始围着你要的题眼在产出。
