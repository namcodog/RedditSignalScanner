# 2026-05-13 Root GitHub Governance Plan

## 目标

把当前根仓剩余 dirty 从“混在一起”治理成可解释、可验证、可分批提交的主系统改动；不再向已全绿的 PR #3 继续塞新范围。

## 当前基线

- 冻结锚点：PR #3 在 `9c540a8` 已全绿。
- 当前工作分支：`chore/root-github-governance-20260513`。
- Wave 1 提交：`d631d5a feat(backend): add brand intelligence registry services`。
- 小程序边界：`hotpost-mini/hotpost-mini-app` 仍只显示既有派生产物脏状态，本轮不碰。
- 剩余 root dirty 粗分：
  - Brand Intelligence R15 主系统功能：后端服务、API、模型、迁移、脚本、配置、测试、计划、报告。
  - Hotpost 社区探索编排：orchestrator、脚本、测试、SOP、社区治理报告。
  - 运营与 phase-log：05-12 / 05-13 ops-log、phase1117-1130、四入口更新。
  - 派生产物 / 大报告：brand digest JSON、trend audit、hot lane audit 等。

## 提交波次

### Wave 1: Brand Intelligence 主系统最小闭环

状态：已完成本地提交 `d631d5a`。

范围：
- `backend/app/services/brand_intelligence/`
- `backend/scripts/brand_intelligence/`
- `backend/app/api/v1/endpoints/brand_intelligence.py`
- `backend/app/models/brand_registry.py`
- `backend/config/brand_*.json`
- `backend/tests/services/brand_intelligence/`
- `backend/tests/api/test_brand_registry_api_contract.py`
- `backend/tests/models/test_brand_registry_models.py`
- brand 相关迁移、Makefile brand targets、R15 plan/spec。

验证：
- brand intelligence 目标测试。
- brand registry API/model 测试。
- `black --check` / `isort --check-only` 覆盖提交文件。
- `make boundary-status`。

提交策略：
- 不提交大型 digest JSON，除非测试或文档明确依赖。
- 报告优先只提交摘要 `.md` 和必要小型 `.json`。

### Wave 2: Hotpost 社区探索编排

范围：
- `backend/app/services/hotpost/community_exploration_orchestrator.py`
- `backend/scripts/hotpost/run_community_exploration_loop.py`
- `backend/tests/services/hotpost/test_community_exploration_orchestrator.py`
- 社区探索 SOP / plan。
- Makefile hotpost exploration targets。

验证：
- community exploration 目标测试。
- dry-run 或脚本 `--help` 级验证。
- `make boundary-status`。

提交策略：
- 不把小程序 cloudfunction 派生产物混入。
- 社区探索报告按“必要追溯摘要优先”提交。

### Wave 3: 项目记录与 phase-log 收口

范围：
- `reports/phase-log/CURRENT_STATUS.md`
- `reports/phase-log/OPEN_ITEMS.md`
- `reports/phase-log/MILESTONES.md`
- `reports/phase-log/INDEX.md`
- `reports/phase-log/phase1117.md` 到 `phase1130.md`
- `reports/ops-log/2026-05-12.md`
- `reports/ops-log/2026-05-13.md`
- `reports/ops-log/INDEX.md`

验证：
- 手工检查四入口能回答当前状态、未完成事项、下一步、追溯入口。
- `git diff --check`。

提交策略：
- 只在 Wave 1 / Wave 2 代码事实确定后提交记录，避免日志先于代码落 GitHub。

### Wave 4: 派生产物与大报告筛选

范围：
- `reports/brand-intelligence/*.json/csv`
- `reports/community-governance/*.json/md`
- `reports/evals/*.json/md`

验证：
- 文件是否被 phase-log / docs / tests 引用。
- 文件大小和复现成本。

提交策略：
- 默认不提交大 JSON / CSV。
- 需要追溯时只提交摘要 `.md` 或小型决策 `.json`。
- 若大产物是外部验收证据，单独提交并在 commit message 写明原因。

## 红线

- 不使用 `git add .`。
- 不提交 `hotpost-mini/` 子仓内容。
- 不把 Wave 1 和 Wave 2 混成一个提交。
- 不为清仓删除未审计文件。
- 不把 PR #3 继续扩大范围；后续走新分支 / 新 PR 或 stacked PR。

## 当前下一步

1. 执行 Wave 2 详细审计：读取 Hotpost 社区探索 orchestrator、脚本、测试、Makefile hotpost hunk 和 SOP。
2. 跑 community exploration 目标测试或脚本级 dry-run/help 验证。
3. 输出 Wave 2 精确 stage 清单。
4. 只有验证通过后，才做 Wave 2 精确提交。
