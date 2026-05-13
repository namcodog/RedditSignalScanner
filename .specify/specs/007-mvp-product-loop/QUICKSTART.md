# 快速开始：007-mvp-product-loop

**目标**: 2 周内完成 MVP 产品闭环，让用户用起来，本地稳固正常跑

---

## 🚀 立即开始（5 分钟）

### 1. 查看完整计划

```bash
cd .specify/specs/007-mvp-product-loop

# 查看功能规格
cat spec.md

# 查看实施计划
cat plan.md

# 查看任务清单
cat tasks.md
```

### 2. 创建工作分支

```bash
git checkout -b 007-mvp-product-loop
```

### 3. 开始执行

按照 `tasks.md` 的 Phase 顺序执行，从 Phase 1 开始。

---

## 📋 Week 1 执行清单（P0 功能）

### Day 1-2: 洞察卡片（US1）

**目标**: 用户能看到结构化洞察卡片并点击查看证据

#### 后端任务（6h）

```bash
cd backend

# T010: 创建 InsightCard schema
cat > app/schemas/insight.py << 'EOF'
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class Evidence(BaseModel):
    post_id: str
    post_url: str
    excerpt: str
    timestamp: datetime
    subreddit: str

class InsightCard(BaseModel):
    id: str
    title: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    time_window: str
    evidence: List[Evidence]
EOF

# T011: 创建 InsightService
touch app/services/insight_service.py
# [实现从 Analysis 提取洞察的逻辑]

# T012: 创建 insights API 路由
touch app/api/routes/insights.py
# [实现 GET /api/insights/{task_id}]

# T013: 创建测试
touch tests/api/test_insights.py
# [实现 API 测试]

# 运行测试
pytest tests/api/test_insights.py -v
```

#### 前端任务（6h）

```bash
cd frontend

# T014: 创建类型定义
mkdir -p src/types
cat > src/types/insight.ts << 'EOF'
export interface Evidence {
  post_id: string;
  post_url: string;
  excerpt: string;
  timestamp: string;
  subreddit: string;
}

export interface InsightCard {
  id: string;
  title: string;
  summary: string;
  confidence: number;
  time_window: string;
  evidence: Evidence[];
}
EOF

# T015: 创建 API 客户端
mkdir -p src/api
touch src/api/insights.ts
# [实现 API 调用]

# T016-T018: 创建组件和页面
mkdir -p src/components src/pages
touch src/components/InsightCard.tsx
touch src/components/EvidenceList.tsx
touch src/pages/InsightsPage.tsx

# T019: 更新路由
# 编辑 src/App.tsx，新增 /insights/:taskId 路由

# 类型检查
npm run type-check
```

#### 验收测试（2h）

```bash
# 启动服务
make dev-golden-path

# 手动测试
# 1. 创建分析任务
# 2. 访问 http://localhost:3006/insights/{taskId}
# 3. 点击洞察卡片
# 4. 验证证据链
# 5. 点击原帖链接

# 记录结果
mkdir -p reports/local-acceptance
cat > reports/local-acceptance/us1-insights.md << 'EOF'
# US1 验收报告

**日期**: $(date +%Y-%m-%d)
**状态**: [ ] 通过 / [ ] 失败

## 测试结果
- [ ] 洞察卡片列表正常展示
- [ ] 点击卡片能展开证据
- [ ] 证据包含原帖链接
- [ ] 点击链接能打开 Reddit

## 问题记录
[如有问题，详细描述]
EOF
```

---

### Day 3: 质量看板（US2）

**目标**: 运营能看到实时质量指标

#### 后端任务（3h）

```bash
cd backend

# T023: 创建 DailyMetrics schema
cat > app/schemas/metrics.py << 'EOF'
from pydantic import BaseModel
from datetime import date

class DailyMetrics(BaseModel):
    date: date
    cache_hit_rate: float
    duplicate_rate: float
    processing_time_p50: float
    processing_time_p95: float
EOF

# T024: 创建 MetricsService（复用现有指标）
touch app/services/metrics_service.py

# T025: 创建 metrics API 路由
touch app/api/routes/metrics.py

# T026: 创建测试
touch tests/api/test_metrics.py
pytest tests/api/test_metrics.py -v
```

#### 前端任务（5h）

```bash
cd frontend

# T027: 安装 recharts
npm install recharts

# T028-T030: 创建组件和页面
touch src/types/metrics.ts
touch src/api/metrics.ts
touch src/components/MetricsChart.tsx
touch src/pages/DashboardPage.tsx

# T031: 更新路由
# 编辑 src/App.tsx，新增 /dashboard 路由

npm run type-check
```

---

### Day 4: API 契约化（US3）

**目标**: 所有 API 有严格类型，CI 自动检测 breaking changes

```bash
cd backend

# T035-T037: 审查所有 API 端点
grep -r "async def" app/api/routes/ | grep -v "response_model"
# [确保所有端点都有 response_model]

# T038: 新增 ActionItem schema
# 编辑 app/schemas/report_payload.py

# T039: 更新 OpenAPI baseline
make update-api-schema

# T040: 修改 CI 配置
# 编辑 .github/workflows/ci.yml，新增 make test-contract

# T041: 测试 breaking change 检测
# 故意修改一个字段 → 提交 → 验证 CI 失败

# T042: 运行契约测试
make test-contract
```

---

### Day 5: 本地验收流程（US4）

**目标**: 一键启动所有服务，自动验收核心功能

