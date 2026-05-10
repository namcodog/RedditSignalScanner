# CLAUDE.md

本文件是 Claude Code 的独立入口，覆盖：启动序列、行为准则、业务硬约束、工程规范、skill 路由。

---

## 会话启动（每次必须执行）

### key-os 使用协议（强约束）

`key-os` 是外部 OS，不是当前项目仓库的一部分。统一只通过 `keyos` CLI 访问，禁止直接进入 `KEYOS_ROOT` 文件树。

**启动固定序列：**
```
keyos status --json
keyos check --json
keyos read --json
```
- `keyos read --json` 返回的 `files` 是跨项目连续性首跳，不替代本项目 phase-log 当前状态。
- 已知目标时，再按需扩展：`keyos read rules --json`、`keyos read wiki --json`、`keyos read audit --json`、`keyos read project:<name> --json`。
- 扩展读取只补充跨项目规则和历史判断；涉及 RedditSignalScanner 当前进度时，仍必须回到 `reports/phase-log/` 四入口核实。

**调用边界：**
- 研究/资料任务优先：`keyos wiki query --json`、`keyos wiki ingest ... --json`。
- 任务完成需沉淀经验：`keyos close ... --json`；高价值任务优先 `keyos steward prepare ... --json` / `keyos steward close ... --json`。
- 写回仅限高价值判断，且只允许用：`keyos inbox ...`、`keyos write ...`、`keyos close ...`、`keyos steward ...`、`keyos wiki ...`。

**失败处理：**
- `keyos` 无有效 JSON、JSON 明确 failure、或无法判断当前状态 → 先停止，立即 `keyos doctor --json`。
- `keyos check --json` 的纯 warning 不算硬失败，记录后继续。

**明确禁止：**
- 不要直接手改 `daily / project / wiki` 文件，不要直接进入 `KEYOS_ROOT` 文件树找内容，不要把自己当成 `key-os` 仓库维护者。
- 你的职责是使用 `key-os`、读取 `key-os`、回填高价值结果给 `key-os`。
- 不在当前项目目录里再维护第二套长期记忆系统。
- `mem/` 仅作历史资料层保留，若与 `keyos` CLI 返回结果冲突，以 `keyos` 为准。

### phase-log 四入口

项目状态四入口（涉及进度/下一步时必须读）：
```
reports/phase-log/CURRENT_STATUS.md  OPEN_ITEMS.md  MILESTONES.md  INDEX.md
```
- 按任务类型读 SOP / reference / 代码，不一上来全量读 docs。
- key-os 与 phase-log 冲突时：不静默合并，先说明冲突，以最新项目产物为准。

---

## 行为准则：Karpathy 编码规则（强约束，最高频使用）

这组规则用于减少 LLM 常见编码错误。极简单任务可用判断力压缩流程，但不能跳过事实核实和必要验证。

### 1. 先想清楚再写代码
- 不做未经说明的假设；有假设必须明说。
- 不隐藏困惑；不确定时先问，或先指出缺口。
- 多种解释同时存在时，列出解释和取舍，不静默选一种。
- 有更简单方案时必须说出来；当前方案不合理时要直接指出。

### 2. 简单优先
- 只写解决当前问题的最小代码。
- 不做未被要求的新功能。
- 不为单次使用代码抽象。
- 不增加未被要求的灵活性、配置化或扩展点。
- 不为不可能或不该发生的场景写防御性错误处理。
- 如果 200 行能被 50 行清楚解决，必须重写成更短版本。
- 自检问题：资深工程师会不会认为这过度复杂？如果会，先简化。

### 3. 手术式改动
- 只碰必须修改的内容。
- 不顺手美化旁边代码、注释、格式。
- 不重构没有坏掉的东西。
- 匹配现有代码风格，即使你个人会用另一种写法。
- 发现无关死代码时只指出，不删除。
- 只删除本次改动制造出来的未使用 import / 变量 / 函数。
- 每一行 diff 都必须能追溯到用户当前请求。

