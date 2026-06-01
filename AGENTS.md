# Repository Guidelines

## 行为准则：Karpathy 编码规则（最高频使用）

这组规则用于减少 LLM 常见编码错误。它默认偏谨慎；极简单任务可以用判断力压缩流程，但不能跳过事实核实和必要验证。

1. 先想清楚再写代码
   - 不允许做任何硬编码的执行。
   - 不做未经说明的假设；有假设必须明说。
   - 不隐藏困惑；不确定时先问，或先指出缺口。
   - 多种解释同时存在时，列出解释和取舍，不静默选一种。
   - 有更简单方案时必须说出来；当前方案不合理时要直接指出。

2. 简单优先
   - 只写解决当前问题的最小代码。默认不超过200行代码。
   - 不做未被要求的新功能。
   - 不为单次使用代码抽象。
   - 不增加未被要求的灵活性、配置化或扩展点。
   - 不为不可能或不该发生的场景写防御性错误处理。
   - 如果 200 行能被 50 行清楚解决，必须重写成更短版本。
   - 自检问题：资深工程师会不会认为这过度复杂？如果会，先简化。

3. 手术式改动
   - 只碰必须修改的内容。
   - 不顺手美化旁边代码、注释、格式。
   - 不重构没有坏掉的东西。
   - 匹配现有代码风格，即使你个人会用另一种写法。
   - 发现无关死代码时只指出，不删除。
   - 只删除本次改动制造出来的未使用 import / 变量 / 函数。
   - 每一行 diff 都必须能追溯到用户当前请求。

4. 目标导向执行
   - 先定义成功标准，再循环到验证通过。
   - “加校验”要落成“为非法输入写测试，再让测试通过”。
   - “修 bug”要落成“写出复现 bug 的测试，再让测试通过”。
   - “重构”要落成“改前改后测试都通过”。
   - 多步任务必须写短计划，格式是：步骤 -> 验证点。
   - “让它能用”这种弱标准不允许作为完成条件；必须拆成可检查的验收点。

这组规则是否生效，只看三个结果：diff 里的无关改动变少、因过度复杂导致的返工变少、澄清问题发生在实现前而不是出错后。

## 🧠 key-os 使用协议（强约束）

你当前在**别的项目仓库**里工作。`key-os` 是外部 OS，不是当前项目仓库的一部分，也不是你要维护的主仓库。

### 基本原则

- 先遵守当前项目自己的本地规则文件
- `key-os` 只作为外部个人 OS：提供记忆、读取路由、治理门禁、写回规则和收口检查；当前任务仍以本仓交付为主
- canonical root 固定为 `/Users/hujia/Library/CloudStorage/GoogleDrive-namcodog@gmail.com/我的云端硬盘/key-os`
- `/Users/hujia/key-os` 只允许作为快捷入口或兼容路径，不是正式真相源
- 当前执行模式是控制 agent 执行，`keyos` CLI 负责读取路由、写回门禁、收口和检查；`steward LLM` 默认关闭
- 当前项目的代码、文档、测试、交付物继续写在当前项目仓库
- 不在当前项目目录里再维护第二套长期记忆系统，也不要把外部运行时变成 `key-os` 的长期管理员

### 启动与读取

- 每次会话开始固定执行：`keyos status --json` -> `keyos check --json` -> `keyos read --json`。
- `keyos read --json` 返回的 `files` 是 key-os 初始化首跳，只代表跨项目连续性和推荐上下文，不替代本项目 phase-log 当前状态。
- 如果已知道目标，完成固定初始化后再按需使用：`keyos read rules --json`、`keyos read wiki --json`、`keyos read audit --json`、`keyos read project:<name> --json`、`keyos wiki query "<topic>" --json`。
- 默认窄读，只读 `keyos` 返回的 `files`；不把 `/Users/hujia`、home 根目录或 `key-os` 全库当默认 grep / glob 起点。
- 检索优先级：`keyos` CLI 命中文件 -> canonical root 下被显式点名的文件 -> 当前仓库限定目录。
- 涉及 memory / knowledge base / history / prior discussions / topic ideas 时，先走 `keyos read` 或 `keyos wiki query`，不要把普通文件系统搜索当成记忆检索。
- 扩展读取只补充跨项目规则、历史判断或项目连续性；涉及 RedditSignalScanner 当前进度时，仍必须回到 `reports/phase-log/` 四入口核实。

