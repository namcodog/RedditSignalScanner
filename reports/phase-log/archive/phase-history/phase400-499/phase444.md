# Phase 444 - 首页剩余 4 张卡 live 补齐，EDC 真阻塞修完

## 发现了什么？

- 这轮目标不是再证明“能出一两条 Full A”，而是把首页剩余 4 张标准卡全部跑完，拿到真实 live 结果。
- 先纠正一个结论：
  - 上一轮记录里把 `make test-e2e-live-report-preflight` 记成了“假告警”。
  - 这次重新串行执行 `make test-e2e-live-report-cleanup-apply && make test-e2e-live-report-preflight` 后，门禁是正常的。
  - 之前看到旧读数，是因为我把 cleanup 和 preflight 并行跑了，读数混在了一起，不是系统真故障。
- 真正卡人的只剩 EDC 这张卡，而且是两个真实问题叠在一起：
  1. `edc_everyday_carry_v1` 的社区白名单太泛，混入了 `r/Ultralight`、`r/CampingGear`、`r/BuyItForLife`、`r/onebag` 这类偏题社区，导致早期 run 会掉到 `topic_mismatch` 或样本稀释。
  2. EDC profile 明明声明 `preferred_days=730`，但补样逻辑把窗口硬截在 `180` 天，窄题补样深度不够。

## 是否需要修复？

- 需要，而且已经修了。
- 这次不是“先记债以后再说”，而是边跑边把最后一张卡的真阻塞打掉，再重新 live 验收。

## 精确修复方法

### 1. 收紧 EDC topic profile

- 文件：`backend/config/topic_profiles.yaml`
- 处理：
  - 保留 live 验证过的核心社区：
    - `r/EDC`
    - `r/Knife_Swap`
    - `r/EDCexchange`
    - `r/knifeclub`
    - `r/multitools`
    - `r/flashlight`
  - 删除泛主题噪音社区：
    - `r/Ultralight`
    - `r/CampingGear`
    - `r/BuyItForLife`
    - `r/onebag`
  - 开启 `require_context_for_fetch: true`

### 2. 修补样窗口，跟 profile 的窄题 lookback 对齐

- 文件：`backend/app/services/analysis/analysis_engine.py`
- 新增 `_resolve_topic_profile_backfill_window(preferred_days)`
- 新逻辑：
  - 默认仍是 `30 / 7`
  - `preferred_days > 30` 时，允许补样窗口按 profile 扩到最多 `365` 天
  - `> 90` 天时 slice 统一走 `30` 天
- 这样 EDC 这类窄题不再被硬卡在 `180` 天。

### 3. 补回归测试

- 文件：`backend/tests/services/analysis/test_topic_profiles.py`
  - 新增 EDC profile 回归测试，锁定：
    - `r/EDC`
    - `r/Knife_Swap`
    - `r/EDCexchange`
    - `require_context_for_fetch=True`
- 文件：`backend/tests/services/analysis/test_analysis_engine.py`
  - 新增 backfill window 回归测试，锁定：
    - `None -> (30, 7)`
    - `123 -> (123, 30)`
    - `730 -> (365, 30)`

## live 结果

### 本轮补齐的 4 张卡

- `cross_border_paypal_v1`
  - `task_id=e78134e1-a188-4524-bfc5-7a8b8dd2b1b3`
  - `accepted=true`
  - `report_tier=A_full`
  - `llm_used=true`
- `cross_border_cashflow_v1`
  - `task_id=a80d5ef9-0e37-4e40-a092-48739ca2d707`
  - `accepted=true`
  - `report_tier=A_full`
  - `llm_used=true`
- `home_cleaning_v1`
  - `task_id=7713f6e2-2f16-43f6-9d99-2d47c33971cf`
  - `accepted=true`
  - `report_tier=A_full`
  - `llm_used=true`
- `edc_everyday_carry_v1`
  - `task_id=6c181629-8139-410a-86eb-cdf441c9306a`
  - `analysis_id=e542031b-6468-468d-8053-5a9e0be4fde8`
  - `report_id=1ab50864-0ead-423d-9839-f63d5628d1a3`
  - `accepted=true`
  - `report_tier=A_full`
  - `llm_used=true`
  - `report_markdown` 已返回长版 narrative

### 当前总盘点

- 先前已完成：
  - `cross_border_payment_v1`
    - `task_id=f6bf027a-36d4-4669-a088-3e168e38efe3`
  - `saas_collaboration_v1`
    - `task_id=76e45d73-7d6b-46cf-8d34-1ab79125dbf4`
- 加上本轮 4 张，首页 6 张标准卡在“当前 narrative prompt 口径下”的真实 live 验收已经补齐到：
  - `6 / 6`

## 验证

- `cd backend && ../.venv/bin/pytest tests/services/analysis/test_topic_profiles.py -q`
  - `14 passed`
- `cd backend && ../.venv/bin/pytest tests/services/analysis/test_analysis_engine.py -q -k 'preferred_days or resolve_topic_profile_backfill_window'`
  - `2 passed`
- `make test-e2e-live-report-cleanup-apply && make test-e2e-live-report-preflight`
  - `ok=true`
- `backend/scripts/acceptance/run_live_report_acceptance.py ... edc_everyday_carry_v1`
  - `accepted=true`
  - `task_id=6c181629-8139-410a-86eb-cdf441c9306a`

## 下一步系统性的计划是什么？

1. 不再停留在 `6/6 跑通 1 次`，升级到重复稳定性：
   - 先做 `6 张卡 x 3 轮`
   - 再决定要不要升到 `5x` 门禁
2. 把这轮 EDC 修复收成正式矩阵验收入口，而不是靠手工一张张跑。
3. 对照 `reports/t1价值的报告.md` 继续做文本强度差距表，但暂时不碰主链结构。

## 这次执行的价值是什么？

- 这次把“还差 4 张”的 live 缺口彻底补完了。
- 更关键的是，最后一张 EDC 不是靠运气过线，而是把 profile 噪音和补样深度这两个真问题一起修掉后，再拿到真实 `A_full`。
- 到这一刻为止，可以严谨地说：
  - 首页 6 张标准卡在当前 narrative 口径下，已经全部完成真实 live Full A 验收。
