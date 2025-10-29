# Reddit Signal Scanner 项目优化重构

**创建日期**: 2025-10-21  
**状态**: Draft  
**负责人**: Tech Lead + PM

---

## 📋 文档索引

- **[spec.md](./spec.md)**: 功能规格说明（12 个用户故事，P0-P2 优先级）
- **[plan.md](./plan.md)**: 实施计划（技术上下文、架构设计、API 契约）
- **[tasks.md](./tasks.md)**: 任务清单（60 个任务，按里程碑和用户故事组织）
- **[risk-register.md](./risk-register.md)**: 风险台账（技术风险、进度风险、缓解措施）

---

## 🎯 项目目标

**把"从 Reddit 抓信号 → 去噪与结构化 → 生成可交易的洞察"做成稳定流水线，并形成可交付的洞察卡片与导出能力。**

### 版本规划

| 里程碑 | 时间 | 目标 | 关键成果 |
|--------|------|------|----------|
| **M0** | 1 周 | 清理技术债务、上线最小可用产品 | 仓库瘦身、质量看板 v0、洞察卡片 v0、CSV 导出 |
| **M1** | 1 个月 | 产品闭环 + 质量提升 | 去重二级化、API 契约化、成本优化、PPT/Notion 导出、NER v1 |
| **M2** | 1 季度 | 高级功能 + 优化 | 趋势分析 v1、竞品雷达、主动学习闭环 |

---

## 🚀 快速开始

### M0（1 周）执行清单

#### Day 1-2: 仓库清理与 CI 优化
```bash
# 1. 创建清理脚本
cd backend/scripts
cat > cleanup_repo.sh << 'EOF'
#!/bin/bash
echo "清理前仓库体积: $(du -sh ../../ | cut -f1)"
rm -rf ../../node_modules ../../venv
find ../.. -type d -name "__pycache__" -exec rm -rf {} +
find ../.. -type d -name ".pytest_cache" -exec rm -rf {} +
find ../.. -type d -name ".mypy_cache" -exec rm -rf {} +
echo "清理后仓库体积: $(du -sh ../../ | cut -f1)"
EOF
chmod +x cleanup_repo.sh

# 2. 执行清理
./cleanup_repo.sh

# 3. 更新 .gitignore
cat >> ../../.gitignore << 'EOF'
# 依赖目录
node_modules/
venv/
__pycache__/
.pytest_cache/
.mypy_cache/

# Python 编译文件
*.pyc
*.pyo
*.pyd
.Python

# E2E 失败快照
reports/failed_e2e/
EOF

# 4. 提交
git add .gitignore
git commit -m "chore: 清理依赖目录并更新 .gitignore"
```

#### Day 3-4: 最小质量看板 v0
```bash
# 1. 创建数据库迁移
cd backend
alembic revision -m "add_quality_metrics_table"

# 2. 运行迁移
alembic upgrade head

# 3. 启动后端服务
make dev-backend

# 4. 访问质量看板
# http://localhost:8006/api/metrics
```

#### Day 5-6: 洞察卡片 v0
```bash
# 1. 创建数据库迁移
alembic revision -m "add_insight_card_table"

# 2. 运行迁移
alembic upgrade head

# 3. 访问洞察列表
# http://localhost:3006/insights
```

#### Day 7: E2E 收敛 + CSV 导出
```bash
# 1. 运行 E2E 测试
make test-e2e

# 2. 验证时间 ≤ 5 分钟
# 3. 测试 CSV 导出
# http://localhost:3006/report/{task_id} -> 点击"导出 CSV"
```

---

## 📊 成功标准

### M0 验收标准（1 周）

- [ ] **仓库瘦身**: 体积下降 ≥ 50%
- [ ] **CI 优化**: 安装时长下降 ≥ 40%（从 5 分钟降至 3 分钟）
- [ ] **质量看板**: 可访问 `/metrics` 页面，展示采集成功率、重复率、处理耗时
- [ ] **洞察卡片**: 可浏览洞察列表，点击展开证据段落
- [ ] **E2E 测试**: `make test-e2e` ≤ 5 分钟
- [ ] **CSV 导出**: 可下载 CSV 文件，可在 Excel 中打开

### M1 验收标准（1 个月）

- [ ] **去重优化**: 重复率下降 ≥ 30%，主题簇纯度 ≥ 0.75
- [ ] **API 契约**: 前端无手写类型，字段拼写错误在编译期失败
- [ ] **成本优化**: 单条洞察成本下降 ≥ 30%，缓存命中率 ≥ 60%
- [ ] **导出完整**: PPT 和 Notion 导出可用
- [ ] **NER v1**: F1 ≥ 0.75，实体在卡片中高亮渲染
- [ ] **质量看板 v1**: 支持可配置指标和时间窗

### M2 验收标准（1 季度）