### 改前治理

- 修改任何文件前先运行：

```bash
KEYOS_ROOT="/Users/hujia/Library/CloudStorage/GoogleDrive-namcodog@gmail.com/我的云端硬盘/key-os" keyos steward prepare \
  --goal "<本次目标>" \
  --acceptance "<可验证验收点>" \
  --llm-provider disabled \
  --json
```

- 只有看到 `execution_discipline_v1.status=active` 才能继续。
- 如果 `prepare` 返回 block、`keyos check` 失败、或 JSON 不可判断，先停止并处理阻塞。

### 调用边界

- 研究 / 资料任务优先用 `keyos wiki query --json`、`keyos wiki ingest ... --json`。
- 写回 `key-os` 只能通过 CLI：`keyos inbox ...`、`keyos write ...`、`keyos steward ...`、`keyos wiki ...`、`keyos evolve --json`。
- 不要手改 `key-os` canonical 文件；尤其不要静默改 `00-core/*`、`01-memory/MEMORY.md`、`01-memory/ARCHIVE.md`。
- 任务完成后如果触发写回条件，运行 `keyos steward close ... --json`，再运行 `keyos check --json`。

### 真实任务回流

当本仓完成一个可验证的真实任务，并且满足下面任一条件时，必须把结果回流到 key-os，避免 key-os 的质量账本长期只有治理样本。

触发条件：
- 改变了下一次任务应该采用的判断。
- 产出可复用结论、失败教训或方法。
- 踩到下次容易重犯的坑。
- 完成一次真实工程 / 运营任务，例如产品、后端、前端、小程序、数据链、质量门禁、产卡、发布、补漏、真机排障或 release surface 修复，并已完成验证。

不满足以上条件的只读问答或微小检查，不强行写回。

收口命令：

```bash
KEYOS_ROOT="/Users/hujia/Library/CloudStorage/GoogleDrive-namcodog@gmail.com/我的云端硬盘/key-os" keyos steward close \
  --task-type "engineering|research|writing|governance" \
  --file "<本仓关键文件或报告>" \
  --result-quality "A|B|C" \
  --wrong-context "<这次纠正了什么误判，没有就写 none>" \
  --promotion-action "none" \
  --note "<一句话写清真实任务、验证结果和可复用经验>" \
  --llm-provider disabled \
  --json
```

close 约束：
- 颗粒度按工作 session，不按 commit。
- `--note` 用一句话写结论，不写过程流水。
- `--wrong-context` 非 `none` 时，`--promotion-action` 必须填具体动作。
- `task_type` 不要写成 `governance`，除非这次任务真的只是在维护 `key-os` 或本仓规则文件。真实产品 / 工程 / 运营任务优先用 `engineering`、`research` 或 `writing`，让 `task-quality-ledger.md` 出现非治理样本。

### 失败处理

- `keyos` 没有返回可解析 JSON、JSON 明确显示 failure、或结果无法判断当前状态时，先停止并立即执行 `keyos doctor --json`。
- `keyos check --json` 的纯 warning 不算硬失败，记录 warning 后继续当前任务。

### 明确禁止

- 不要直接手改 `daily / project / wiki` 文件，不要直接进入 `KEYOS_ROOT` 文件树找内容，不要把自己当成 `key-os` 仓库维护者。
- 你的职责是使用 `key-os`、读取 `key-os`、回填高价值结果给 `key-os`。
- 完整云端协议入口：`key-os/AGENTS.md`、`key-os/03-governance/AGENT_OS_PROTOCOL.md`、`key-os/03-governance/EXTERNAL_AGENT_PROMPT.md`。

### 关于仓库内 `mem/`

- `/Users/hujia/Desktop/RedditSignalScanner/mem/` 只作为历史资料层保留，可参考但不再作为 canonical memory；若与 `key-os` 返回结果冲突，以 `keyos` CLI 路由结果为准。

---

## 使用前提（User Rules）

### 入口与当前状态

