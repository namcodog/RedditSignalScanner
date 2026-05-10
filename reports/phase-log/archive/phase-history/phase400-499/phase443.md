# Phase 443 - 两条真实 Full A live 报告验收

## 发现了什么

### 1. `Phase 442` 后最关键的缺口已经不是 prompt，而是 live 实物

- 上一轮只完成了：
  - narrative prompt 第一刀收紧
  - prompt 级测试通过
- 但还没有真正用实时链路证明：
  - `A_full` 真的能稳定跑出来
  - `llm_used=true` 的长版 narrative 报告真的落地了
  - 真实标准题在现网口径下没有再掉级

### 2. live 前置门禁有一个“假卡死”

- `cleanup_live_acceptance_backlog.py --apply` 已经把 stale backlog 清到 0。
- 但 `make test-e2e-live-report-preflight` 仍然打印旧的 `205 / 205` 积压数，和数据库真实状态冲突。
- 直接跑同一个后端脚本：
  - `backend/scripts/acceptance/live_report_preflight_gate.py`
  - 读到的是真实状态：
    - `task_outbox_pending=0`
    - `queued_not_enqueued=0`
- 说明这次卡住的不是库里还有积压，而是 `make` 这一层的前置门禁包装存在读数异常。

## 是否需要修复

- 需要，但这次先不在主链上乱动。
- 当前更重要的是先拿到真实 `A_full` 实报，证明 `Phase 442` 的 narrative 收口已经在 live 生效。
- `make` 这层 preflight 异常需要单独列成后续修复项，不该继续阻断这轮验收。

## 精确执行方法

### 1. 直接绕过异常的 make 前置包装

- 保留：
  - backlog cleanup
  - 同一套 backend preflight script
- 绕过：
  - `make test-e2e-live-report-preflight`

### 2. 手动按 live 验收真实步骤执行

- 启 backend / frontend
- seed 测试账号
- 起隔离 analysis worker
- 起隔离 bulk worker
- 用 `run_live_report_acceptance.py` 分别跑两条标准题：
  - `cross_border_payment_v1`
  - `saas_collaboration_v1`

## 验证结果

### 样本 1：跨境回款 / 手续费

- `topic_profile_id`: `cross_border_payment_v1`
- `task_id`: `f6bf027a-36d4-4669-a088-3e168e38efe3`
- 结果：
  - `status=completed`
  - `report_tier=A_full`
  - `llm_used=true`
  - `decision_cards=4`
  - `battlefields=4`
  - `pain_points=3`
  - `drivers=3`
  - `opportunities=2`
- 关键产物：
  - 顶部机会：`多平台回款加速器`
  - 核心战场：`战场：r/stripe`
  - 已返回长版 narrative markdown

### 样本 2：SaaS 协作

- `topic_profile_id`: `saas_collaboration_v1`
- `task_id`: `76e45d73-7d6b-46cf-8d34-1ab79125dbf4`
- 结果：
  - `status=completed`
  - `report_tier=A_full`
  - `llm_used=true`
  - `decision_cards=4`
  - `battlefields=4`
  - `pain_points=4`
  - `drivers=3`
  - `opportunities=2`
- 关键产物：
  - 顶部机会：`远程onboarding自动化工具`
  - 核心战场：`战场：r/entrepreneur`
  - 已返回长版 narrative markdown

## 四问统一反馈

### 1）发现了什么？

- `Phase 442` 的 prompt 第一刀已经在 live 真实生效，不是“只在测试里变好看”。
- 两条标准题都首轮打出 `A_full`，而且都是 `llm_used=true` 的 narrative 长报告。
- 当前真正的阻塞不是 live 主链，而是 `make test-e2e-live-report-preflight` 这一层存在旧读数异常。

### 2）是否需要修复？

- 需要。
- 但这次优先级应该拆开看：
  - P0 已完成：真实 Full A 报告产出
  - P1 待补：`make` 层 preflight 读数异常

### 3）精确修复方法

- 下一轮单独修 `make test-e2e-live-report-preflight`：
  - 对齐它和 `live_report_preflight_gate.py` 的真实读数
  - 查清是 shell 包装、变量展开还是旧输出残留
- narrative 主链本身暂时不继续动结构，先把 6 张标准卡剩余 4 条 live 抽检补完。

### 4）下一步系统性的计划是什么？

1. 补完剩余 4 张标准卡的 live narrative 抽检。
2. 对照 `reports/t1价值的报告.md` 做章节/证据密度差距表。
3. 如果还偏机器味，只做 prompt 第二刀，不动主链结构。
4. 单独修 live preflight 的 make 包装异常。

### 5）这次执行的价值是什么？

- 这次把“Full A 长报告第一刀”从提示词层，真正推进到了 live 交付层。
- 现在已经不是“理论上能出 narrative”，而是已经拿到了两条真实、可打开、可复核的 `A_full` 报告。
