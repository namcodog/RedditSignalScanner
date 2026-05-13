# phase1132 - Brand R16 文本护栏与 sidecar 接入

## 这轮达到的目的

Brand system evidence 不再只能用 `verified`；`accepted` 品牌也可以进入系统证据层，但每条 mention 必须先过文本匹配护栏。

## 当前状态变化

- 新增配置化 `brand_match_guard`，`accepted` 命中会过滤普通短语误伤；`Can Do` 已从系统证据报告移除。
- `brand-system-evidence-2026-05-13` 当前为 `brand_count=117 / mention_count=976 / interest_tag_count=9 / community_count=60`。
- `brand-ops-sidecar` 已带上 `system_evidence_summary`，今日为 `system_evidence_brands=117`。
- `brand_ops_sidecar.py` 已拆短到 `198` 行，新增输出模块承接 markdown。

## 还没完成什么

品牌证据还没接入社区推荐解释正文，也没写入语义库、小程序快照或 Gold DB。

## 下一步

把安全品牌证据接入社区推荐解释和 Hotpost 后续上下文，不做前端品牌页。
