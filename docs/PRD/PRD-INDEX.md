# PRD体系快速索引 - Reddit Signal Scanner

## 🧭 导航概览

**项目哲学**: 从复杂到极简的革命性重构，基于Linus Torvalds的"数据结构优先、消除特殊情况"原则。

**核心承诺**: 30秒输入，5分钟分析，找到目标客户在Reddit上的真实声音。

**系统级 PRD**：`PRD-SYSTEM.md` 为唯一总标准；各 PRD 为分模块细化说明。

## ✅ 对齐口径（PRD 为唯一标准）

> 说明：PRD 是最终标准；下列资料作为“实现事实校验源”，已反向对齐到 PRD。

- **API 实现事实**：`docs/API-REFERENCE.md`（已同步入 PRD-02）
- **报告字段口径**：PRD-02 / PRD-03 / PRD-05 / PRD-SYSTEM（含 market_health + ps_ratio 口径）
- **数据库真相**：`docs/sop/2025-12-14-database-architecture-atlas.md` + `current_schema.sql`
- **抓取真相**：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
- **清洗/打分真相**：`docs/sop/数据清洗打分规则v1.2规范.md`
- **语义库/闭环真相**：`.specify/specs/011-semantic-lexicon-development-plan.md`、`.specify/specs/016-unified-semantic-report-loop/spec.md`、`.specify/specs/016-unified-semantic-report-loop/design.md`
- **演练与故障注入**：`scripts/phase106_rehearsal_matrix.py`、`backend/tests/e2e/test_fault_injection.py`
- **执行与验收记录**：`reports/phase-log/phase106.md`、`reports/phase-log/phase107.md`、`reports/phase-log/phase108.md`、`reports/phase-log/phase109.md`、`reports/phase-log/phase110.md`、`reports/phase-log/phase111.md`、`reports/phase-log/phase112.md`、`reports/phase-log/phase113.md`、`reports/phase-log/phase114.md`
- **运行手册**：`docs/本地启动指南.md`、`docs/OPERATIONS.md`

---

## 📋 PRD文档一览表

| PRD | 标题 | 一句话总结 | 状态 | 关键输出 |
|-----|------|-----------|------|----------|
| [PRD-SYSTEM](PRD-SYSTEM.md) | 系统级 PRD | 全量系统规范与追溯矩阵 | ✅ 已同步 | 系统全貌 + 可追溯口径 |
| [PRD-01](PRD-01-数据模型.md) | 数据模型设计 | 多域数据模型（爬取/清洗/评分/事实/报告/决策单元）与 DB Atlas 对齐 | ✅ 已同步 | `users`, `tasks`, `analyses`, `reports`, `decision_units_v`, `semantic_main_view` |
| [PRD-02](PRD-02-API设计.md) | API设计规范 | 全量接口合同（黄金链路 + Admin + DecisionUnit） | ✅ 已同步 | `/api/analyze`, `/api/status/{task_id}`, `/api/tasks/{task_id}/sources`, `/api/decision-units` |
| [PRD-03](PRD-03-分析引擎.md) | 分析引擎设计 | 缓存优先 + 社区池 + facts_v2 门禁 + LLM 报告 | ✅ 已同步 | 社区发现→数据采集→信号提取→门禁→LLM 报告 |
| [PRD-04](PRD-04-任务系统.md) | 任务系统架构 | Celery 多队列 + Beat + 可靠性与预算牙齿 | ✅ 已同步 | 队列路由、重试、监控、自动补量 |
| [PRD-05](PRD-05-前端交互.md) | 前端交互设计 | 核心三页 + SSE + 报告结构标准 + DecisionUnits | ✅ 已同步 | 输入页→等待页→报告页→决策单元 |
| [PRD-06](PRD-06-用户认证.md) | 用户认证系统 | JWT 无状态认证 + Admin 鉴权 | ✅ 已同步 | `/api/auth/register`, `/api/auth/login`, `/api/auth/me` |
| [PRD-07](PRD-07-Admin后台.md) | Admin后台设计 | 候选审核/社区池/任务复盘（P0）+ 导入/调级/语义/反馈（P1） | ✅ 已同步 | `/api/admin/communities/*`, `/api/admin/tasks/*`, `/api/admin/metrics/contract-health`, `/api/admin/dashboard/stats` |
| [PRD-08](PRD-08-端到端测试规范.md) | 端到端测试规范 | 关键路径 + 故障注入 + 合同门禁 | ✅ 已同步 | E2E/性能/稳定性矩阵 |
| [PRD-09](PRD-09-动态社区池与预热期实施计划.md) | 动态社区池与预热期 | 社区池+发现+验毒+评估+调级建议 | ✅ 已同步 | `community_pool`/`discovered_communities`/`tier_suggestions` |
| [PRD-10](PRD-10-Admin社区管理Excel导入.md) | Admin Excel 导入 | 社区批量导入与追踪 | ✅ 已同步 | `/api/admin/communities/template|import|import-history` |

