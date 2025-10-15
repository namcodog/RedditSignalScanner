# Reddit Signal Scanner - 0-1重写项目文档

> **项目状态**: 📋 规划阶段
> **创建日期**: 2025-10-10
> **目标工期**: 15天
> **质量承诺**: 100% PRD符合度 + Linus设计哲学 + 类型安全零容忍

---

## 🎯 项目概述

Reddit Signal Scanner是一个智能商业洞察工具，帮助产品创始人从Reddit讨论中快速发现：
- 🎯 用户痛点（Pain Points）
- 🏢 竞品分析（Competitors）
- 💡 商业机会（Opportunities）

**核心承诺**: 30秒输入，5分钟分析，找到目标客户的真实声音。

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
| `make db-upgrade` | 升级数据库到最新版本 |
| `make clean` | 清理所有生成文件 |
| `make deploy-checklist` | （待实现）部署前Checklist占位 |

> **部署 / 运维**：生产部署步骤详见 `docs/DEPLOYMENT.md`；日常监控、故障排查和备份请参考 `docs/OPERATIONS.md`。

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
| Day 0 | 环境准备完成 | 开发环境 + 工具链 | ✅ 完成 |
| Day 1 | 数据模型完成 | 4表架构 + 迁移脚本 | ✅ 完成 |
| Day 2 | API层开始 | 任务创建端点 | ⏳ 进行中 |
| Day 5 | API层完成 | 4个核心端点 + SSE | ⏳ 待开始 |
| Day 8 | 分析引擎完成 | 4步流水线 | ⏳ 待开始 |
| Day 11 | 前端完成 | 3页面SPA | ⏳ 待开始 |
| Day 13 | 运维管理完成 | Admin后台 | ⏳ 待开始 |
| Day 15 | 最终验收 | 完整MVP + 文档 | ⏳ 待开始 |

---

## ✅ 最终验收标准

### 功能完整性
- [ ] PRD-01: 数据模型 100%实现
- [ ] PRD-02: API设计 100%实现
- [ ] PRD-03: 分析引擎 100%实现
- [ ] PRD-04: 任务系统 100%实现
- [ ] PRD-05: 前端交互 100%实现
- [ ] PRD-06: 用户认证 100%实现
- [ ] PRD-07: Admin后台 100%实现
- [ ] PRD-08: 测试规范 100%实现

### 质量指标
- [ ] mypy --strict: **0错误**
- [ ] 后端测试覆盖率: **>80%**
- [ ] 前端测试覆盖率: **>70%**
- [ ] API响应时间: **<200ms**
- [ ] 分析完成时间: **<300s**
- [ ] 无 `# type: ignore`
- [ ] 无 `Any` 类型
- [ ] 无 `Dict[str, Any]`

### 文档完整性
- [ ] README.md
- [ ] API文档（OpenAPI）
- [ ] 部署文档
- [ ] 维护手册
- [ ] 所有ADR记录

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
| 2025-10-10 | 1.3.0 | 新增环境配置完全指南，完整依赖清单 | Claude |
| 2025-10-10 | 1.2.0 | 新增3人并行开发方案（12天，无Mock） | Claude |
| 2025-10-10 | 1.1.0 | 新增文档阅读指南，优化文档导航 | Claude |
| 2025-10-10 | 1.0.0 | 初始版本，创建4个核心文档 | Claude |

---

## 📄 许可证

本项目文档遵循MIT许可证。

---

**Remember**: "Talk is cheap. Show me the code." - Linus Torvalds

**Let's build it right! 🚀**

---

最后更新: 2025-10-10
维护者: Reddit Signal Scanner 开发团队
