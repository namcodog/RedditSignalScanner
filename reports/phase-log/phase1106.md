# phase1106

日期：2026-05-08

## 这轮达到的目的

把社区回流判断从逐个发布验证，推进到 R11.5 价值评分算法。

## 当前状态变化

- 新增配置驱动评分规则：`backend/config/community_value_scoring.json`。
- R11 dry-run 行新增 `value_assessment`，输出 `score / stage / positive_signals / risks`。
- Markdown 报告新增 `Value Stage / Score`，用于人工只看高价值少数社区。
- 当前 `r/CursorAI` 为 `validated / score=56`，不是 `pool_candidate`。

## 还没完成什么

算法现在只做只读 dry-run，不写 DB，也不自动入池。下一步只在出现 `pool_candidate` 且用户确认后，进入 R12 Dev 写入。
