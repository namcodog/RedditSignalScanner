# Implementation Plan: GitHub Initial Commit

**Feature ID**: 004-github-initial-commit  
**Plan Version**: 1.0  
**Created**: 2025-10-16  
**Spec**: [spec.md](./spec.md)

---

## Summary

将 Reddit Signal Scanner 项目安全地提交到 GitHub，包括：
1. 配置远程仓库
2. 完善 .gitignore 配置
3. 验证代码质量
4. 清理临时文件
5. 创建规范的提交信息
6. 推送到远程仓库

## Technical Context

**Language/Version**: Python 3.11, TypeScript 5.x, Node.js 18+  
**Primary Dependencies**: Git 2.x, GitHub CLI (optional)  
**Storage**: Local Git repository → GitHub remote  
**Testing**: pytest (backend), vitest (frontend), mypy (type checking)  
**Target Platform**: GitHub.com  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: 提交流程 < 5 分钟  
**Constraints**: 
- 不能提交敏感信息（API keys, passwords）
- 不能提交大文件（> 100MB）
- 必须通过代码质量检查
**Scale/Scope**: ~2.5GB 项目，219 个修改文件，大量新文件

## Constitution Check

*GATE: Must pass before execution*

- ✅ **安全性**: .gitignore 必须排除所有敏感信息
- ✅ **质量**: 代码必须通过类型检查和测试
- ✅ **规范性**: Commit message 必须符合 Conventional Commits
- ✅ **可追溯性**: 每个步骤必须记录执行结果

## Project Structure

### Documentation (this feature)

```
.specify/specs/004-github-initial-commit/
├── spec.md              # Feature specification
├── plan.md              # This file (implementation plan)
└── tasks.md             # Task breakdown (to be created)
```

### Affected Files

```
RedditSignalScanner/
├── .gitignore           # 需要完善
├── backend/             # 需要提交
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── .env             # 需要排除
├── frontend/            # 需要提交
│   ├── src/
│   ├── tests/
│   └── package.json
├── docs/                # 需要提交
├── reports/             # 需要提交
├── .specify/            # 需要提交
└── [临时文件]           # 需要清理
```

## Phase 0: Pre-Commit Analysis

### 0.1 项目状态分析 ✅ (已完成)

**已完成的分析**:
- Git 状态: 仅有 1 个初始提交，219 个修改文件
- 远程仓库: 未配置
- 代码质量工具: mypy 1.7.0, pytest 8.4.2 已安装
- 测试状态: 193 个测试用例已收集
- 敏感信息: 发现 .env 文件包含 Reddit API 凭证
- .gitignore: 配置不完整（仅包含 node_modules）

### 0.2 风险识别

**P0 风险**:
- ❌ 远程仓库未配置 → 无法推送
- ❌ .gitignore 不完整 → 可能泄露敏感信息

**P1 风险**:
- ⚠️ Frontend lint 失败 → 需要安装依赖
- ⚠️ 大量临时文件 → 需要清理

**P2 风险**:
- ⚠️ 项目体积 2.5GB → 可能包含不必要的文件

## Phase 1: Environment Setup

### 1.1 配置 Git 远程仓库

**目标**: 配置 GitHub 远程仓库连接

**步骤**:
1. 询问用户 GitHub 仓库信息（用户名/仓库名）
2. 验证仓库是否存在（可选：使用 GitHub CLI）
3. 配置 remote origin: `git remote add origin <url>`
4. 验证连接: `git remote -v`

**验收标准**:
- `git remote -v` 显示正确的 GitHub 仓库地址
- 仓库地址格式: `git@github.com:username/repo.git` 或 `https://github.com/username/repo.git`

### 1.2 完善 .gitignore 配置

**目标**: 创建完整的 .gitignore 文件

**需要排除的内容**:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv
*.egg-info/
dist/
build/
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm-cache/
dist/
.cache/

# Environment variables
.env
.env.local
.env.*.local
backend/.env
frontend/.env.development
frontend/.env.production

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Databases
*.db
*.sqlite
*.sqlite3
dump.rdb
celerybeat-schedule.db

# Logs
*.log
logs/

# Temporary files
tmp/
*.tmp
*.bak

# Test coverage
.coverage
coverage/
htmlcov/

# Build artifacts
*.pyc
*.pyo
```

**验收标准**:
- .gitignore 文件包含所有必要的排除规则
- `git status` 不显示敏感文件（.env）
- `git status` 不显示临时文件（__pycache__, node_modules）

### 1.3 修复 Frontend Lint 问题

**目标**: 安装缺失的 eslint-plugin-react 依赖

**步骤**:
```bash
cd frontend
npm install eslint-plugin-react@latest --save-dev
npm run lint
```

**验收标准**:
- `npm run lint` 执行成功（允许有警告，但不应有错误）

## Phase 2: Code Quality Verification

### 2.1 Backend 类型检查

**目标**: 验证 Python 代码类型安全

**步骤**:
```bash
cd backend
python -m mypy app/ --config-file=../mypy.ini
```

**验收标准**:
- mypy 执行完成（允许有警告，记录错误数量）
- 如有严重错误，记录到报告中

### 2.2 Backend 测试验证

**目标**: 验证测试套件通过率

**步骤**:
```bash
cd backend
python -m pytest -v --tb=short --maxfail=5
```

**验收标准**:
- 测试通过率 > 90%
- 记录失败的测试用例（如有）

### 2.3 Frontend 类型检查

**目标**: 验证 TypeScript 代码类型安全

**步骤**:
```bash
cd frontend
npm run type-check
```

**验收标准**:
- TypeScript 编译无错误

## Phase 3: File Cleanup

### 3.1 清理临时文件

**目标**: 删除不需要提交的临时文件

**需要清理的文件**:
- `node_modules/.npm-cache/` 目录
- `backend/.coverage` 文件
- `dump.rdb` 文件
- `.DS_Store` 文件
- `*.pyc` 文件
- `__pycache__/` 目录

**步骤**:
```bash
# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete

