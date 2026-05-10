# phase1040

## 这轮达到的目的

V13 人工审核表已补齐到当前 published 全量 `448` 张，不再是之前的 `377` 张局部表。

## 当前状态变化

补跑了前段 offset `0-59`、尾部 offset `437-447`，并用 card_id 定向补齐当前 offset `60-70` 的 `11` 张漏项。完整审核表已生成：`reports/evals/hotpost_v13_shadow_human_review_sheet_full.csv / .xlsx`。

## 还没完成什么

线上卡还没有替换；完整表需要用户人工审核或改稿后，再生成最终 apply plan。

## 下一步做什么

用户只改完整 `.xlsx` 的审核列；改完后导入 CSV，生成 human-approved plan，并重新跑质量检查后再替换线上。
