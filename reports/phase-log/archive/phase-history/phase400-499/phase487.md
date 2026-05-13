# Phase 487 - live 矩阵噪音收口（重复/嵌套标题根治）

## 时间
- 2026-03-26

## 目标
- 不再停留在“跑通一次”，而是把 live 矩阵里可复现的低质量噪音彻底收口。
- 重点修复：
  - pain 标题重复
  - opportunity 标题 `围绕「围绕` 嵌套
  - 执行会话长期堆积导致的运行告警干扰

## 执行内容

### 1) 运行层清理
- 清理遗留交互 shell（历史 `zsh -il`），减少会话占用。
- 使用 `manage_live_runtime.py` 统一停启 live runtime，确保单实例干净现场。

### 2) 发现并确认根因
- 新矩阵初跑：
  - `reports/local-acceptance/warzone_live_matrix_final_1774499117.json`
  - `A_full=1 / B_trimmed=3 / C_scouting=4 / errors=0`
- hard-gate 失败根因聚焦为结构噪音（不是随机漂移）：
  - `Tools_EDC` 出现重复 pain
  - `Tools_EDC` 出现 nested opportunity：`围绕「围绕...」`
  - `Frugal_Living` 仍有重复 pain

### 3) 代码级修复（report 结构合同层）
- 文件：`backend/app/services/report/structured_report_fallback.py`
- 新增并接入三类收口能力：
  - `linked_pain` 锚点归一（去壳）：把 `围绕「...」反复出现的关键麻烦` 还原为核心 pain anchor。
  - opportunity scaffold 标题去嵌套：消除 `围绕「围绕...」`。
  - pain/opportunity 标题确定性去重：重复时自动打场景后缀，避免同轮重复卡片。
- 同时修复 opportunity 组合链中重复标题回退逻辑，避免再次手工拼出 nested 标题。

### 4) 测试与验证
- 回归：
  - `pytest tests/services/report/test_structured_report_fallback.py -q` -> `32 passed`
  - `pytest tests/scripts/acceptance/test_validate_warzone_live_matrix.py -q` -> `4 passed`
- 新增定向测试（已通过）：
  - fallback pain 重复标题去重
  - enforce contract 下 nested opportunity 标题消除

### 5) live 复验（重启 runtime 后）
- 关键点：重启 runtime 后再跑，确保新代码实际生效（Python 服务不热更新）。
- 新矩阵：
  - `reports/local-acceptance/warzone_live_matrix_final_1774502165.json`
  - `A_full=2 / B_trimmed=3 / C_scouting=3 / errors=0`
- hard-gate：
  - baseline gate（`--min-a-full 1 --max-c-scouting 4`）通过，`issues=[]`
  - strict gate（`--min-a-full 3 --max-c-scouting 2`）未过，仅剩全局阈值问题：
    - `A_full count 2 < required 3`
    - `C_scouting count 3 > allowed 2`

## 四问回顾
1. 发现了什么？
- 当前主问题不是“系统随机漂移”，而是“结构噪音可复现”：重复 pain + nested opportunity。

2. 是否需要修复？
- 必须修，这类噪音直接破坏 Full A 可读性与前后端一致性。

3. 精确修复方法？
- 在 canonical report 合同层做统一归一、去嵌套、去重，避免下游再靠页面兜底。

4. 下一步系统性计划？
- 继续针对严格门槛推进（`A_full>=3, C<=2`）：
  - 优先打 `C_scouting` 的样本深度与 evidence 充足度。
  - 再跑 8 领域矩阵并用 hard-gate 封板。

5. 这次执行价值？
- 把“文本噪音”从随机症状变成可测试、可门禁、可复验的系统问题，稳定性提升有硬证据（baseline gate 通过，issues 清零）。