- 对话规范：与产品经理沟通一律使用简洁、通俗、健谈的中文；工程术语要翻成小白也能明白的大白话。
- 启动读取顺序分四层：
  1. key-os 初始化层：固定完成 `keyos status --json` / `keyos check --json` / `keyos read --json`，只读取返回的 `files`，用于获得跨项目连续性和推荐首跳。
  2. 项目状态层：凡是涉及 RedditSignalScanner 当前进度、下一步、未完成事项，必须读取 `reports/phase-log/CURRENT_STATUS.md`、`OPEN_ITEMS.md`、`MILESTONES.md`、`INDEX.md`。
  3. 任务扩读层：按任务类型读取对应 SOP / reference / 代码文件；不要一开始全量读 docs。
  4. 背景资料层：根目录 README 和旧文档阅读指南只在需要理解历史背景或新人导览时读取，不作为当前状态真相源。
- key-os 负责跨项目连续性和个人 OS；phase-log 负责本项目当前状态。两者看起来不一致时，不静默合并；先说明冲突，再以可验证的最新项目产物为准。

### 主项目 / Hotpost / 小程序边界

- 根目录 `task_plan.md` 只用于当前日常运营；边界护栏、主项目复位、小程序功能计划分别写到 `docs/superpowers/plans/`，不要混写。
- `hotpost-mini/hotpost-mini-app` 是独立 git 小程序仓库；小程序提交必须在子仓内完成，主仓提交前必须运行 `make boundary-status`。
- 禁止在根仓用 `git add .` 混入小程序；根仓本地应通过 `.git/info/exclude` 忽略 `/hotpost-mini/`。
- `mini_snapshots` 和 `hotpost-mini/.../cloudfunctions/*/data` 是发布派生产物，只能由 `push_mini_snapshot.py` 写入，不手改。

### Git 收口 / 回滚门禁

- 用户要求“提交 / 收口 / 推送 / 记录状态”时，默认必须提交并 push 到远端；只有用户明确说“只本地提交”才可以不 push。
- 提交必须按主仓、小程序子仓、运营记录、派生产物分批 staging；禁止 `git add .`，禁止把小程序子仓改动混入主仓。
- 收口前必须记录本轮前后的 commit 锚点；可回滚证明优先使用这些 commit 通过 `git revert` 反向提交，禁止用 `git reset --hard` 或 force push 作为默认回滚方案。
- 最终状态必须用命令证明，不接受口头 clean：主仓和小程序子仓都要满足工作区空、暂存区空、stash 空、`HEAD == origin/main`、远端 `main` hash 等于本地 `HEAD`。
- 最终检查入口固定为 `make git-clean-status`；涉及小程序边界时仍必须同时跑 `make boundary-status`。

### 思考与反馈

- 不使用“你说得对、我认了、我没想好”这类敷衍或讨好式表达。
- 默认站在需求的对立面，用事实、边界、取舍来审视问题；不能为了迎合口头判断而偏移结论。
- 没有真实核实的方法、数据或验证链路，不能当作解决方案对外反馈。
- 如果一个需求存在多种解释，先把分歧和取舍说清楚；关键点不清楚时先指出，不把困惑藏进实现里。
- 重要任务收尾默认覆盖五件事：发现了什么、是否需要修复、精确修复方法、下一步计划、这次执行的价值。简单任务可以合并成短答。

### 实现边界

- Karpathy 规则是默认实现纪律；本段只补项目红线。
- 多步任务执行前必须写分步计划，并把任务翻译成可验证结果；每一行改动都必须能追溯到当前需求。
- 不写用来掩盖问题的模糊 fallback。显式业务合同里的 assist / rescue 可以存在，但必须可观测、可验证、不能吞掉错误。
- 新增逻辑优先拆到职责清楚的小文件；不在原文件上无边界叠代码。

### 工具与验证

- 代码定位优先用 `serena` MCP 或 `rg`；复杂根因判断可用顺序化思考。
- 外部资料、库用法、最佳实践必须用当前可用的官方文档或可靠来源验证；不要把不可用工具写成硬阻塞。
- UI / 端到端问题才需要浏览器、Playwright 或 Chrome DevTools 类工具；非 UI / 非 E2E 任务不强制使用浏览器。
- 任何 MCP 安装或配置后需立即自检；超过 12 秒仍无法确认可用，就停止排查并把阻塞记录到 `reports/`。
- 涉及代码行为变更时测试优先：先补或更新测试，再改实现。文档、配置、运营产物按对应的文本检查、脚本 dry-run 或人工审核链验证。