---

> 说明：所有 PRD 已按统一口径更新，并以本索引为唯一导航入口。

## 🔗 依赖关系DAG图

### 总体架构视图
```
Reddit Signal Scanner - PRD依赖关系图

                    ┌─────────────────┐
                    │   PRD-01 数据   │ ⭐️ ROOT
                    │   模型设计      │ [零依赖]
                    └─────────┬───────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │ PRD-02 API │  │ PRD-03 分析│  │ PRD-04 任务│
        │ 设计规范   │  │ 引擎设计   │  │ 系统架构   │
        └─────┬─────┘  └───────────┘  └─────┬─────┘
              │                             │
      ┌───────┼─────────────────────────────┼───────┐
      │       │                             │       │
┌─────▼─────┐ │                       ┌─────▼─────┐ │
│ PRD-05 前端│ │                       │ PRD-07    │ │
│ 交互设计   │ │                       │ Admin后台 │ │
└───────────┘ │                       └───────────┘ │
              │                                     │
        ┌─────▼─────┐                               │
        │ PRD-06 用户│                               │
        │ 认证系统   │                               │
        └─────┬─────┘                               │
              │                                     │
              └─────────────────┬───────────────────┘
                                │
                      ┌─────────▼──────────┐
                      │   PRD-08 端到端    │
                      │   测试规范         │ [依赖所有]
                      └────────────────────┘
```

### 详细依赖关系表

| PRD | 直接依赖 | 间接依赖 | 并行可能性 | 阻塞风险 |
|-----|---------|---------|-----------|---------|
| PRD-01 | 无 | 无 | N/A | 🔴 高风险 - 阻塞所有 |
| PRD-02 | PRD-01 | 无 | ✅ 可与03,04并行 | 🟡 中风险 - 阻塞05,06 |
| PRD-03 | PRD-01 | 无 | ✅ 可与02,04并行 | 🟢 低风险 - 仅影响分析 |
| PRD-04 | PRD-01 | 无 | ✅ 可与02,03并行 | 🟡 中风险 - 阻塞07 |
| PRD-05 | PRD-02 | PRD-01 | ❌ 需等待02完成 | 🟢 低风险 - 仅影响UI |
| PRD-06 | PRD-01,02 | 无 | ❌ 需等待01,02 | 🟡 中风险 - 阻塞认证 |
| PRD-07 | PRD-01,02,04 | 无 | ❌ 需等待多个前置 | 🟢 低风险 - 运维功能 |
| PRD-08 | ALL | ALL | ❌ 最后实施 | 🟢 低风险 - 质量保证 |
| PRD-10 | PRD-01,02,07 | 无 | ❌ 需等待 Admin 基础 | 🟢 低风险 - 运维入口 |

### 关键依赖说明

**强依赖**（必须完成前置PRD）:
- PRD-02 → PRD-01: API设计需要数据模型定义
- PRD-05 → PRD-02: 前端需要API端点规范
- PRD-06 → PRD-01,02: 用户认证需要users表和API集成
- PRD-08 → ALL: E2E测试需要完整系统

**弱依赖**（可并行开发）:
- PRD-03, PRD-04可与PRD-02并行（都基于PRD-01）
- PRD-07可在PRD-04完成后独立开发

### 🧭 PRD-代码-测试-文档矩阵

