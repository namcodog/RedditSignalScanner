# Phase 359 - 报告链 market template 与 blacklist 合同收口

## 时间
- 2026-03-17

## 本轮目标
- 收掉 `report` 整组里剩下的 3 条残留红灯
- 把 market template、blacklist 过滤、report 测试环境隔离这三处继续钉成稳定合同

## 发现了什么
- `backend/app/services/community/blacklist_loader.py`
  之前只认 `global_blacklist`，但 `backend/config/community_blacklist.yaml` 真实在用的是 `blacklisted_communities`。
- `backend/app/services/report/market_workflow.py`
  之前 market mode 的 template 路径并没有真正打通：
  - 相对路径解析不稳
  - analysis fallback 在内部被 `QuoteResult` 旧签名打断
- `tests/services/report/` 里还存在全局设置串味：
  - 一个测试把 `enable_market_report` 打开后，后面的普通报告测试会被误带进 market mode。

## 这次做了什么
- blacklist 兼容键补齐：
  - `backend/app/services/community/blacklist_loader.py`
  - 现在同时支持：
    - `global_blacklist`
    - `blacklisted_communities`
- market template 真正打通：
  - `backend/app/services/report/market_workflow.py`
  - `backend/app/services/report/report_service.py`
  - `backend/app/services/report/market_report.py`
  - 现在 market mode 会优先走 analysis-based template fallback，路径解析也和当前仓库结构对齐。
- report 测试环境隔离：
  - 新增 `backend/tests/services/report/conftest.py`
  - 用 autouse fixture 把：
    - `enable_market_report`
    - `report_mode`
    - `market_report_template_path`
    每条测试都拉回默认值，避免互相串味。
- 补测试门禁：
  - `backend/tests/services/community/test_blacklist_loader.py`
  - `backend/tests/services/report/test_market_workflow.py`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_report_service_market_template_config.py tests/services/report/test_report_p1_rules.py tests/services/report/test_market_workflow.py tests/services/community/test_blacklist_loader.py -q`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report -q`
- `cd backend && python -m py_compile app/services/community/blacklist_loader.py app/services/report/market_workflow.py app/services/report/report_service.py app/services/report/market_report.py tests/services/report/conftest.py tests/services/community/test_blacklist_loader.py tests/services/report/test_market_workflow.py`
- `SKIP_DB_RESET=1 make test-quality-gate`

## 结果
- `report` 整组现在：
  - `101 passed`
- 黑名单社区 `r/noise` 不再漏进 overview top communities
- market mode 现在真的能吃到：
  - override template
  - `gtm_summary`
- 普通报告测试不再被 market mode 全局开关串味

## 下一步
- 继续第三轮，优先专打剩余最重的几块：
  1. `facts / 报告模块` 剩余 wrapper / seam
  2. `数据采集模块` 剩余 side-effect / wrapper
  3. `语义 / 标签模块` 剩余 sync / import-export 接缝