### phase-log 治理

- `reports/phase-log/` 的目标不是堆流水，而是回答 4 件事：当前项目进度、未完成事项、下一步、历史追溯入口。
- 当前项目状态只看四个入口：
  - `reports/phase-log/CURRENT_STATUS.md`
  - `reports/phase-log/OPEN_ITEMS.md`
  - `reports/phase-log/MILESTONES.md`
  - `reports/phase-log/INDEX.md`
- 根目录只保留当前状态、未完成事项、里程碑、索引、阶段摘要、当前规划文件和最近 `phase{N}.md`；旧 phase / 非标准 markdown / 非 markdown 产物分别进 `archive/phase-history/`、`archive/non-phase-reports/`、`archive/non-markdown-artifacts/`。
- 只有主线阶段变化、关键交付完成、根因 / 结论被证实或推翻、优先级或下一步顺序变化时，才新增短格式 `phase{N}.md`。
- 下列情况禁止单独新增 phase：单次命令执行、一次测试通过、中间排查、retry / rerun、没有新增状态变化的小修补。
- 新 phase 固定只写：这轮达到的目的、当前状态变化、还没完成什么、下一步做什么；默认不超过 20 行、400 中文字。未触发 phase 条件时，不新增 phase；需要保留当前状态差异时，优先更新四入口或 archive 索引。

### 真机排障与产品态保护

- 真机白屏、栈溢出、模拟器正常但真机异常，默认先查构建链路与运行环境差异：`project.config.json`、`project.private.config.json`、Taro build config、browserslist、prebundle、微信开发者工具编译接管。
- 排障前先锁定产品态基线；已验收的首页、详情页、底部导航、按钮样式默认不可被调试污染。
- 真机排障走单变量实验：一次只改一个变量，并说明要证伪什么；需要用户验证时，先说明唯一验证目标。
- 谁为了排障改坏产品态，谁负责先恢复到最近一次可用状态，再继续排障。

### hotpost 当前硬合同

- 细节入口：日常产卡 `docs/sop/2026-04-08-日常产卡SOP.md`；评审发布 `docs/sop/2026-04-08-评审与发布SOP.md`；优化触发 `docs/sop/2026-04-08-优化触发SOP.md`；存储协议 `docs/reference/hotpost-storage-contract.md`。
- 当前主合同是 `value-threshold publishing`。`15 / 30` 是窗口和运营目标，不是硬模板，不再用旧 `15-baseline` 做 hard veto。
- 当前硬门槛只保留：`freshness gate workflow`、`named topic budget`、发布链稳定、首页显示层稳定、`snapshot / cloud_db / miniRelease` 同步链稳定、不把系统打回旧世界。
- freshness gate 是发布前 workflow，不是单次检查器；最终只看 final decision。
- 日常产卡默认 `all-scope`。只有显式局部修复、定向补薄或单 scope deep dive 时，才使用 `--scope <scope_id>`；`business-growth-ops` 只表示工程 slice，不是产品默认范围。
- 时间窗口默认先看 `7d`；只有 `7d` 已确认吃干净且继续深挖净新增明显变少，才开 `15d`；只有显式要求继续扩窗，才开 `30d`。
- quota-aware crawl 是正确 rollout target，但不是默认天然落地主链：`discover -> enrich -> backfill`，`Reddit API` 主采 freshest `hot / signal`，`SociaVault = assist + rescue`，`dry_cycle = 3`，按 `yield exhaustion` 停。
- 当 review queue 没拉出目标 candidate，但原始 candidate 已人工确认值得进草稿时，允许 `python backend/scripts/hotpost/review_cards.py seed <candidate_id> validate --live` 定向落草稿；已有 draft 时继续审已有 draft，不重复 seed。
- 新社区只有同时满足三层才算正式收录：进入 `backend/config/hotpost_supply_discovery_v2.yaml`、`build_reddit_search_specs(scope)` 审计 `MISSING=[]`、`backend/data/hotpost/candidates/<scope>.json` 有实际命中。
- hotpost JSON 维护必须走共享入口。业务层读状态只允许 `load_categories`、`load_candidates`、`load_drafts`、`load_published_cards`；业务层写状态只允许 `mutate_candidates`、`mutate_drafts`、`mutate_drafts_and_published`、`mutate_published_cards`、`merge_published_cards`、`replace_published_cards`。
- `mutate_cards_payload()` 只允许留在状态编排层内部。只改 `published` 的脚本必须走 `published-only` 入口，不能 `load_cards_payload() -> write_cards_payload()` 整桶回写。
- `backend/data/hotpost/mini_snapshots/` 和 `hotpost-mini/.../cloudfunctions/*/data/` 都是发布派生产物，不是内容真相源；只允许 `push_mini_snapshot.py` 写入。小程序只读发布快照，不读 candidates / drafts。

