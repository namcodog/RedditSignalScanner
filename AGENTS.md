# Repository Guidelines

## 使用前提（User Rules）

- 入门阅读顺序：`README.md` → `docs/2025-10-10-文档阅读指南.md` → 角色章节。
- 对话规范：与产品经理沟通一律使用简洁、通俗、健谈的中文，必须说大白话；把工程术语翻译成小白也能明白的表达，直接明了。
- 测试优先：先写测试，再开发实现。
- 进度基线：以 /Users/hujia/Desktop/RedditSignalScanner/reports/phase-log获取最新的信息，进行进度回顾。
- 产出记录：阶段成果与差异必须写入 `reports/phase-log/phase{N}.md`（未记录视为未完成）。
- MCP 工具优先（开发/测试/排障标准）：先用 serena MCP 熟悉代码与定位问题 → 用顺序化思考确认根因 → 用 exa-code MCP 查最佳实践 → 用 Chrome DevTools MCP（端到端的时候非端到端不需要） 验证修复；任何 MCP 安装/配置后需立即自检，超过 12 秒必须停止排查并记录到 `reports/`。
- 执行前必须写分步计划（plan）并按顺序推进。
- 统一反馈四问：1）发现了什么？2）是否需要修复3）精确修复方法？（若无可以不叙述）4）下一步系统性的计划是什么？5）这次执行的价值是什么？达到了什么目的？（若无可以不叙述）
- 数据库三库规则（统一口径）：
  - 金库（`reddit_signal_scanner`）：标准库/生产库，只读；非生产环境禁止写入。
  - Dev 库（`reddit_signal_scanner_dev`）：开发与验收主库；所有联调/手工任务写入这里。
  - Test 库（`reddit_signal_scanner_test`）：自动化测试专用，可随时清空重建。
  - 数据复制只允许“金库 → Dev”，且仅按指定 task 相关数据复制；禁止全库复制与反向写回。
  - 非生产环境访问金库必须显式开启 `ALLOW_GOLD_DB=1`，默认禁止。

## Project Structure & Module Organization

- `backend/`: FastAPI service, Celery tasks, Alembic migrations (`alembic/`), tests in `backend/tests/`.
- `frontend/`: Vite + React + TypeScript SPA (`src/`), tests in `frontend/tests/` and `vitest` specs.
- `reports/phase-log/`: progress, acceptance, and analysis records.
- `docs/`: PRD, quality gates, and architecture notes.
- `.specify/`: spec-driven source of truth (specs, plans, tasks). Use `.specify/specs/*` as the latest progress baseline.
- `Makefile`: unified dev, test, and utility commands.

## Build, Test, and Development Commands

- Setup: `make env-setup` (installs backend and frontend deps).
- Golden path (recommended): `make dev-golden-path` (Redis + Celery + Backend + Frontend + seed data).
- Dev servers: `make dev-backend`, `make dev-frontend`.
- Tests: `make test-backend`, `make test-frontend`, `make test-e2e` (requires services running).
- DB migrations: `make db-migrate MESSAGE="desc"`, `make db-upgrade`, `make db-downgrade`.
- Frontend build: `cd frontend && npm run build`.

## Coding Style & Naming Conventions

- Python: PEP 8, 4-space indent, mandatory type hints; run `mypy --strict` (see `mypy.ini`). Use snake_case for modules/functions, PascalCase for classes, UPPER_SNAKE_CASE for constants.
- TypeScript/React: 2-space indent; ESLint + Prettier enforced (`npm run lint`, `npm run format`). Components in PascalCase, files like `src/components/ReportCard.tsx`.
- Follow quality gates in `docs/2025-10-10-质量标准与门禁规范.md` (Black + isort, no `Any`, no `# type: ignore`).

## Testing Guidelines

- Backend: `pytest` in `backend/tests/` (name as `test_*.py`). Aim for 80%+ coverage on core modules. Safe runner available via Makefile.
- Frontend: `vitest` (`npm test`, `npm run test:coverage`), UI tests in `frontend/tests/`.
- E2E: `make test-e2e` after starting services; Playwright config at `frontend/playwright.config.ts`.

## Commit & Pull Request Guidelines

- Commits: use Conventional Commits, e.g., `feat(backend): add SSE stream`, `fix(frontend): handle empty state)`.
- PRs: include purpose, linked PRD section(s), testing evidence (commands run), and screenshots for UI changes. Ensure quality gates pass: `make phase-1-2-3-verify` or `make test-all` + `mypy --strict`.
- Progress reference: link the relevant `.specify/specs/...` doc and, when applicable, attach `.specify/templates/*`-derived plan/tasks used.

## Security & Configuration

- Secrets: keep out of VCS; use `.env` files (`.env.local`, `backend/.env`, `frontend/.env.development`).
- Ports: see `docs/reference/PORT_CONFIGURATION.md`; defaults backend `8006`, frontend `3006`, Redis `6379`.
- Optional: `docker-compose.test.yml` for consistent test environments.