```bash
# T044: 创建验收脚本
cat > backend/scripts/seed/local_acceptance.py << 'EOF'
#!/usr/bin/env python3
"""本地验收测试脚本"""
import asyncio
import httpx

async def test_registration():
    """测试注册功能"""
    # [实现]
    pass

async def test_login():
    """测试登录功能"""
    # [实现]
    pass

async def test_analysis():
    """测试分析功能"""
    # [实现]
    pass

async def main():
    print("🚀 开始本地验收测试...")
    await test_registration()
    await test_login()
    await test_analysis()
    print("✅ 所有测试通过！")

if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x backend/scripts/seed/local_acceptance.py

# T045: 新增 Makefile 命令
cat >> Makefile << 'EOF'

local-acceptance: ## 运行本地验收测试
	@echo "==> Running local acceptance tests ..."
	cd backend && python scripts/seed/local_acceptance.py
EOF

# T047: 优化 dev-golden-path
# 编辑 Makefile，确保所有服务稳定启动

# T049-T051: 验收测试
make dev-golden-path
make local-acceptance
```

---

## 📋 Week 2 执行清单（P1 功能）

### Day 6-7: 阈值校准（US5）

```bash
# T052: 抽样 200 条帖子
cd backend
python -c "
from app.db.session import SessionFactory
from app.models.posts_storage import PostHot
import asyncio
import csv

async def sample_posts():
    async with SessionFactory() as db:
        result = await db.execute('SELECT * FROM posts_hot ORDER BY RANDOM() LIMIT 200')
        posts = result.fetchall()
        
        with open('../data/annotations/sample_200.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['post_id', 'title', 'summary', 'label', 'strength'])
            for post in posts:
                writer.writerow([post.id, post.title, post.summary, '', ''])

asyncio.run(sample_posts())
"

# T053-T054: 人工标注（6h）
# 打开 data/annotations/sample_200.csv
# 标注：label (机会/非机会), strength (强/中/弱)

# T056-T059: 创建校准脚本
cat > backend/scripts/calibrate_threshold.py << 'EOF'
#!/usr/bin/env python3
"""阈值校准脚本"""
import pandas as pd
import numpy as np

def calculate_precision_at_k(predictions, labels, k=50):
    """计算 Precision@K"""
    # [实现]
    pass

def grid_search_threshold():
    """网格搜索最优阈值"""
    df = pd.read_csv('../data/annotations/sample_200.csv')
    # [实现网格搜索]
    pass

if __name__ == "__main__":
    grid_search_threshold()
EOF

# T060-T062: 运行校准
python backend/scripts/calibrate_threshold.py
```

### Day 8-10: 实体词典 + 报告行动位（US6）

```bash
# T063-T064: 手写实体词典
cat > backend/config/entity_dictionary.yaml << 'EOF'
brands:
  - Notion
  - Slack
  - Asana
  - Trello
  - Monday.com

features:
  - 协作
  - 自动化
  - 集成
  - 模板
  - 工作流

pain_points:
  - 效率低
  - 成本高
  - 学习曲线陡
  - 缺少集成
  - 数据孤岛
EOF

# T065-T067: 创建实体匹配服务
touch backend/app/services/analysis/entity_matcher.py
touch backend/tests/services/test_entity_matcher.py

# T068-T071: 报告行动位强化
# 编辑 backend/app/services/analysis_engine.py
# 编辑 backend/app/api/routes/reports.py
# 创建 frontend/src/components/ActionItems.tsx
# 编辑 frontend/src/pages/ReportPage.tsx

# T072-T075: 验收测试
pytest backend/tests/services/test_entity_matcher.py -v
```

---

## ✅ 每日检查清单

### 每天开始前

- [ ] 拉取最新代码：`git pull origin main`
- [ ] 查看今日任务：`cat .specify/specs/007-mvp-product-loop/tasks.md`
- [ ] 启动服务：`make dev-golden-path`

### 每天结束前

- [ ] 运行测试：`make test-backend && make test-frontend`
- [ ] 代码格式化：`cd backend && black . && isort .`
- [ ] 类型检查：`cd frontend && npm run type-check`
- [ ] 提交代码：`git add . && git commit -m "feat(007): [描述]"`
- [ ] 更新进度：编辑 `README.md` 的进度追踪部分

---

## 🚨 遇到问题怎么办？

### 1. 记录到 blockers.md

```bash
cat >> reports/blockers.md << 'EOF'
## [日期] - [问题简述]

**影响 User Story**: US1/US2/...
**描述**: [详细描述问题]
**尝试的解决方案**: [列出已尝试的方法]
**状态**: 阻塞/解决中
**负责人**: [姓名]
EOF
```

### 2. 寻求帮助

- 查看相关文档：`docs/PRD/`, `docs/handbook/`
- 查看历史实现：`git log --grep="关键词"`
- 询问团队成员

### 3. 调整计划

如果某个任务超时，立即调整计划：
- 评估是否可以简化实现
- 评估是否可以延后到 P1
- 更新 `plan.md` 和 `tasks.md`

---

## 📊 进度追踪

使用 GitHub Issues 或项目看板追踪进度：

```bash
# 创建 GitHub Issue
gh issue create --title "007-mvp-product-loop: Week 1 进度" --body "$(cat .specify/specs/007-mvp-product-loop/README.md)"

# 或使用项目看板
# 将 tasks.md 中的任务导入到看板
```

---

## 🎯 成功标准

### Week 1 结束时

- [ ] 运行 `make dev-golden-path` 所有服务启动
- [ ] 运行 `make local-acceptance` 所有测试通过
- [ ] 用户能看到洞察卡片并点击查看证据
- [ ] 运营能在质量看板查看实时指标

### Week 2 结束时

- [ ] Precision@50 ≥ 0.6
- [ ] 报告中能识别 50 个核心实体
- [ ] 报告有行动位（问题定义、建议动作、置信度、优先级）
- [ ] 产品经理能独立使用产品

---

**祝你顺利完成！** 🚀

