# Spec 007: MVP 产品闭环补全

**Status**: 🚀 Active  
**Priority**: P0 - 马上能用起来，本地稳固正常跑  
**Timeline**: 2 周（Week 1: P0, Week 2: P1）  
**Created**: 2025-10-27

---

## 📋 快速导航

- **[spec.md](./spec.md)** - 功能规格（User Stories + 验收标准）
- **[plan.md](./plan.md)** - 实施计划（技术方案 + 时间表）
- **[tasks.md](./tasks.md)** - 任务清单（81 个可执行任务）
- **[acceptance.md](./acceptance.md)** - 验收报告（执行后生成）

---

## 🎯 核心目标

**让用户用起来、本地稳固正常跑**

### 当前痛点
- ❌ 用户看不到结构化洞察（只有一堆文字）
- ❌ 无法验证证据真实性（缺少原帖链接）
- ❌ 运营无法监控质量（盲飞状态）
- ❌ API 缺少严格类型（前后端不一致）
- ❌ 本地验收流程不标准（每次手动检查）

### 解决方案
- ✅ 洞察卡片展示 + 证据验证
- ✅ 质量看板实时监控
- ✅ API 契约强制执行
- ✅ 本地验收流程标准化
- ✅ 阈值校准 + 实体词典 + 报告行动位

---

## 📊 User Stories 优先级

### Week 1: P0 功能（本地稳固可用）

| ID | User Story | 验收标准 | 预计时间 |
|----|-----------|---------|---------|
| US1 | 洞察卡片展示与证据验证 | 用户能点击卡片查看证据 | 2 天 |
| US2 | 质量看板实时监控 | 运营能看到实时指标 | 1 天 |
| US3 | API 契约强制执行 | CI 自动检测 breaking changes | 1 天 |
| US4 | 本地验收流程标准化 | `make local-acceptance` 通过 | 1 天 |

### Week 2: P1 功能（数据质量提升）

| ID | User Story | 验收标准 | 预计时间 |
|----|-----------|---------|---------|
| US5 | 阈值校准与数据质量提升 | Precision@50 ≥ 0.6 | 2 天 |
| US6 | 实体词典 v0 与报告行动位 | 识别 50 个核心实体 | 2 天 |

---

## 🚀 快速开始

### 1. 查看任务清单

```bash
cat .specify/specs/007-mvp-product-loop/tasks.md
```

### 2. 开始执行（按 Phase 顺序）

```bash
# Phase 1: Setup
mkdir -p data/annotations reports/local-acceptance reports/threshold-calibration

# Phase 2: Foundational
cd backend
make db-migrate MESSAGE="add action items to analysis"
cd ../frontend
npm install recharts

# Phase 3-8: 按 tasks.md 执行
# ...
```

### 3. 验收测试

```bash
# Week 1 验收（P0 功能）
make dev-golden-path          # 启动所有服务
make local-acceptance         # 运行验收测试

# Week 2 验收（P1 功能）
cd backend
python scripts/calibrate_threshold.py  # 阈值校准
pytest tests/services/test_entity_matcher.py  # 实体匹配测试
```

---

## 📁 新增文件清单

### 后端（Backend）

```
backend/
├── app/
│   ├── api/routes/
│   │   ├── insights.py          # 新增
│   │   └── metrics.py           # 新增
│   ├── schemas/
│   │   ├── insight.py           # 新增
│   │   └── metrics.py           # 新增
│   ├── services/
│   │   ├── insight_service.py   # 新增
│   │   ├── metrics_service.py   # 新增
│   │   └── analysis/
│   │       └── entity_matcher.py # 新增
├── config/
│   └── entity_dictionary.yaml   # 新增
├── scripts/
│   ├── calibrate_threshold.py   # 新增
│   └── local_acceptance.py      # 新增
└── tests/
    ├── api/
    │   ├── test_insights.py     # 新增
    │   └── test_metrics.py      # 新增
    └── services/
        └── test_entity_matcher.py # 新增
```

### 前端（Frontend）

```
frontend/
├── src/
│   ├── pages/
│   │   ├── InsightsPage.tsx     # 新增
│   │   └── DashboardPage.tsx    # 新增
│   ├── components/
│   │   ├── InsightCard.tsx      # 新增
│   │   ├── EvidenceList.tsx     # 新增
│   │   ├── MetricsChart.tsx     # 新增
│   │   └── ActionItems.tsx      # 新增
│   ├── api/
│   │   ├── insights.ts          # 新增
│   │   └── metrics.ts           # 新增
│   └── types/
│       ├── insight.ts           # 新增
│       └── metrics.ts           # 新增
```

### 数据与报告

```
data/
└── annotations/
    └── sample_200.csv           # 新增

reports/
├── local-acceptance/            # 新增目录
└── threshold-calibration/       # 新增目录
```

---

## ✅ 验收标准

### Week 1 验收（P0）

- [ ] 用户能在报告页面看到洞察卡片列表
- [ ] 点击卡片可展开查看证据段落
- [ ] 每条证据都有原帖链接和时间戳
- [ ] 运营能在质量看板查看实时指标
- [ ] 质量看板 5 秒内刷新趋势图
- [ ] CI 中自动检测 API breaking changes
- [ ] 运行 `make local-acceptance` 所有测试通过

### Week 2 验收（P1）

- [ ] Precision@50 ≥ 0.6
- [ ] 报告中能识别 50 个核心实体
- [ ] 报告新增行动位字段（问题定义、建议动作、置信度、优先级）
- [ ] 前端高亮显示实体和行动建议

### 最终验收（2 周后）

- [ ] 运行 `make dev-golden-path` 所有服务启动成功
- [ ] 运行 `make local-acceptance` 所有测试通过
- [ ] 生成验收报告到 `reports/local-acceptance/final.md`
- [ ] 产品经理能独立使用产品（注册 → 分析 → 查看洞察 → 导出）

---

## 📝 进度追踪

### Week 1 进度

- [ ] Day 1-2: US1 洞察卡片（后端 + 前端）
- [ ] Day 3: US2 质量看板
- [ ] Day 4: US3 API 契约化
- [ ] Day 5: US4 本地验收流程

### Week 2 进度

- [ ] Day 6-7: US5 阈值校准
- [ ] Day 8: US6 实体词典
- [ ] Day 9-10: US6 报告行动位

---

## 🔗 相关文档

- **PRD**: `docs/PRD/PRD-INDEX.md`
- **架构**: `docs/PRD/ARCHITECTURE.md`
- **API 参考**: `docs/API-REFERENCE.md`
- **本地运行**: `docs/handbook/本地运行验收执行方案-2025-10-07.md`
- **质量标准**: `docs/2025-10-10-质量标准与门禁规范.md`

---

## 🚨 注意事项

1. **按 Phase 顺序执行**：Phase 2 完成前，所有 User Story 无法开始
2. **每完成一个 User Story，立即验收**：不要等到最后一起测试
3. **遇到阻塞立即记录**：记录到 `reports/blockers.md`
4. **所有配置文件纳入版本控制**：`entity_dictionary.yaml`、`scoring_rules.yaml`
5. **每天结束前提交代码**：确保进度可追溯

---

## 📞 联系方式

- **Spec 负责人**: [待填写]
- **技术负责人**: [待填写]
- **产品负责人**: [待填写]

---

**最后更新**: 2025-10-27  
**下次检查**: Week 1 结束（2025-11-03）

