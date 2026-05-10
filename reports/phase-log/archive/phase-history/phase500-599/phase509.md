# Phase 509 - Family 证据纯度收口

## 本轮目标
- 先把 `Family_Parenting` 这条 open-question live 里最脏的问题收掉：
  - 不再混入 `r/Entrepreneur`
  - 不再混入 `r/ProductManagement`
  - 不允许错赛道证据把结果“抬”成假 `A_full`

## 这次做了什么
- 在 `backend/app/services/report/structured_report_fallback.py` 增加了两层过滤：
  - warzone 过滤
  - source 社区白名单过滤
- 白名单来源统一改成这轮 analysis 已确认的社区池：
  - `sources.communities`
  - `sources.communities_detail`
- 把这些过滤补到了两个层级：
  - `build_structured_report_fallback(...)`
  - `enforce_structured_report_contract(...)`
- 过滤范围覆盖：
  - `target_communities`
  - `evidence_chain`
  - `sample_posts_db`
  - `source_examples`

## 新增/更新测试
- `backend/tests/services/report/test_structured_report_fallback.py`
  - 新增 `Family` cross-warzone 合同测试
  - 新增 `sample_posts_db/source_examples` 只能信本轮 source 社区池的测试

## 验证结果
- `cd backend && SKIP_DB_RESET=1 pytest tests/services/report/test_structured_report_fallback.py -q`
  - `35 passed`
- `make live-runtime-restart`
  - backend / analysis-live / bulk-live 全部 ready

## 定向 live 复验结果
- 复验题目：
  - `Family_Parenting`
  - 描述：`我们是新手父母，夜奶和睡眠记录总断档，家人换手照护时经常漏项，想知道有没有真实可行的产品切口。`
- 复验结论：
  - 证据纯度问题已收住
  - 但 live 结果从之前的“假 A”变成了“诚实的 C”
- 具体表现：
  - `target_communities` 已回到 parenting 池：
    - `r/NewParents`
    - `r/daddit`
    - `r/parenting`
    - `r/beyondthebump`
  - 不再出现：
    - `r/Entrepreneur`
    - `r/ProductManagement`
  - 但结果停在：
    - `report_tier = C_scouting`
    - `analysis_blocked = insufficient_samples`
    - `reddit_links = []`
    - `warmup upgrade timeout`

## 这次的真实价值
- 不是“又没过”，而是把系统从“靠错证据撑出 A”推进成了“证据不够就老实留在 C”。
- 这意味着主链更稳了，也更诚实了。
- 现在剩下的问题已经从“输出层污染”收敛成了一个更明确的 coverage 问题：
  - `Family_Parenting` 的 live 数据覆盖和 warmup/backfill 提升链还不够强

## 下一步
- 不再继续打 prompt
- 直接修 `Family_Parenting` 的 coverage 提升链：
  - 为什么补量后依然拿不到 clickable Reddit links
  - 为什么 warmup 180 秒后仍无法从 `C_scouting` 升到 `A_full`
