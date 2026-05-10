# Day 16-20 统筹规划（Lead）

日期: 2025-10-15
规划人: Lead
范围: Day 16-20 后续开发与增强事项

---

## 一、执行摘要

根据蓝图与实施检查清单，Day 14-15 已完成"测试与验收"阶段的最小闭环。Day 16-20 **不在原始 15 天蓝图范围内**，属于后续增强与优化阶段。

### 当前状态（Day 15 结束）
- ✅ Phase 0-3: 数据模型、API、分析引擎、任务系统、前端、认证、Admin 后台全部完成
- ✅ Phase 4-5: 端到端测试最小闭环通过（SSE 单测 + E2E 脚本）
- ✅ PRD-10: Excel 导入功能完成并验收通过
- ⏳ PRD-08 完整覆盖: 仍有缺口（并发/故障注入/降级一致性）
- ⏳ PRD-09: 动态社区池与预热期（未启动）

### Day 16-20 定位
- **非阻塞上线**: 当前系统已可上线运行
- **增强与优化**: 补齐 PRD-08 覆盖、实施 PRD-09、性能优化、文档完善
- **Beta 测试准备**: 为真实用户测试做准备

---

## 二、Day 16-20 任务分解

### Day 16: PRD-08 补齐（并发与故障注入）

**目标**: 补齐 PRD-08 的 P1/P2 测试用例

**任务清单**:
1. **并发测试**（Backend Agent A + QA）
   - 100 并发用户测试（目标 95% 成功率）
   - 数据库连接池压力测试
   - Redis 连接池压力测试
   - 预期产出: `backend/tests/e2e/test_concurrent_users.py`

2. **故障注入测试**（Backend Agent B + QA）
   - Redis 故障降级测试
   - 数据库故障恢复测试
   - Celery Worker 崩溃重试测试
   - 预期产出: `backend/tests/e2e/test_fault_injection_extended.py`

3. **SSE 降级一致性测试**（Frontend + Backend A）
   - SSE 连接失败自动降级到轮询
   - 降级后状态一致性验证
   - 预期产出: `frontend/src/hooks/useTaskStatus.test.ts`

**验收标准**:
- [ ] 并发测试通过（95% 成功率）
- [ ] 故障注入测试全部通过
- [ ] SSE 降级测试通过
- [ ] 测试报告记录在 `reports/phase-log/DAY16-TESTING.md`

---

### Day 17: PRD-09 实施（动态社区池 - 第一阶段）

**目标**: 实现动态社区池基础架构

**任务清单**:
1. **数据库扩展**（Backend Agent A）
   - 新增 `community_pool` 表（PRD-09 定义）
   - 新增 `community_quality_metrics` 表
   - Alembic 迁移脚本
   - 预期产出: `backend/alembic/versions/00X_community_pool.py`

2. **社区池加载服务**（Backend Agent A）
   - 实现 `CommunityPoolLoader` 服务
   - 从 Git 仓库加载初始社区列表
   - 质量评分初始化
   - 预期产出: `backend/app/services/community_pool_loader.py`

3. **Admin API 扩展**（Backend Agent B）
   - 社区池管理 API（查看/添加/禁用）
   - 质量指标查询 API
   - 预期产出: `backend/app/api/routes/admin_community_pool.py`

**验收标准**:
- [ ] 数据库迁移成功
- [ ] 社区池加载服务单测通过
- [ ] Admin API 集成测试通过
- [ ] 文档更新在 `docs/PRD/PRD-09-动态社区池与预热期实施计划.md`

---

### Day 18: PRD-09 实施（预热期与质量评分）

**目标**: 实现预热期机制与质量评分算法

**任务清单**:
1. **预热期调度器**（Backend Agent B）
   - Celery 定时任务（每日预热）
   - 预热策略实现（PRD-09 定义）
   - 预期产出: `backend/app/tasks/community_warmup_tasks.py`

2. **质量评分算法**（Backend Agent A）
   - 实现 PRD-09 定义的质量评分公式
   - 缓存命中率统计
   - 信号质量评估
   - 预期产出: `backend/app/services/community_quality_scorer.py`

3. **前端社区池管理页面**（Frontend）
   - Admin 社区池管理界面
   - 质量指标可视化
   - 预期产出: `frontend/src/pages/admin/CommunityPool.tsx`

**验收标准**:
- [ ] 预热任务调度成功
- [ ] 质量评分算法单测通过
- [ ] 前端管理页面可用
- [ ] 端到端预热流程验证通过

---

### Day 19: 性能优化与监控增强

**目标**: 性能优化与生产监控准备

**任务清单**:
1. **性能优化**（Backend Agent A）
   - 数据库查询优化（索引审查）
   - Redis 缓存策略优化
   - 分析引擎并行度调优
   - 预期产出: 性能测试报告（目标 < 4 分钟）

