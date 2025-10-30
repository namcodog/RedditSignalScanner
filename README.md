# Reddit Signal Scanner - AI驱动的商业洞察工具

> **项目状态**: ✅ **Phase 0-3 已完成，E2E 测试通过**
> **创建日期**: 2025-10-10
> **最后更新**: 2025-10-28
> **当前版本**: v0.9.0 (MVP 核心功能完成)
> **质量承诺**: 100% PRD符合度 + Linus设计哲学 + 类型安全零容忍

---

## 🎯 项目概述

Reddit Signal Scanner 是一个智能商业洞察工具，帮助产品创始人从 Reddit 讨论中快速发现：
- 🎯 用户痛点（Pain Points）
- 🏢 竞品分析（Competitors）
- 💡 商业机会（Opportunities）

**核心承诺**: 30秒输入，5分钟分析，找到目标客户的真实声音。

### 🆕 最新更新（2025-10-28）

- 新增 `make local-acceptance` 一键验收脚本：自动校验 Redis/Celery/后端/前端健康状态，并跑通注册→分析→报告→导出全链路。
- 报告页面支持“关键实体”标签页，基于实体词典汇总品牌、功能与痛点命中度，辅助产品经理快速确认线索。

### 📊 当前项目状态

| Phase | 完成度 | 状态 | 关键成果 |
|-------|--------|------|---------|
| **Phase 0: 冷热分层基础** | 100% (5/5) | ✅ COMPLETE | 增量抓取 + 双写架构 |
| **Phase 1: 数据基础设施** | 87.5% (7/8) | ✅ 核心完成 | 社区池管理 + 监控系统 |
| **Phase 2: 分析引擎改造** | 100% (10/10) | ✅ COMPLETE | 样本守卫 + 去重优化 |
| **Phase 3: 评测与优化** | 96% (47/49) | ✅ 编码完成 | 标注工作流 + 红线检查 |
| **P0: 测试基础稳固** | 100% (4/4) | ✅ COMPLETE | 测试性能提升 42% |
| **E2E 测试** | 100% | ✅ COMPLETE | 完整产品闭环验证 |
| **Phase 4: 迭代与延伸** | 0% (0/6) | ⏳ NOT_STARTED | NER + 趋势分析 |

**关键指标**:
- ✅ 测试通过率：250/250 (100%)
- ✅ CI/CD：所有检查通过
- ✅ 代码质量：mypy --strict 零错误
- ✅ 性能：去重性能提升 95%，测试执行时间提升 42%

---

## 🚀 快速启动

### 方式 1: 使用 Makefile（推荐）

```bash
# 查看所有可用命令
make help

# 查看快速启动指南
make quickstart

# 启动后端服务器（终端 1）
make dev-backend
# 访问: http://localhost:8006
# API 文档: http://localhost:8006/docs

# 启动前端服务器（终端 2）
make dev-frontend
# 访问: http://localhost:3006

# 运行测试
make test-backend

# 运行端到端测试（需完整环境）
make test-e2e

# 验证Admin端到端流程（需设置ADMIN_EMAILS）
make test-admin-e2e

# 启动 Celery Worker（可选，终端 3）
make celery-start
```

> ℹ️ **Makefile 公共脚本**：常见的环境加载、服务启动和健康检查逻辑已统一收敛到 `scripts/makefile-common.sh`。
> 扩展新命令时，优先在该脚本中添加函数再在 Makefile 中调用，以保持命令行为一致。

### 方式 2: 手动启动

```bash
# 后端
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8006

# 前端（新终端）
cd frontend
npm run dev

# Celery Worker（可选，新终端）
cd backend
python scripts/start_celery_worker.py
```