| PRD | 关键代码目录 | 核心验证命令 / 测试 | 主要参考文档 |
|-----|--------------|----------------------|--------------|
| PRD-01 数据模型 | `backend/app/models`<br>`backend/alembic/` | `pytest backend/tests/models` | `docs/sop/2025-12-14-database-architecture-atlas.md` |
| PRD-02 API 设计 | `backend/app/api/`<br>`backend/app/api/v1/` | `pytest backend/tests/api` | `docs/API-REFERENCE.md` |
| PRD-03 分析引擎 | `backend/app/services/analysis_engine.py`<br>`backend/app/services/report_service.py` | `pytest backend/tests/services` | `docs/ALGORITHM-FLOW.md` |
| PRD-04 任务系统 | `backend/app/core/celery_app.py`<br>`backend/app/tasks/` | `pytest backend/tests/tasks` | `docs/OPERATIONS.md` |
| PRD-05 前端交互 | `frontend/src/pages/`<br>`frontend/src/api/`<br>`frontend/src/router/` | `npm run test`<br>`npm run type-check` | `docs/本地启动指南.md` |
| PRD-06 用户认证 | `backend/app/api/v1/endpoints/auth.py`<br>`backend/app/core/security.py` | `pytest backend/tests/api` | `docs/2025-10-10-质量标准与门禁规范.md` |
| PRD-07 Admin 后台 | `backend/app/api/admin`<br>`backend/app/api/legacy`<br>`frontend/src/pages/admin/` | `pytest backend/tests/api` | `docs/OPERATIONS.md` |
| PRD-08 端到端测试 | `tests/`<br>`frontend/tests/`<br>`backend/tests/` | `make test-e2e` | `docs/真实Reddit-API端到端测试指南.md` |
| PRD-09 动态社区池 | `backend/app/services/discovery`<br>`backend/app/tasks/discovery` | `pytest backend/tests/services` | `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md` |
| PRD-10 Excel 导入 | `backend/app/api/legacy/admin_communities.py`<br>`backend/app/services/community_import_service.py` | `pytest backend/tests/api/test_admin_community_import.py` | `docs/PRD/PRD-10-Admin社区管理Excel导入.md` |

---

＊ 当前实现：SSE 支持 connected/progress/completed/error/heartbeat/close，`make sse-test` 可用于基础连通性验证。




＊ 阶段执行工作表已归档到 `docs/archive/2025-10-09-敏捷开发避坑与高效交付指南.md`，仅供历史追溯。

## 🚀 推荐实现顺序

### Phase 1: 数据基础 (Day 1-2)
```
1. PRD-01 数据模型设计 ⭐️ [最高优先级]
   └── 输出: 数据库表结构、索引、约束
```

### Phase 2: 核心服务 (Day 3-6) [可并行]
```
2. PRD-02 API设计规范 
   └── 输出: 4个API端点 + SSE实现

3. PRD-04 任务系统架构 [可与PRD-02并行]
   └── 输出: Celery worker + 任务调度

4. PRD-03 分析引擎设计 [需要PRD-04的任务队列]
   └── 输出: 四步分析算法
```

### Phase 3: 用户界面 (Day 7-10)
```
5. PRD-06 用户认证系统 [需要PRD-01,02]
   └── 输出: JWT认证 + 多租户

6. PRD-05 前端交互设计 [需要PRD-02,06] 
   └── 输出: React SPA三页面
```

### Phase 4: 运维管理 (Day 11-12)
```
7. PRD-07 Admin后台设计 [需要基础系统稳定]
   └── 输出: 候选审核 + 社区池管理 + 任务复盘
```

### Phase 5: 质量保证 (Day 13-15)
```
8. PRD-08 端到端测试规范 [需要完整系统]
   └── 输出: 测试套件 + 持续集成
```

---

## 🔍 快速查找索引

### 按功能模块查找

**数据层**:
- 表结构定义 → PRD-01 § 2.1
- 索引策略 → PRD-01 § 2.3  
- 多租户隔离 → PRD-01 § 2.2, PRD-06 § 2.2

**API层**:
- 端点定义 → PRD-02 § 3.1
- SSE实现 → PRD-02 § 3.2
- 错误处理 → PRD-02 § 4.2
- 认证集成 → PRD-06 § 3.3

**业务逻辑层**:
- 社区发现算法 → PRD-03 § 2.2
- 数据收集策略 → PRD-03 § 2.3  
- 分析引擎 → PRD-03 § 2.4
- 任务队列 → PRD-04 § 2.2

**用户界面层**:
- 前端路由 → PRD-05 § 2.2
- 组件设计 → PRD-05 § 2.3
- 状态管理 → PRD-05 § 2.4
- 认证流程 → PRD-06 § 3.1

### 按关键词查找

**性能相关**:
- "5分钟承诺" → PRD-03 § 1.1, PRD-08 § 2.2
- 缓存策略 → PRD-01 § 2.1, PRD-03 § 2.3
- 并发处理 → PRD-04 § 2.3, PRD-08 § 2.4
- SSE vs 轮询 → PRD-02 § 2.1, PRD-05 § 2.4

**安全相关**:
- JWT认证 → PRD-06 § 2.1
- 多租户隔离 → PRD-01 § 2.2, PRD-06 § 3.3
- 密码安全 → PRD-06 § 2.3
- API权限 → PRD-02 § 4.3

**架构相关**:
- 微服务分层 → PRD-04 § 2.1
- 数据流设计 → PRD-03 § 2.1  
- 错误处理 → PRD-02 § 4.2, PRD-04 § 3.3
- 配置管理 → PRD-07 § 2.1