### 4. 目标导向执行
- 先定义成功标准，再循环到验证通过。
- "加校验"要落成"为非法输入写测试，再让测试通过"。
- "修 bug"要落成"写出复现 bug 的测试，再让测试通过"。
- "重构"要落成"改前改后测试都通过"。
- 多步任务必须写短计划，格式是：步骤 -> 验证点。
- "让它能用"这种弱标准不允许作为完成条件；必须拆成可检查的验收点。

**生效标准：** diff 无关改动变少、过度复杂返工变少、澄清问题发生在实现前而非出错后。

**对话与反馈：**
- 中文沟通，工程术语翻成大白话；不用敷衍/讨好式表达。
- 站在需求对立面审视，不迎合口头判断；未核实的方法不当作解决方案。
- 重要任务收尾覆盖五件事：发现什么、须修复吗、精确修法、下一步、执行价值。

**实现纪律：**
- 多步任务执行前必须写分步计划并翻译成可验证结果。
- 不写模糊 fallback；assist/rescue 必须可观测、可验证、不吞错误。
- 新增逻辑优先拆到职责清楚的小文件。

**MCP 工具使用场景：**

| 场景 | 工具 | 说明 |
|---|---|---|
| 代码搜索/符号定位 | `serena` | 项目内找函数、类、引用，优先用 serena |
| 库/框架 API 文档 | `context7` | 查第三方库用法、最新 API |
| 通用网页搜索 | `tavily-mcp` | 日常搜索、新闻、实时信息 |
| 语义/学术搜索 | `exa` | 需要语义理解的高质量搜索、论文检索 |
| 网页内容读取 | `jina` (read_url) 或 `WebFetch` | 提取网页全文，jina 对 paywall/JS 页面更强 |
| 批量 URL 抓取 | `jina` (parallel_read_url) | 同时读多个 URL |
| 网页截图 | `jina` (capture_screenshot_url) | 不需要交互的静态截图 |
| 浏览器交互/UI 测试 | `playwright` | 需要点击、填表、导航的端到端操作 |
| 浏览器调试/性能 | `chrome-devtools` | 审查网络请求、console、性能分析 |
| 复杂多步推理 | `sequential-thinking` | 需要分步思考的根因分析、架构决策 |
| 远程文档查询 | `mcp-deepwiki` | 查 GitHub 仓库的 deepwiki 文档 |
| 规格工作流 | `spec-workflow` | 创建/管理 spec、记录实现日志 |

**选择原则：**
- 代码相关优先 `serena`，库文档优先 `context7`。
- 网页搜索：一般查资料用 `tavily`，需要高质量/语义搜索用 `exa`。
- 网页内容：单页面用 `jina read_url`，需要交互用 `playwright`。
- 截图：静态用 `jina capture_screenshot_url`，需要交互态用 `playwright`。
- 非 UI/E2E 任务不强制使用浏览器；MCP 安装后 12s 内不可用即停并记录到 `reports/`。
- 代码行为变更测试优先：先补/更新测试，再改实现。

---

## 业务硬约束

### hotpost（不可违反）

- **主合同**：`value-threshold publishing`，`15/30` 是窗口不是硬模板。
- **硬门槛**：freshness gate workflow、named topic budget、发布链/snapshot/cloud_db/miniRelease 同步链稳定、不退回旧世界。
- **日常默认**：`all-scope`；时间窗默认 `7d`，吃净后才开 `15d`，显式要求才开 `30d`。
- **采集链**：`discover→enrich→backfill`，Reddit API 主采 freshest `hot/signal`，SociaVault=assist+rescue，`dry_cycle=3`，按 yield exhaustion 停。
- **JSON 维护**：读写必须走共享入口（load_*/mutate_*），`mutate_cards_payload()` 仅限编排层内部。
- **小程序**：只读发布快照，不读 candidates/drafts；snapshot 仅 `push_mini_snapshot.py` 写入。
- **新社区收录三条件**：进入 discovery v2 YAML、审计 MISSING=[]、candidates JSON 有实际命中。