### 常用 Makefile 命令

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make quickstart` | 显示快速启动指南 |
| `make dev-backend` | 启动后端服务器 (端口 8006) |
| `make dev-frontend` | 启动前端服务器 (端口 3006) |
| `make test-backend` | 运行后端测试 |
| `make test-e2e` | 运行端到端测试（需Redis + Celery + Backend） |
| `make test-admin-e2e` | 验证Admin端到端流程（需配置`ADMIN_EMAILS`） |
| `make celery-start` | 启动 Celery Worker |
| `make local-acceptance` | 一键执行本地验收脚本并生成 Markdown 报告 |
| `make db-upgrade` | 升级数据库到最新版本 |
| `make clean` | 清理所有生成文件 |
| `make deploy-checklist` | （待实现）部署前Checklist占位 |

> **部署 / 运维**：生产部署步骤详见 `docs/DEPLOYMENT.md`；日常监控、故障排查和备份请参考 `docs/OPERATIONS.md`。

#### Makefile 模块结构

- `Makefile` 仅保留变量、帮助信息以及 `makefiles/*.mk` 的 `include`；
- 公共 shell 函数集中在 `scripts/makefile-common.sh`；
- 目录拆分：`dev.mk`（开发/黄金路径）、`test.mk`（测试）、`celery.mk`、`infra.mk`（Redis/端口）、`db.mk`、`acceptance.mk`、`tools.mk`、`clean.mk`、`ops.mk` 等。
- 拓展新命令时，优先在公共脚本中补函数，然后在对应模块的新目标里引用，避免重复脚本逻辑。

#### Admin Dashboard 端到端验证指南
1. **配置管理员邮箱**：确保后端启动前已设置 `ADMIN_EMAILS`，例如  
   ```bash
   export ADMIN_EMAILS=admin-e2e@example.com
   export ADMIN_E2E_PASSWORD=TestAdmin123   # 如需复用现有管理员密码
   ```
2. **启动依赖服务**：按 `make dev-backend`、`make celery-start`、`make redis-start` 启动 Redis、Celery、后端服务（需要完整分析流水线可用）。
3. **执行脚本**：运行 `make test-admin-e2e`，脚本会自动：
   - 注册/登录管理员和辅助测试用户
   - 创建分析任务并等待完成
   - 校验 `/api/admin/dashboard/stats`、`/api/admin/tasks/recent`、`/api/admin/users/active`
4. **查看结果**：脚本成功后会输出关键指标；若失败，请根据提示检查服务状态、管理员邮箱配置或Celery日志。

---

## 📚 文档导航

> 💡 **首次阅读？** 请查看 [📖 文档阅读指南](./2025-10-10-文档阅读指南.md) - 包含分角色、分阶段的详细阅读路径

### 🗺️ 主文档（必读）

#### 1. [0-1重写蓝图](./2025-10-10-Reddit信号扫描器0-1重写蓝图.md)
**用途**: 总体架构、技术选型、15天实施路线图

**关键内容**:
- 重写原因和优势
- 核心设计原则（Linus哲学）
- Phase 0-5 详细实施计划
- 代码示例和验收标准

**适合人群**: 全体开发人员、技术负责人

---

#### 2. [每日实施检查清单](./2025-10-10-实施检查清单.md)
**用途**: 每日任务跟踪、进度管理、质量验收

**关键内容**:
- Day 0-15 详细任务清单
- 每日验收标准
- 质量门禁检查脚本
- 每日总结模板

**使用方式**: 每天开始前查看当天任务，结束前填写总结

**适合人群**: 全体开发人员（必须每日使用）

---

#### 3. [架构决策记录ADR](./2025-10-10-架构决策记录ADR.md)
**用途**: 记录所有重大技术决策的背景、理由和后果

**已记录的决策**:
- ADR-001: 4表架构 vs 多表设计
- ADR-002: SSE vs 轮询
- ADR-003: 缓存优先架构
- ADR-004: 类型安全零容忍
- ADR-005: Pydantic Schema验证
- ADR-006: Celery任务队列
- ADR-007: React + TypeScript
- ADR-008: JWT认证
- ADR-009: PostgreSQL数据库
- ADR-010: 测试金字塔
- ADR-011: Git工作流

**适合人群**: 架构师、技术负责人、新人Onboarding

---

#### 4. [质量标准与门禁规范](./2025-10-10-质量标准与门禁规范.md)
**用途**: 定义代码质量标准、门禁流程、检查清单

**关键内容**:
- 4级质量门禁（开发→提交→PR→发布）
- 类型安全标准（零容忍原则）
- 测试质量要求（覆盖率>80%）
- 代码格式规范
- 命名规范
- 文档标准

**适合人群**: 全体开发人员（必读）

---

#### 5. [📖 文档阅读指南](./2025-10-10-文档阅读指南.md) ⭐ 新增
**用途**: 帮助团队快速定位所需文档，理解文档关系

**关键内容**:
- 文档全景地图和依赖关系图
- 分角色阅读路径（新人/后端/前端/架构师/QA）
- 分阶段阅读清单（Day 0-15）
- 与最小化Navigator的协同阅读策略
- 常见问题FAQ和快速查找指南

**使用方式**:
- 新人第一天：完整阅读"新人开发者"章节
- 日常开发：按当前阶段查找对应文档
- 遇到问题：查看FAQ或快速查找表

**适合人群**: 全体团队成员（强烈推荐首先阅读）

---

#### 6. [🚀 3人并行开发方案](./docs/2025-10-10-3人并行开发方案.md) ⭐ 新增
**用途**: 3人团队12天并行开发的完整执行方案

**关键内容**:
- 3个角色定义（后端A/后端B/前端）
- 12天详细时间线（每天每人任务）
- 依赖关系和协作节点
- 无Mock开发策略
- 每日工作节奏和质量保证

**使用方式**:
- 团队开始前：全员阅读角色定义
- 每日早上：查看当天的任务分工
- 遇到阻塞：查看阻塞处理策略

**适合人群**: 3人团队（2后端+1前端）

**优势**: 相比单人15天，节省25%时间（12天完成）

---

#### 7. [⚙️ 环境配置完全指南](./docs/2025-10-10-环境配置完全指南.md) ⭐ 新增
**用途**: 开发环境一站式配置指南

**关键内容**:
- 完整依赖清单（Python/Node/PostgreSQL/Redis）
- 配置文件示例（.env/mypy.ini/pytest.ini/docker-compose.yml）
- 3种安装方式（本地/Docker/快速启动）
- 环境验证脚本
- 常见问题排查

**使用方式**:
- Day 0必读：按照快速开始3步配置环境
- 遇到问题：查看常见问题章节
- 环境维护：定期检查依赖更新

**适合人群**: 全体开发人员（Day 0必读）

**特点**: 复制粘贴即可用的完整配置

---

### 📖 原项目参考文档

这些文档位于 `/Users/hujia/Desktop/最小化Navigator/docs/PRD/`

#### PRD文档（按实施顺序）

| 编号 | 文档 | 状态 | 优先级 | 对应阶段 |
|------|------|------|--------|---------|
| PRD-01 | [数据模型设计](../最小化Navigator/docs/PRD/PRD-01-数据模型.md) | ✅ 完整 | P0 | Phase 1 (Day 1-2) |
| PRD-02 | [API设计规范](../最小化Navigator/docs/PRD/PRD-02-API设计.md) | ✅ 完整 | P0 | Phase 2 (Day 3-5) |
| PRD-03 | [分析引擎设计](../最小化Navigator/docs/PRD/PRD-03-分析引擎.md) | ✅ 完整 | P0 | Phase 2 (Day 6-8) |
| PRD-04 | [任务系统架构](../最小化Navigator/docs/PRD/PRD-04-任务系统.md) | ✅ 完整 | P0 | Phase 2 (Day 6-8) |
| PRD-05 | [前端交互设计](../最小化Navigator/docs/PRD/PRD-05-前端交互.md) | ✅ 完整 | P1 | Phase 3 (Day 9-11) |
| PRD-06 | [用户认证系统](../最小化Navigator/docs/PRD/PRD-06-用户认证.md) | ✅ 完整 | P1 | Phase 3 (Day 9-11) |
| PRD-07 | [Admin后台设计](../最小化Navigator/docs/PRD/PRD-07-Admin后台.md) | ✅ 完整 | P2 | Phase 4 (Day 12-13) |
| PRD-08 | [端到端测试规范](../最小化Navigator/docs/PRD/PRD-08-端到端测试规范.md) | ✅ 完整 | P1 | Phase 5 (Day 14-15) |

#### 其他参考文档

- [PRD索引](../最小化Navigator/docs/PRD/PRD-INDEX.md) - PRD依赖关系和实施顺序
- [架构概览](../最小化Navigator/docs/PRD/ARCHITECTURE.md) - 模块边界和依赖规范
- [敏捷开发避坑指南](../最小化Navigator/2025-10-09-敏捷开发避坑与高效交付指南.md) - 开发流程和环境准备
- [项目核查报告](../最小化Navigator/docs/strategy/2025-10-08-项目全面深度核查报告.md) - 现有项目问题分析

---

## 🚀 快速开始

### 新人Onboarding（第一天）

**Step 1: 阅读文档（2小时）**
1. 阅读本README（10分钟）
2. **[📖 文档阅读指南](./2025-10-10-文档阅读指南.md) - 新人开发者章节（20分钟）** ⭐ 必读
3. 阅读[0-1重写蓝图](./2025-10-10-Reddit信号扫描器0-1重写蓝图.md)的"执行摘要"和"核心设计原则"章节（30分钟）
4. 阅读[质量标准](./2025-10-10-质量标准与门禁规范.md)的"零容忍原则"和"质量门禁"章节（30分钟）
5. 浏览[架构决策记录](./2025-10-10-架构决策记录ADR.md)（30分钟）
6. 查看[PRD-INDEX](../最小化Navigator/docs/PRD/PRD-INDEX.md)了解功能全貌（30分钟）

**Step 2: 环境搭建（2-3小时）**
按照[⚙️ 环境配置完全指南](./docs/2025-10-10-环境配置完全指南.md)执行 - 提供完整的依赖安装和配置文件

**Step 3: 熟悉流程（1小时）**
1. 配置IDE（VSCode settings.json）
2. 安装pre-commit hooks
3. 运行示例质量检查

---

## 📋 开发流程

### 每日工作流程

```bash
# 1. 早上：查看当日任务
cat 2025-10-10-实施检查清单.md | grep "Day X"

# 2. 开发过程中：实时类型检查（IDE自动）

# 3. 提交前：自动门禁检查
git commit -m "..."  # pre-commit自动运行

# 4. 晚上：质量检查
./scripts/daily_quality_check.sh

# 5. 填写每日总结
vim 2025-10-10-实施检查清单.md
```

### API 契约维护

- **更新 OpenAPI 基线**：`make update-api-schema`（当后端接口有意变更时执行，并提交 `backend/docs/openapi-schema.json`）。
- **生成前端 API SDK**：`make generate-api-client`（基于最新 OpenAPI Schema 输出 TypeScript 客户端）。
- **后台任务巡检**：`make test-tasks-smoke`（快速检查维护/监控 Celery 任务封装是否正常）。

### Git工作流

```bash
# 1. 创建feature分支
git checkout -b feature/dayX-task-name

# 2. 开发 + 测试

# 3. 提交（触发pre-commit）
git add .
git commit -m "feat(模块): 简短描述

- 详细变更1
- 详细变更2

符合PRD-0X章节X.X"

# 4. 推送并创建PR
git push origin feature/dayX-task-name

# 5. 等待CI检查和代码Review

# 6. 合并到main
```

---

## 🎯 关键里程碑

| 日期 | 里程碑 | 交付物 | 状态 |
|------|--------|--------|------|
| 2025-10-16 | Phase 0 完成 | 冷热分层架构 + 增量抓取 | ✅ 完成 |
| 2025-10-17 | Phase 1 完成 | 社区池管理 + 监控系统 | ✅ 完成 |
| 2025-10-18 | Phase 2 完成 | 样本守卫 + 去重优化 | ✅ 完成 |
| 2025-10-20 | Phase 3 完成 | 标注工作流 + 红线检查 | ✅ 完成 |
| 2025-10-21 | P0 + E2E 完成 | 测试优化 + 完整产品验证 | ✅ 完成 |
| 待定 | Phase 4 开始 | NER + 趋势分析 + 证据图谱 | ⏳ 待开始 |

### 🎉 最新成果（2025-10-21）

**E2E 测试完成**:
- ✅ 完整产品闭环验证（用户注册 → 任务提交 → 报告生成）
- ✅ JWT 认证机制验证
- ✅ SSE 实时通信验证
- ✅ Celery 异步任务验证
- ✅ Reddit API 真实数据抓取（317 条）
- ✅ 数据库记录完整性验证

**性能优化成果**:
- 去重性能：500 帖子从几十秒 → <1 秒（提升 95%）
- 测试执行时间：>120s → 69.58s（提升 42%）
- 数据库查询：减少 80%
- Reddit API 调用：减少 50%

**代码质量**:
- 测试通过率：250/250 (100%)
- CI/CD：所有检查通过
- mypy --strict：零错误
- 代码覆盖率：>80%

---

## ✅ 验收标准与完成情况

### 功能完整性

- [x] PRD-01: 数据模型 100%实现 ✅
- [x] PRD-02: API设计 100%实现 ✅
- [x] PRD-03: 分析引擎 100%实现 ✅
- [x] PRD-04: 任务系统 100%实现 ✅
- [x] PRD-05: 前端交互 100%实现 ✅
- [x] PRD-06: 用户认证 100%实现 ✅
- [ ] PRD-07: Admin后台 部分实现（基础功能完成）
- [x] PRD-08: 测试规范 100%实现 ✅

### 质量指标

- [x] mypy --strict: **0错误** ✅
- [x] 后端测试覆盖率: **>80%** ✅
- [x] 前端测试覆盖率: **>70%** ✅
- [x] API响应时间: **<200ms** ✅
- [x] 分析完成时间: **<300s** ✅
- [x] 无 `# type: ignore` ✅
- [x] 无 `Any` 类型 ✅
- [x] 无 `Dict[str, Any]` ✅

### 文档完整性

- [x] README.md ✅
- [x] API文档（OpenAPI）✅
- [x] 部署文档 ✅
- [x] 维护手册 ✅
- [x] 所有ADR记录 ✅
- [x] E2E 测试报告 ✅
- [x] 性能优化报告 ✅

---

## 📞 团队协作

### 沟通渠道
- **每日站会**: 15分钟，同步进度和阻塞项
- **每周质量复盘**: 检查质量指标，调整计划
- **技术决策会**: 重大技术选型需要团队讨论

### 角色分工
- **技术负责人**: 架构决策、代码Review、风险管理
- **后端开发**: 数据模型、API、分析引擎、任务系统
- **前端开发**: React SPA、SSE客户端、UI组件
- **QA**: 测试用例、质量门禁、自动化测试
- **DevOps**: 环境搭建、CI/CD、部署

---

## 🆘 常见问题

### Q1: 为什么要从0重写而不是修复现有代码？

**A**: 基于2025-10-08深度核查报告：
- 现有项目存在架构债务（数据流转故障、API膨胀、配置混乱）
- 重写可以避免历史包袱
- 基于PRD从第一天构建正确的架构
- 15天交付MVP比修复历史债务更快

### Q2: 如何保证15天能完成？

**A**:
- 完整详细的PRD文档（无需设计）
- 明确的质量标准（避免返工）
- 每日检查清单（进度可控）
- 类型安全内建（减少bug）

### Q3: 类型安全零容忍会不会影响开发速度？

**A**:
- 初期稍慢，但避免后期返工
- IDE提供强大的类型提示和自动补全
- 重构更安全（编译期发现错误）
- 总体开发时间反而减少

### Q4: 测试覆盖率80%是否太高？

**A**:
- 这是行业标准，不算高
- 测试驱动开发（TDD）自然达到高覆盖率
- 高覆盖率降低线上bug
- 符合PRD-08要求

---

## 📝 变更日志

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|---------|--------|
| 2025-10-21 | 0.9.0 | **E2E 测试完成 + 性能优化**<br>- 完整产品闭环验证<br>- 去重性能提升 95%<br>- 测试执行时间提升 42%<br>- 前端认证流程改进 | Augment |
| 2025-10-21 | 0.8.0 | **P0 测试基础稳固**<br>- 修复 pytest-asyncio 冲突<br>- 优化去重性能<br>- 新增快速测试 | Augment |
| 2025-10-20 | 0.7.0 | **Phase 3 完成**<br>- 标注工作流<br>- 阈值优化<br>- 红线检查<br>- 机会报告 | Augment |
| 2025-10-18 | 0.6.0 | **Phase 2 完成**<br>- 样本守卫<br>- 关键词抓取<br>- 去重优化 | Augment |
| 2025-10-17 | 0.5.0 | **Phase 1 完成**<br>- 社区池管理<br>- 监控系统<br>- 分层调度 | Augment |
| 2025-10-16 | 0.4.0 | **Phase 0 完成**<br>- 冷热分层架构<br>- 增量抓取 | Augment |
| 2025-10-10 | 1.3.0 | 新增环境配置完全指南，完整依赖清单 | Claude |
| 2025-10-10 | 1.2.0 | 新增3人并行开发方案（12天，无Mock） | Claude |
| 2025-10-10 | 1.1.0 | 新增文档阅读指南，优化文档导航 | Claude |
| 2025-10-10 | 1.0.0 | 初始版本，创建4个核心文档 | Claude |

---

## 📄 许可证

本项目文档遵循MIT许可证。

---

## 🔗 相关链接

- **GitHub 仓库**: [namcodog/RedditSignalScanner](https://github.com/namcodog/RedditSignalScanner)
- **CI/CD 状态**: ✅ 所有检查通过（Run #64）
- **最新提交**: `ece6da36` - E2E 测试完成 + 前端改进
- **项目文档**: `.specify/specs/005-data-quality-optimization/`
- **测试报告**: `reports/phase-log/e2e-real-user-test-2025-10-21.md`
- **性能分析**: `reports/phase-log/test-performance-analysis.md`

---

**Remember**: "Talk is cheap. Show me the code." - Linus Torvalds

**We built it right! 🚀**

---

**最后更新**: 2025-10-21
**维护者**: Reddit Signal Scanner 开发团队
**当前版本**: v0.9.0 (MVP 核心功能完成)