### 按技术栈查找

**后端(Python)**:
- FastAPI → PRD-02, PRD-06
- Celery + Redis → PRD-04
- SQLAlchemy → PRD-01
- Transformers → PRD-03

**前端(React)**:
- 组件架构 → PRD-05 § 2.3
- 状态管理 → PRD-05 § 2.4  
- EventSource(SSE) → PRD-05 § 2.4
- JWT客户端 → PRD-06 § 3.2

**数据库**:
- PostgreSQL → PRD-01
- Redis缓存 → PRD-01 § 2.1, PRD-04 § 2.2
- 索引优化 → PRD-01 § 2.3

**运维工具**:
- Docker → PRD-07 § 3.1, PRD-08 § 3.1
- 监控 → PRD-07 § 2.2
- 日志 → PRD-07 § 2.3
- 测试 → PRD-08

---

## ⭐️ Linus审查要点汇总

### 【已解决的设计缺陷】

1. **数据结构设计** (PRD-01)
   - ✅ 四表架构消除了特殊情况
   - ✅ 用户多租户从第一天就支持
   - ✅ 索引基于真实查询模式设计

2. **API过度复杂** (PRD-02)  
   - ✅ 300次轮询 → SSE实时推送
   - ✅ 四个端点 vs 复杂的REST tree
   - ✅ 错误处理有明确降级方案

3. **分析引擎诚实性** (PRD-03)
   - ✅ 承认"5分钟承诺"基于缓存而非实时爬取
   - ✅ 缓存命中率驱动的动态策略
   - ✅ 线性流水线避免复杂依赖

4. **任务系统可靠性** (PRD-04)
   - ✅ 使用成熟的Celery而非自制轮子
   - ✅ 3次重试 + 死信队列
   - ✅ 基于CPU核心数的动态worker配置

### 【持续关注点】

1. **测试诚实性** (PRD-08)
   - ⚠️ 测试必须验证真实失败场景
   - ⚠️ 性能承诺要有量化指标
   - ⚠️ 多租户隔离的0泄露验证

2. **配置复杂度** (PRD-07)
   - ⚠️ Git配置 vs 数据库配置的一致性
   - ⚠️ 热更新的原子性保证

### 【Linus金句摘录】

> **"数据结构优先"** - PRD-01审查  
> 好的数据结构让代码自然简单，坏的数据结构让代码永远复杂。

> **"诚实的架构"** - PRD-03审查  
> 我们不是在构建能在0.1秒内分析整个Reddit的神奇系统，我们是在构建一个诚实地利用缓存的实用系统。

> **"简单胜过聪明"** - PRD-02审查  
> SSE比300次轮询简单，4个端点比复杂的REST tree简单。

> **"为失败而设计"** - PRD-04审查  
> 系统会失败，任务会失败，网络会失败。我们的代码必须优雅地处理这些失败。

---

## 🔧 实施与验收清单（以当前口径为准）

- **运行清单**：`docs/验收清单-本地环境.md`
- **端到端测试**：`docs/真实Reddit-API端到端测试指南.md`
- **质量门禁**：`docs/2025-10-10-质量标准与门禁规范.md`
- **执行记录**：`reports/phase-log/phase{N}.md`
- **PRD 对齐**：`docs/PRD/PRD-INDEX.md` + `docs/PRD/PRD-SYSTEM.md`

> 旧“Day 分阶段实施清单”已归档到 `docs/archive/2025-10-10-实施检查清单.md`。

---

## 📚 相关文档

### 核心设计文档
- [系统架构完整讲解](../系统架构完整讲解.md) - 当前架构全景
- [产品重构方案_Linus视角.md](产品重构方案_Linus视角.md) - 技术架构重构
- [PRD体系计划.md](PRD体系计划.md) - PRD撰写标准

### Linus审查报告  
- [Linus Torvalds 审查报告：PRD 4-7.md](Linus Torvalds 审查报告：PRD 4-7.md)
- [Linus Torvalds 二次审查报告.md](Linus Torvalds 二次审查报告.md)

### 项目指导文档
- [CLAUDE.md](CLAUDE.md) - 开发指导原则
- [linus的建议.md](linus的建议.md) - 技术决策指导

---

**记住Linus的话："Talk is cheap. Show me the code."**

这个索引只是开始，真正的价值在于按照这个蓝图构建出**可工作、可扩展、可维护**的系统。

**最后更新**: 2025-01-14  
**维护者**: Claude AI (基于Linus Torvalds的设计哲学)