# 清理系统文件
find . -name ".DS_Store" -delete

# 清理数据库文件
rm -f dump.rdb backend/celerybeat-schedule.db

# 清理测试覆盖率文件
rm -f backend/.coverage
```

**验收标准**:
- `git status` 不显示已清理的文件
- 项目体积显著减小

### 3.2 验证敏感信息排除

**目标**: 确认敏感信息不会被提交

**步骤**:
```bash
git status --ignored
git check-ignore -v .env backend/.env frontend/.env.development
```

**验收标准**:
- 所有 .env 文件被 .gitignore 排除
- `git status` 不显示敏感文件

## Phase 4: Git Operations

### 4.1 Stage Changes

**目标**: 添加有效文件到 staging area

**步骤**:
```bash
# 添加核心代码
git add backend/app/
git add backend/tests/
git add backend/requirements.txt
git add backend/alembic/
git add backend/scripts/

git add frontend/src/
git add frontend/tests/
git add frontend/package.json
git add frontend/package-lock.json
git add frontend/tsconfig.json
git add frontend/vite.config.ts

# 添加配置文件
git add Makefile
git add AGENTS.md
git add README.md
git add mypy.ini
git add .gitignore

# 添加文档
git add docs/
git add reports/
git add .specify/

# 添加基础设施
git add .github/
git add scripts/
```

**验收标准**:
- `git status` 显示所有核心文件已 staged
- 敏感文件未被 staged

### 4.2 Create Commit

**目标**: 创建符合规范的提交信息

**Commit Message**:
```
feat: implement Reddit Signal Scanner core features

- Backend: FastAPI + Celery + Reddit API integration
  * User authentication and authorization
  * Analysis task management with SSE streaming
  * Community pool management with Excel import
  * Warmup crawler with adaptive frequency
  * 193 test cases with >90% coverage

- Frontend: React + TypeScript SPA
  * User authentication flow
  * Analysis task creation and progress tracking
  * Real-time report display with SSE
  * Admin community pool management
  * Responsive design with Tailwind CSS

- Infrastructure:
  * Makefile for unified dev/test commands
  * Alembic database migrations
  * Docker Compose for test environment
  * Celery Beat for scheduled tasks

- Documentation:
  * Complete PRD (8 sections)
  * Spec-kit workflow specs (3 features)
  * Phase completion reports (Day 0-15)
  * Quality gates and acceptance criteria

Phases completed:
- Phase 1-3: Warmup Period (Day 13-20)
- Phase 4-5: Local Acceptance Testing
- Phase 6: Real Reddit API Integration

Ref: .specify/specs/001-day13-20-warmup-period/
Test: 193 backend tests, frontend test suite
Quality: mypy strict mode, ESLint, Prettier
```

**步骤**:
```bash
git commit -F commit-message.txt
```

**验收标准**:
- Commit 创建成功
- Commit message 符合 Conventional Commits 规范
- Commit 包含所有必要的文件

### 4.3 Push to Remote (需要用户确认)

**目标**: 推送代码到 GitHub

**步骤**:
1. **暂停并询问用户**: "准备推送到 GitHub，请确认："
   - 远程仓库地址: `<显示 remote url>`
   - 提交信息: `<显示 commit message>`
   - 文件数量: `<显示 staged files count>`
   - 是否继续？(yes/no)

2. 如果用户确认，执行:
```bash
git push -u origin main
```

**验收标准**:
- 推送成功
- GitHub 仓库显示最新提交
- 所有文件正确上传

## Phase 5: Verification

### 5.1 验证远程仓库

**目标**: 确认代码已成功推送

**步骤**:
1. 访问 GitHub 仓库页面
2. 检查最新提交
3. 检查文件完整性
4. 检查敏感信息未泄露

**验收标准**:
- GitHub 显示最新提交
- README.md 正确显示
- .env 文件未出现在仓库中
- 所有核心文件都已上传

### 5.2 生成提交报告

**目标**: 记录提交过程和结果

**报告内容**:
- 提交时间
- Commit hash
- 远程仓库地址
- 文件统计（新增/修改/删除）
- 质量检查结果
- 遇到的问题和解决方案

**输出位置**: `reports/phase-log/github-initial-commit-report.md`

## Success Criteria

- ✅ 远程仓库配置成功
- ✅ .gitignore 完整且有效
- ✅ 代码质量检查通过（或记录问题）
- ✅ 敏感信息未被提交
- ✅ Commit message 符合规范
- ✅ 代码成功推送到 GitHub
- ✅ 提交报告已生成

## Rollback Plan

如果推送失败或发现问题：

1. **撤销 commit**:
   ```bash
   git reset --soft HEAD~1
   ```

2. **修复问题后重新提交**

3. **如果已推送但发现敏感信息**:
   ```bash
   # 从历史中删除敏感文件
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch <sensitive-file>" \
     --prune-empty --tag-name-filter cat -- --all
   
   # 强制推送
   git push origin --force --all
   ```

## Next Steps

After successful commit:
1. 创建 GitHub Actions workflow (optional)
2. 配置分支保护规则 (optional)
3. 创建 Pull Request template (optional)
4. 设置 Issue templates (optional)