2. **监控增强**（Backend Agent B）
   - Prometheus metrics 导出
   - 关键指标仪表盘（Grafana）
   - 告警规则配置
   - 预期产出: `backend/app/monitoring/metrics.py`

3. **日志增强**（Backend Agent B）
   - 结构化日志（JSON 格式）
   - 关键路径日志完善
   - 错误追踪集成（Sentry）
   - 预期产出: `backend/app/core/logging.py`

**验收标准**:
- [ ] 分析耗时 < 4 分钟（90% 缓存命中）
- [ ] Prometheus metrics 可访问
- [ ] 日志结构化完成
- [ ] 监控仪表盘可用

---

### Day 20: 文档完善与 Beta 准备

**目标**: 文档完善、部署准备、Beta 测试计划

**任务清单**:
1. **文档完善**（文档维护者 + Lead）
   - 更新 README（快速开始）
   - API 文档完善（OpenAPI/Swagger）
   - 部署文档（Docker Compose + 环境变量）
   - 运维手册（日常操作 + 故障排查）
   - 预期产出: `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`

2. **部署准备**（Backend Agent B）
   - Docker Compose 配置优化
   - 环境变量模板（.env.example）
   - 健康检查端点
   - 预期产出: `docker-compose.yml`, `.env.example`

3. **Beta 测试计划**（QA + Lead）
   - Beta 用户招募计划
   - 测试用例清单
   - 反馈收集机制
   - 预期产出: `docs/BETA-TEST-PLAN.md`

4. **最终验收**（Lead）
   - PRD-01 至 PRD-10 符合度检查
   - 质量门禁最终验证
   - 上线检查清单
   - 预期产出: `reports/phase-log/DAY20-FINAL-ACCEPTANCE.md`

**验收标准**:
- [ ] 所有文档更新完成
- [ ] Docker Compose 一键启动成功
- [ ] Beta 测试计划审批通过
- [ ] 最终验收报告完成

---

## 三、资源分配与并行策略

### 人员分工
- **Backend Agent A**: Day16 并发测试 → Day17-18 PRD-09 核心实现 → Day19 性能优化
- **Backend Agent B**: Day16 故障注入 → Day17-18 PRD-09 支撑实现 → Day19-20 监控与部署
- **Frontend Agent**: Day16 SSE 降级测试 → Day18 社区池管理页面 → Day20 文档协助
- **QA Agent**: Day16 测试执行 → Day17-19 PRD-09 验证 → Day20 Beta 测试计划
- **Lead**: 全程统筹 → Day20 最终验收

### 并行节点
- Day 16: 并发测试 || 故障注入 || SSE 降级（三线并行）
- Day 17: 数据库扩展 || Admin API || 文档准备（两线并行）
- Day 18: 预热调度 || 质量评分 || 前端页面（三线并行）
- Day 19: 性能优化 || 监控增强 || 日志增强（三线并行）
- Day 20: 文档 || 部署 || Beta 计划 || 最终验收（四线并行）

---

## 四、风险与缓解

### 风险 1: PRD-09 实施复杂度高
- **缓解**: Day 17-18 分两阶段实施，优先基础架构，质量评分可后置
- **降级**: 若时间不足，Day 18 可简化为手动社区池管理，自动预热延后

### 风险 2: 性能优化可能需要架构调整
- **缓解**: Day 19 优先低风险优化（索引/缓存），架构调整需评审
- **降级**: 若无法达到 4 分钟目标，保持 5 分钟承诺即可

### 风险 3: 文档与部署准备时间不足
- **缓解**: Day 16-19 每日同步更新文档，Day 20 仅做最终审查
- **降级**: 最小化文档（README + API Docs），运维手册可后补

---

## 五、验收标准（Day 20 结束）

### 功能完整性
- [ ] PRD-01 至 PRD-08: 100% 实现
- [ ] PRD-09: 基础架构完成（预热期可选）
- [ ] PRD-10: Excel 导入已验收

### 质量指标
- [ ] mypy --strict: 0 错误
- [ ] 后端测试覆盖率: > 80%
- [ ] 前端测试覆盖率: > 70%
- [ ] E2E 测试: P0 100% 通过，P1 90% 通过

### 性能指标
- [ ] 分析耗时: < 5 分钟（90% 缓存命中）
- [ ] API 响应: < 200ms
- [ ] 并发支持: 100 用户 95% 成功率

### 文档完整性
- [ ] README 快速开始
- [ ] API 文档（Swagger）
- [ ] 部署文档
- [ ] 运维手册
- [ ] Beta 测试计划

---

## 六、下一步行动（立即执行）

1. **确认 Day 16-20 规划**（等待用户确认）
2. **分配 Day 16 任务**（并发/故障注入/SSE 降级）
3. **启动 Day 16 执行**（三线并行）

---

**备注**: 本规划基于 15 天蓝图的延伸，Day 16-20 为增强阶段，不阻塞上线。若需调整优先级或缩减范围，请及时反馈。
