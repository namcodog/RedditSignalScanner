# phase681 - breakdown skill optimization closure

## 本阶段完成
- 完成 `breakdown judge v2` 校准与全量评估。
- 新增 `breakdown suggestion coherence gate`，在 suggestion 层拦截强拼候选。
- 新增 `breakdown overlap audit v1`，开始识别已发布 write 卡的主题撞车与冗余。
- 修复 `materialize_breakdown_drafts.py` 的脚本导入路径，使 CLI 可直接从仓库根执行。
- 对齐并修复 breakdown 相关测试样本，使测试口径和新门槛一致。

## 关键结果
- `breakdown_judge_calibration_v2`：整体匹配率提升到 `88.89%`。
- `breakdown_judge_full_eval_v2`：`18` 条样本中 `16 pass / 2 fail`。
- `breakdown_suggestion_gate_audit_v1`：已知 `2` 条 suggestion fail case 全部被 gate 拦截，`blocked_fail_count = 2`，`blocked_pass_count = 0`。
- `materialize_breakdown_drafts.py` 当前真实运行结果：`materialized = 0`，说明 live suggestion 池中没有再漏出不合格拆解草稿。
- breakdown 新增回归测试：`8 passed`。

## 当前系统边界
- `breakdown judge v2` 负责单卡是否成立。
- `breakdown suggestion coherence gate` 负责 suggestion 阶段的强拼拦截。
- `breakdown overlap audit v1` 负责卡组冗余预警，但仍是第一版，不等于最终去重裁决器。
- 自动化仍然只到 `write draft`，不自动 publish。

## 收口判断
- `breakdown V2 + breakdown skill optimization` 这一轮已形成可运行闭环。
- 当前小程序收尾版本已具备：
  - 稳定 signal 生产
  - 可控 breakdown 生产
  - breakdown 内容质量 gate
  - breakdown suggestion 强拼拦截
  - 初版 overlap 冗余审计