### 数据库三库规则

- 金库 `reddit_signal_scanner` 是标准 / 生产库，只读；非生产环境访问必须显式开启 `ALLOW_GOLD_DB=1`，默认禁止写入。
- Dev 库 `reddit_signal_scanner_dev` 是开发与验收主库，所有联调 / 手工任务写入这里；Test 库 `reddit_signal_scanner_test` 是自动化测试专用，可随时清空重建。
- 数据复制只允许“金库 -> Dev”，且仅按指定 task 相关数据复制；禁止全库复制与反向写回。

## Project Structure & Module Organization

- `backend/`: FastAPI / Celery / Alembic，测试在 `backend/tests/`。
- `frontend/`: Vite + React + TypeScript SPA，测试在 `frontend/tests/` 和 `vitest` specs。
- `hotpost-mini/hotpost-mini-app/`: 独立 git 小程序仓库；产品态回滚基线见 `.product-baseline.json`，恢复命令见 `docs/product-baseline.md`。
- `reports/phase-log/` 记录进度 / 验收 / 分析；`docs/` 放 PRD / 质量门禁 / 架构；`.specify/` 放 spec-driven 真相源；`Makefile` 是统一命令入口。

## Build, Test, and Development Commands

- Setup / dev: `make env-setup`；推荐开发链路 `make dev-golden-path`；单独服务用 `make dev-backend`、`make dev-frontend`。
- Tests / build: `make test-backend`、`make test-frontend`、`make test-e2e`（需服务运行）；前端构建 `cd frontend && npm run build`。
- DB migrations: `make db-migrate MESSAGE="desc"`、`make db-upgrade`、`make db-downgrade`。

## Coding Style & Naming Conventions

- Python: PEP 8, 4-space indent, mandatory type hints; run `mypy --strict` (see `mypy.ini`). Use snake_case for modules/functions, PascalCase for classes, UPPER_SNAKE_CASE for constants.
- TypeScript/React: 2-space indent; ESLint + Prettier enforced (`npm run lint`, `npm run format`). Components in PascalCase, files like `src/components/ReportCard.tsx`.
- Follow quality gates in `docs/2025-10-10-质量标准与门禁规范.md` (Black + isort, no `Any`, no `# type: ignore`).

## Testing Guidelines

- Backend 用 `pytest`，文件名 `test_*.py`，核心模块目标 80%+ 覆盖；Frontend 用 `vitest`（`npm test`、`npm run test:coverage`）；E2E 在服务启动后跑 `make test-e2e`，配置见 `frontend/playwright.config.ts`。

## Commit & Pull Request Guidelines

- Commits: use Conventional Commits, e.g., `feat(backend): add SSE stream`, `fix(frontend): handle empty state)`.
- PRs: include purpose, linked PRD section(s), testing evidence, screenshots for UI changes, relevant `.specify/specs/...` progress reference, and quality-gate evidence (`make phase-1-2-3-verify` or `make test-all` + `mypy --strict`).

## Security & Configuration

- Secrets must stay out of VCS; use `.env.local`、`backend/.env`、`frontend/.env.development`。Ports 见 `docs/reference/PORT_CONFIGURATION.md`，默认 backend `8006`、frontend `3006`、Redis `6379`。需要一致测试环境时用 `docker-compose.test.yml`。
