# phase1039

## 这轮达到的目的

V13 shadow 结果已进入人工审核表阶段；现在用户可以用表格改稿，不需要直接改 `.md` 或 `.json`。

## 当前状态变化

新增审核工具 `backend/scripts/hotpost/build_v13_shadow_review_sheet.py`，支持从 shadow plan 导出审核 CSV，并从审核 CSV 生成可应用的 human-approved plan。首版审核表已生成：`reports/evals/hotpost_v13_shadow_human_review_sheet.csv / .xlsx`，共 `377` 张。

## 还没完成什么

线上卡还没有替换；需要用户在审核表里确认或修改后，再生成最终 apply plan。

## 下一步做什么

用户只改 `review_status / review_notes / edit_title / edit_summary_line / edit_audience / edit_why_now`；改完后导入生成最终 plan，并重新跑 V11/V12/V13 质量检查。