- [ ] **趋势分析**: 可识别新兴主题（增长率 > 50%）
- [ ] **竞品雷达**: 可生成雷达图，支持多社区对比
- [ ] **主动学习**: 闭环运转，每周新增 ≥ 200 条标注样本

---

## 🎯 高层 OKR

### O1: 数据质量
- **KR1**: 重复率 ≤ 8%
- **KR2**: 采集成功率 ≥ 98%
- **KR3**: 证据可读性评分 ≥ 4/5

### O2: 洞察价值
- **KR1**: 洞察审阅通过率 ≥ 70%
- **KR2**: Top10 机会卡片每周可被复用于评审会

### O3: 成本与效率
- **KR1**: 单条洞察成本下降 30%
- **KR2**: P95 端到端耗时 ≤ 5 分钟

---

## 📈 进度跟踪

### Week 1（M0）
- [x] Day 1-2: 仓库清理与 CI 优化
- [ ] Day 3-4: 最小质量看板 v0
- [ ] Day 5-6: 洞察卡片 v0
- [ ] Day 7: E2E 收敛 + CSV 导出

### Week 2-5（M1）
- [ ] Week 2: API 契约化 + 成本优化
- [ ] Week 3: 导出完整版（PPT/Notion）
- [ ] Week 4: 去重二级化 + 质量看板 v1
- [ ] Week 5: NER v1

### Month 2-3（M2）
- [ ] Month 2: 趋势分析 v1
- [ ] Month 3: 竞品雷达 + 主动学习闭环

---

## 🔧 技术栈

### 后端
- **语言**: Python 3.11
- **框架**: FastAPI, Celery, SQLAlchemy 2.0
- **数据库**: PostgreSQL, Redis
- **测试**: pytest, mypy
- **新增依赖**:
  - `datasketch` (MinHash 去重)
  - `simhash` (SimHash 去重)
  - `scikit-learn` (主题聚类)
  - `python-pptx` (PPT 导出)
  - `notion-client` (Notion 导出)

### 前端
- **语言**: TypeScript 5.x
- **框架**: React 18, Vite
- **测试**: vitest, Playwright
- **新增依赖**:
  - `openapi-typescript` (API 类型生成)
  - `recharts` (图表可视化)

---

## 📚 相关文档

### 项目文档
- [README.md](../../../README.md): 项目总览
- [docs/系统架构完整讲解.md](../../../docs/系统架构完整讲解.md): 系统架构详解
- [docs/分析算法设计详解.md](../../../docs/分析算法设计详解.md): 分析算法详解

### PRD 文档
- [PRD/PRD-INDEX.md](../../../PRD/PRD-INDEX.md): PRD 索引
- [docs/2025-10-10-实施检查清单.md](../../../docs/2025-10-10-实施检查清单.md): 实施检查清单

### 历史记录
- [reports/phase-log/](../../../reports/phase-log/): 阶段日志
- [reports/phase-log/e2e-real-user-test-2025-10-21.md](../../../reports/phase-log/e2e-real-user-test-2025-10-21.md): E2E 测试报告

---

## 🚨 风险与缓解

详见 [risk-register.md](./risk-register.md)

### 高优先级风险

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 依赖目录入库导致仓库膨胀 | 🔴 高 | **立即执行**: 移除 node_modules/venv，CI 缓存 |
| NER F1 < 0.75 | 🔴 高 | 准备 Plan B（纯规则方法），降低目标到 0.65 |
| M0 超期 | 🟡 中 | 砍掉 CSV 导出，放到 M1 |

---

## 👥 角色与分工（RACI）

| 角色 | 职责 | 负责任务 |
|------|------|----------|
| **Tech Lead (TL)** | 架构决策、性能与安全把关 | R/A: 所有技术决策 |
| **Backend** | 数据采集、管道、API | R: T001-T051（后端任务） |
| **Data/ML** | 去重/聚类、NER、趋势、评测 | R: T036-T060（算法任务） |
| **Frontend** | 洞察卡片、看板、导出 | R: T008-T051（前端任务） |
| **PM** | 需求优先级、验收标准、里程碑与节奏 | A/C: 所有用户故事 |
| **Ops（运营/分析）** | 数据源维护、标注与质检、周报与内测运营 | R/C: T044（标注集准备） |
| **QA** | 测试策略与 E2E 质量 | R: T016-T019（E2E 测试） |

---

## 📞 联系方式

- **Tech Lead**: [待填写]
- **PM**: [待填写]
- **Slack Channel**: #reddit-signal-scanner
- **Weekly Sync**: 每周一 10:00 AM

---

## 📝 更新日志

### 2025-10-21
- ✅ 创建项目优化重构规划
- ✅ 完成 spec.md、plan.md、tasks.md
- ✅ 定义 12 个用户故事（P0-P2）
- ✅ 分解 60 个任务（M0-M2）
- ⏳ 待执行：仓库清理（Day 1-2）

---

**下一步行动**: 执行 Day 1-2 任务（仓库清理与 CI 优化）

