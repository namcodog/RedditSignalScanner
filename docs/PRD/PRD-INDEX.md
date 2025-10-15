# PRD体系快速索引 - Reddit Signal Scanner

## 🧭 导航概览

**项目哲学**: 从复杂到极简的革命性重构，基于Linus Torvalds的"数据结构优先、消除特殊情况"原则。

**核心承诺**: 30秒输入，5分钟分析，找到目标客户在Reddit上的真实声音。

---

## 📋 PRD文档一览表

| PRD | 标题 | 一句话总结 | 状态 | 关键输出 |
|-----|------|-----------|------|----------|
| [PRD-01](PRD-01-数据模型.md) | 数据模型设计 | 四表架构支撑多租户+缓存的数据基础 | ✅ Linus审查通过 | `users`, `tasks`, `analysis`, `subreddit_cache` |
| [PRD-02](PRD-02-API设计.md) | API设计规范 | 四端点架构：SSE实时推送替代轮询 | ✅ Linus审查通过 | `/api/analyze`, `/api/stream/{task_id}` |
| [PRD-03](PRD-03-分析引擎.md) | 分析引擎设计 | 四步分析流水线：缓存优先的智能处理 | ✅ 已更新（动态社区池） | 社区发现→数据收集→智能分析→报告生成 |
| [PRD-04](PRD-04-任务系统.md) | 任务系统架构 | Celery+Redis解耦HTTP层与分析引擎 | ✅ Linus审查通过 | 生产者-消费者模式，3次重试机制 |
| [PRD-05](PRD-05-前端交互.md) | 前端交互设计 | 三页面React SPA：极简用户旅程 | ✅ Linus审查通过 | 输入页→等待页→报告页 |
| [PRD-06](PRD-06-用户认证.md) | 用户认证系统 | JWT无状态认证+多租户数据隔离 | ✅ Linus审查通过 | 注册、登录、租户隔离API |
| [PRD-07](PRD-07-Admin后台.md) | Admin后台设计 | 只读监控+Git配置的运维界面 | ✅ Linus审查通过 | 系统监控、配置管理、日志查看 |
| [PRD-08](PRD-08-端到端测试规范.md) | 端到端测试规范 | 四层测试金字塔：故障优先的质量保证 | ✅ Linus审查通过 | 关键路径、故障注入、性能边界测试 |
| [PRD-09](PRD-09-动态社区池与预热期实施计划.md) | 动态社区池与预热期 | 四层社区池架构：自我进化的智能系统 | ✅ 已确认 | 种子社区→自动发现→用户反馈→Admin添加 |

---

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
| PRD-01 数据模型 | `backend/app/models`<br>`backend/app/schemas`<br>`backend/alembic/` | `pytest backend/tests/test_database_schema.py`<br>`make backend-smoke` | `docs/strategy/代码库完整性分析报告-2025-09-26.md`<br>`docs/standards/测试架构设计文档.md` |
| PRD-02 API 设计 | `backend/app/api/v1`<br>`backend/app/core/sse.py`<br>`backend/app/services/task_producer.py` | `pytest backend/tests/test_feedback_events_api.py`<br>`make sse-test`＊ | `docs/standards/API响应统一规范.md`<br>`docs/handbook/本地运行验收执行方案-2025-10-07.md` |
| PRD-03 分析引擎 | `backend/app/services/analysis_engine.py`<br>`backend/app/algorithms/` | `pytest backend/tests/test_analysis_tasks.py`<br>`pytest backend/tests/test_analysis_model.py` | `docs/strategy/8.25-prd03-02架构分析技术方案.md`<br>`docs/strategy/技术债务全面评估报告-2025年9月13日.md` |
| PRD-04 任务系统 | `backend/app/tasks/`<br>`backend/app/services/task_monitor.py`<br>`backend/app/core/` | `pytest backend/tests/test_task_integration.py`<br>`pytest backend/tests/test_retry_mechanism.py` | `docs/strategy/系统级重构方案-黄金路径稳定化与可中断超时.md`<br>`docs/handbook/运维手册-日常起停与验收.md` |
| PRD-05 前端交互 | `frontend/src/pages/`<br>`frontend/src/components/`<br>`frontend/src/services/` | `npm run test`<br>`npm run type-check` | `docs/strategy/reddit_v0_layout_spec.md`<br>`docs/handbook/前端像素级还原强执行计划.md` |
| PRD-06 用户认证 | `backend/app/api/v1/endpoints/auth.py`<br>`backend/app/services/auth_service.py`<br>`frontend/src/services/auth.service.ts` | `pytest backend/tests/test_jwt_auth.py`<br>`pytest backend/tests/test_v0_auth_integration.py` | `docs/strategy/2025-09-23-前端后端状态管理修复方案.md`<br>`docs/standards/PRD实施计划_基于依赖关系.md` |
| PRD-07 Admin 后台 | `backend/app/api/v1/endpoints/admin_*`<br>`backend/app/services/admin/`<br>`frontend/src/pages/admin/` | `pytest backend/tests/test_task_monitoring.py`<br>`pytest backend/tests/test_feedback_events_api.py` | `docs/strategy/backend_state_management_priorities.md`<br>`docs/handbook/运维手册-日常起停与验收.md` |
| PRD-08 端到端测试 | `tests/`<br>`backend/tests/integration/`<br>`frontend/tests/` | `make quick-gate-local`<br>`make openapi-check-stream`＊<br>`pytest backend/tests/services/test_signal_to_report_integration.py::test_signal_to_report_chain_builds_consistent_report -q` | `docs/standards/QUALITY-GATE-RULES.md`<br>`docs/handbook/本地运行验收执行方案-2025-10-07.md` |

---

＊ 当前实现：SSE 测试端点仅发送 connected + 心跳，需要后端补齐完成事件；如需继续开发，可先使用 `make sse-test` 观察警告。OpenAPI 校验在无默认 token 时会返回 401/timeout，可临时设置 `RSS_ALLOW_OPENAPI_MISMATCH=1`，待 PRD-08 实施阶段补上鉴权方案。




＊ 阶段执行工作表见《2025-10-09 敏捷开发避坑与高效交付指南》第7章，包含命令与依赖注意事项。

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
   └── 输出: 只读监控界面
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

## 🔧 实施检查清单

### Day 1-2: 数据基础
- [ ] PRD-01实施完成：数据库表创建+索引
- [ ] 多租户隔离验证：跨租户查询返回空结果  
- [ ] 缓存表设计：24小时TTL自动清理

### Day 3-6: 核心服务  
- [ ] PRD-02实施：4个API端点 + SSE
- [ ] PRD-04实施：Celery worker + 队列
- [ ] PRD-03实施：四步分析算法
- [ ] 5分钟承诺验证：缓存命中率>80%场景

### Day 7-10: 用户界面
- [ ] PRD-06实施：JWT认证 + 用户注册
- [ ] PRD-05实施：React SPA + SSE客户端  
- [ ] 端到端测试：注册→分析→报告完整流程

### Day 11-12: 运维管理
- [ ] PRD-07实施：只读Admin界面
- [ ] 配置热更新验证：运行任务不受影响

### Day 13-15: 质量保证
- [ ] PRD-08实施：测试套件 + CI/CD
- [ ] 故障注入测试：Redis宕机恢复
- [ ] 性能边界测试：100并发用户

---

## 📚 相关文档

### 核心设计文档
- [Reddit 商业信号扫描器.md](Reddit 商业信号扫描器.md) - 完整产品蓝图
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