细节入口：`docs/sop/2026-04-08-日常产卡SOP.md` / `评审与发布SOP.md` / `优化触发SOP.md`

### 数据库三库

| 库 | 用途 | 约束 |
|---|---|---|
| `reddit_signal_scanner` | 金库/生产 | 只读；写入需 `ALLOW_GOLD_DB=1` |
| `reddit_signal_scanner_dev` | 开发验收 | 联调/手工任务写入此库 |
| `reddit_signal_scanner_test` | 自动化测试 | 可随时清空重建 |

禁止全库复制与反向写回，仅允许金库→Dev 按 task 复制。

### 真机排障

- 真机异常先查构建链差异（project.config.json、Taro build config、prebundle 等）。
- 排障前锁定产品态基线，单变量实验（一次一个变量，说明要证伪什么）。
- 排障改坏产品态的，先恢复到最近可用状态再继续。

---

## phase-log 治理

- 四入口（CURRENT_STATUS/OPEN_ITEMS/MILESTONES/INDEX）是唯一真相源。
- 新增 phase 条件：主线阶段变化、关键交付完成、根因被证实/推翻、优先级变化。禁止为单次命令/测试通过/中间排查/retry 新增 phase。
- 新 phase 不超过 20 行/400 中文字，只写：目的、状态变化、未完成、下一步。
- 旧文件归档：`archive/phase-history/`、`archive/non-phase-reports/`、`archive/non-markdown-artifacts/`。

---

## 工程规范

**项目结构：** `backend/` (FastAPI+Celery+Alembic) | `frontend/` (Vite+React+TS) | `hotpost-mini/hotpost-mini-app/` (独立 git 小程序) | `reports/phase-log/` | `docs/` | `Makefile` 统一入口

**常用命令：**

| 场景 | 命令 |
|---|---|
| 开发环境 | `make dev-golden-path` |
| 后端测试 | `make test-backend` |
| 前端测试 | `make test-frontend` |
| E2E 测试 | `make test-e2e` |
| DB 迁移 | `make db-migrate MESSAGE="desc"` |

**代码风格：** Python PEP 8 + mypy --strict + Black/isort | TS/React 2-space + ESLint/Prettier | 禁用 `Any` 和 `# type: ignore`

**提交：** Conventional Commits (`feat(backend): ...`, `fix(frontend): ...`)

**安全：** Secrets 不入 VCS (`.env.local`/`backend/.env`/`frontend/.env.development`) | 端口 back 8006 / front 3006 / Redis 6379

---

## Skill 路由

**架构：** gstack（决策层：该不该做、做什么） + superpowers（执行层：怎么做）。小改动直接进执行层。

**本项目定制 skills（主入口）：** `.agents/skills/` — gstack/superpowers 的精简中文定制版

**默认主链：** `决策 → 执行 → 验收`

```
需求方向清晰吗？
  否 → gstack-office-hours    (.agents/skills/office-hours)
  是 → 方案已有？
         否 → 直接讨论
         是 → 范围/架构有疑问？
                 是 → gstack-plan-ceo-review  (.agents/skills/plan-ceo-review)
                      gstack-plan-eng-review  (.agents/skills/plan-eng-review)
                 否 → using-superpowers → executing-plans (.agents/skills/executing-plans)
```

**验收层（gstack 原版）：** `gstack-review`（代码审查）、`gstack-qa`（修复+验收）、`gstack-qa-only`（只出报告）

**禁止：** 同时拉多套决策 skill、默认扩散到额外设计评审、用 brainstorming/writing-plans 作主入口。

路由总则详见 `.agents/workflows/skills-routing.md`。
