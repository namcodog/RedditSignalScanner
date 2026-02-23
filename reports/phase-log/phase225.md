# Phase 225 - Codex Skill 设计：`rsc-workflow`（日常“保姆 + 护栏”）

日期：2026-02-04

## 发现了什么？
- 这个仓库已经把“怎么跑系统”收口得很强：`Makefile` 是唯一入口，黄金路径脚本也有（`scripts/dev_golden_path.sh`）。
- 同时约束也很多：三库制（Dev/Test/金库只读）、大量环境开关、固定的 MCP 工具链顺序、以及“做完必须写 phase-log”。
- 真实痛点不是缺功能，而是**步骤碎 + 口径多 + 容易漏证据/踩坑**（尤其是 DB 误写、忘记跑测试、忘记补记录）。

## 是否需要修复？
- 不算 bug，但**非常值得做**：用一个 Skill 把“口径 + 安全护栏 + 证据产出”半自动化，能明显降低返工与误操作风险。

## 精确修复方法（Skill 方案）
### 1) Skill 的定位（不替代 Makefile）
做一个“指挥官/保姆”型 Skill：**负责把人带着走**（该检查的先检查、该跑的按顺序跑、该记录的别漏），真正执行仍然交给 `make ...` 和现有脚本。

### 2) 建议的主 Skill：`rsc-workflow`
**何时触发（典型话术）**
- “起服务/跑黄金路径/本地验收怎么跑？”
- “后端/前端测试怎么跑？只跑核心行不行？”
- “Celery/Redis/端口/健康检查出问题了，怎么排？”
- “我要生成 T1 报告 / 跑 KAG 验收 / 跑数据流水线。”
- “我要改代码，但怕踩金库/流程。”

**Skill 的固定流程（默认走安全路径）**
1. **进度基线**：先读 `reports/phase-log/` 最新条目（按更新时间）。
2. **目标澄清**：把用户要做的事归类：开发/排障/验收/跑数据/写报告。
3. **前置检查（护栏）**：
   - 当前目录是否在仓库根（避免跑错）。
   - DB 口径：默认 Dev/Test；若出现 `reddit_signal_scanner`（金库）相关意图，必须二次确认并检查 `ALLOW_GOLD_DB=1`。
   - MCP 是否就绪（可用 `scripts/verify-mcp-tools.sh`）。
   - 端口/服务健康检查（可用 Makefile 目标或 `scripts/check-services.sh`）。
4. **定位与决策**：
   - Serena 先定位代码/入口（别上来就改）。
   - Sequential Thinking 把“根因/方案/影响面”想清楚。
   - 必要时 Exa-Code 补最佳实践（少走弯路）。
5. **测试优先**：先补/改测试，再实现；跑 `make test-backend` / `make test-frontend` / 目标更小的 test target。
6. **收尾产物**：自动提醒并产出 phase-log 模板，确保有“命令 + 关键输出/文件路径”证据。

**强制安全规则（写在 Skill 里当硬护栏）**
- 不直接跑散落的 python 脚本：优先用 `make ...`（仓库已经明确了这是唯一口径）。
- 所有会写库的动作：默认只写 Dev/Test；碰到金库必须硬拦截 + 明示风险。
- 任何 MCP 安装/配置变更：立刻跑自检；超过 12 秒没结果就停并记录到 `reports/`。

### 3) SKILL.md 骨架（建议）
用最小上下文 + 渐进式加载（progressive disclosure）：
- SKILL.md：只放“触发条件 + 固定流程 + 护栏 + 常用命令清单 + 产出模板入口”
- references/：放仓库关键文档索引（README、质量门禁、三库制、端到端手册等）
- scripts/（可选）：放确定性强、重复多的脚本（如：生成 phase-log 骨架、预检 DB/端口）

## 验收标准（Skill 算成功的样子）
- 新人只看 Skill 就能跑通：启动 → 健康检查 → 测试 → 本地验收。
- 每次执行都能讲清楚：用的哪个库、跑了哪些命令、证据文件在哪。
- 不会误写金库：默认拦截，必须显式开关 + 二次确认才允许继续。

## 下一步系统性计划
1. 先落地一个最小可用版本：只做 `rsc-workflow`（覆盖 80% 日常）。
2. 再按需要拆两个小 Skill：
   - `rsc-phase-log`：自动生成 `phase{N}.md` 骨架并提醒填空。
   - `rsc-safe-run`：所有命令执行前做 DB/端口/ENV 预检，专治“手滑”。
3. 选 2~3 个真实任务做演练：起黄金路径、跑后端测试、跑 KAG 验收，验证 Skill 指南是否足够清晰。

## 这次执行的价值
- 把“流程口径 + 安全护栏 + 证据产出”变成可复用的套路，减少漏步骤、踩坑和返工成本。

---

## 补充：用 Serena 直接“检索项目环节”的最快路径（建议写进 Skill）

### Serena 现成的“环节总览”在哪？
- **实际工作流口径**：`.serena/memories/workflow_actual.md`（6 步主链路：社区 → 抓取 → 标注 → 分析 → 报告 → 门禁）
- **架构/模块地图**：`.serena/memories/architecture.md`
- **常用命令清单**：`.serena/memories/commands_and_tools.md`
- **闭环逐环节证据**：`reports/system-workflow-closure-validation-report.md`（每一环对应关键文件/数据流）

### Skill 怎么用这些材料？
建议给 `rsc-workflow` 加一个固定子流程：**“环节地图 / workflow-map”**  
用户只要说“梳理流程/闭环/环节分析/对齐流程图”，Skill 就先：
1) 读 `workflow_actual.md` 把环节列出来  
2) 读闭环验证报告把每个环节的“关键文件/表/定时任务/API”贴成一张表  
3) 再用 Serena 的符号/引用检索去补齐“谁调用谁”（避免纯猜）

### 额外建议（小投入大收益）
- 把 `.serena/project.yml` 的 `languages` 补上 `typescript`，否则前端跳转/找引用会打折扣。
