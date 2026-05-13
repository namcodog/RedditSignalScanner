# Phase 776

## 时间

- 2026-04-12

## 本轮目标

- 保持 `signal v6` 作为当前 `1.0` 标准不动
- 给 repo 内 `signal` 生成链补一条 `Gemini CLI / gemini-3.1-pro-preview` 影子验证入口
- 只做 shadow run，不切正式发布主链

## 执行结果

- 已新增 `GeminiCLIChatClient`
  - `backend/app/services/llm/clients/gemini_cli_client.py`
- 已新增 `signal` shadow service
  - `backend/app/services/hotpost/signal_cli_shadow.py`
- 已新增独立脚本入口
  - `backend/scripts/hotpost/run_signal_cli_shadow.py`
- 已补最小测试：
  - CLI JSON envelope 解析
  - CLI 非零退出报错
  - shadow 候选只保留 `lane=signal`
  - shadow 生成时确实走 `GeminiCLIChatClient`
- 已完成一条真实 smoke：
  - 先跑 `review_cards.py queue --type validate --limit 6`
  - 再对 `cand-business-growth-ops-1sivq3t` 执行 `run_signal_cli_shadow.py`
  - `generated_count=1`

## 关键判断

- 当前 `signal` 的正确节奏仍然是：
  - `v6` 做生产标准
  - `Gemini CLI` 先做 shadow backend
- 这条 CLI 线现在已经技术可用，但还没有证据表明它能替代当前 API 线 `v6 champion`。
- 因此这轮完成的是“接通影子链”，不是“正式切换生产”。

## 涉及文件

- `backend/app/services/llm/clients/gemini_cli_client.py`
- `backend/app/services/hotpost/signal_cli_shadow.py`
- `backend/scripts/hotpost/run_signal_cli_shadow.py`
- `backend/tests/services/llm/test_llm_clients.py`
- `backend/tests/services/hotpost/test_signal_cli_shadow.py`

## 验证

- `python3 -m py_compile backend/app/services/llm/clients/gemini_cli_client.py backend/app/services/hotpost/signal_cli_shadow.py backend/scripts/hotpost/run_signal_cli_shadow.py`
- `pytest backend/tests/services/llm/test_llm_clients.py backend/tests/services/hotpost/test_signal_cli_shadow.py -q --tb=short`
  - `8 passed`
- `cd backend && python scripts/hotpost/review_cards.py queue --type validate --limit 6`
- `cd backend && python scripts/hotpost/run_signal_cli_shadow.py --snapshot-id queue-20260412062551-c751e9d3 --candidate-id cand-business-growth-ops-1sivq3t --json`

## 下一步

- 用同一批 `signal` 候选继续跑 shadow，对比：
  - 当前 API `v6`
  - Gemini CLI `v6`
- 对比重点不是字面像不像，而是：
  - lane 是否漂
  - banned 是否回潮
  - 判断迁移是否写平
- 在 CLI 线没有追平前，不切生产。
