# phase1027 - Hotpost V13 运营 shadow 样本包

## 这轮达到的目的

V12/V13 组合口径已用于非旧实验样本 shadow 产出：`deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro`，只生成审核包，不写 drafts / published / release。

## 当前状态变化

已生成 `reports/evals/hotpost_v13_shadow_new_samples_review_packet.md` 和对应 JSON。6 张样本全部生成成功；自动检查发现 1 个 title 长度残留。同步补了 `Claude Code / Token` 与中文粘连检测、生产规则提示，以及 shadow 单卡 240s 超时保护。

## 还没完成什么

第二次完整重跑在首张 deepseek semantic 请求超过 2 分钟无返回后中断；不是 key 失效，更像外部模型长时间挂起。当前审核包可供人工看质感，但不是“0 残留”的最终批量回归。

## 下一步做什么

先让用户审核这份 shadow 包。若质感通过，再跑带超时保护的新一轮 6-12 张样本；连续两轮通过后，再讨论是否重跑历史已发布卡。
