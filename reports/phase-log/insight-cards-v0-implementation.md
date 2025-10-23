# 洞察卡片 v0 实施报告

**实施日期**: 2025-10-22  
**任务来源**: `.specify/specs/005-data-quality-optimization` 和 `.specify/specs/006-2025-10-21-项目优化重构/tasks.md`  
**目标**: 洞察卡片 v0 上线，证据链可展示

---

## 📋 任务完成情况

### ✅ 已完成任务

#### T010: 创建洞察卡片数据模型
- **文件**: `backend/app/models/insight.py`
- **内容**:
  - `InsightCard` 模型：存储洞察卡片（标题、摘要、置信度、时间窗口、相关子版块）
  - `Evidence` 模型：存储证据段落（原帖 URL、摘录、时间戳、子版块、分数）
  - 使用 PostgreSQL ARRAY 和 JSONB 类型
  - 添加 GIN 索引优化查询性能
- **数据库迁移**: `backend/alembic/versions/20251022_000017_add_insight_cards_and_evidences.py`
- **状态**: ✅ 已执行迁移

#### T011: 创建洞察卡片 API Schema
- **文件**: `backend/app/schemas/insights.py`
- **内容**:
  - `EvidenceResponse`: 证据响应 Schema
  - `InsightCardResponse`: 洞察卡片响应 Schema
  - `InsightCardListResponse`: 洞察卡片列表响应 Schema
- **特点**: 使用 Pydantic 进行严格类型验证

#### T012: 创建洞察卡片 API
- **文件**: `backend/app/api/routes/insights.py`
- **端点**:
  1. `GET /api/insights` - 获取洞察卡片列表
     - 支持按任务 ID 过滤
     - 支持按最小置信度过滤
     - 支持按子版块过滤
     - 支持分页（skip/limit）
  2. `GET /api/insights/{insight_id}` - 获取单个洞察卡片详情
     - 包含完整的证据列表
     - 验证用户权限（只能查看自己的任务）
- **认证**: 使用 JWT Token 认证
- **授权**: 验证任务所有权

#### T012: 集成测试
- **文件**: `backend/tests/integration/test_insights_api.py`
- **测试用例**: 6 个
  1. ✅ `test_get_insights_by_task_id` - 测试根据任务 ID 获取洞察卡片列表
  2. ✅ `test_get_insights_unauthorized` - 测试未授权访问返回 401
  3. ✅ `test_get_insights_forbidden` - 测试访问其他用户的任务返回 403
  4. ✅ `test_get_insights_task_not_found` - 测试任务不存在返回 404
  5. ✅ `test_get_insights_pagination` - 测试分页功能
  6. ✅ `test_get_insight_by_id` - 测试根据 ID 获取单个洞察卡片
- **测试结果**: 所有 6 个测试通过 ✅
- **修复的问题**:
  - 密码哈希格式约束问题（使用 `hash_password()` 函数）
  - 任务状态约束问题（为 `completed` 状态添加 `completed_at` 时间戳）
  - SQLAlchemy `unique()` 方法问题（在 `get_insight` 端点中添加 `.unique()` 调用）

#### T013: 创建洞察卡片前端组件
- **文件**: `frontend/src/components/InsightCard.tsx`
- **功能**:
  - 展示洞察卡片的标题、摘要、置信度、时间窗口、相关子版块
  - 支持点击展开/收起证据列表
  - 置信度标签（高/中/低）
  - 证据数量显示
  - 证据详情展示（子版块、时间戳、摘录、原帖链接、相关性分数）
- **交互**: 可展开/收起证据，支持回调函数

#### T014: 创建证据面板组件
- **文件**: `frontend/src/components/EvidencePanel.tsx`
- **功能**:
  - 展示证据列表
  - 支持分页（每页 10 条）
  - 分页控件（上一页、下一页、页码按钮）
  - 显示范围信息（显示 1-10 / 共 50 条）
  - 证据卡片展示（序号、子版块、时间、摘录、链接、相关性分数）
- **特点**: 响应式设计，支持空状态

#### T015: 创建洞察列表页面
- **文件**: `frontend/src/pages/InsightsPage.tsx`
- **功能**:
  - 展示洞察卡片列表
  - 支持按置信度过滤（滑块控件）
  - 支持按子版块过滤（下拉选择）
  - 过滤器面板（可展开/收起）
  - 返回报告页面按钮
  - 导航面包屑
  - 加载状态和错误处理
- **路由**: `/insights/:taskId`
- **集成**: 使用 `InsightCard` 和 `EvidencePanel` 组件

#### 前端类型定义
- **文件**: `frontend/src/types/insight.types.ts`
- **内容**:
  - `Evidence` 接口
  - `InsightCard` 接口
  - `InsightCardListResponse` 接口
- **导出**: 已添加到 `frontend/src/types/index.ts`

#### 前端服务
- **文件**: `frontend/src/services/insights.service.ts`
- **功能**:
  - `getInsights()` - 获取洞察卡片列表
  - `getInsightById()` - 获取单个洞察卡片详情
- **特点**: 使用 `apiClient` 进行 API 调用

#### 路由配置
- **文件**: `frontend/src/router/index.tsx`
- **新增路由**: `/insights/:taskId`
- **保护**: 需要登录才能访问
- **导出**: 已添加到 `ROUTES` 常量

#### 报告页面集成
- **文件**: `frontend/src/pages/ReportPage.tsx`
- **新增**: "查看洞察卡片" 按钮
- **位置**: 报告页面顶部，分享按钮旁边
- **功能**: 点击跳转到洞察卡片页面

---

## 🎯 功能验证

### 后端 API 验证
- ✅ 数据库迁移成功执行
- ✅ 所有 6 个集成测试通过
- ✅ API 端点正常工作
- ✅ 认证和授权验证正常

### 前端验证
- ✅ TypeScript 类型检查通过（新增文件无错误）
- ✅ 组件结构完整
- ✅ 路由配置正确
- ✅ 服务层实现完整

---

## 📊 技术实现细节

### 后端技术栈
- **ORM**: SQLAlchemy 2.0 (Mapped, mapped_column)
- **数据库**: PostgreSQL (ARRAY, JSONB, GIN 索引)
- **API 框架**: FastAPI
- **认证**: JWT Token
- **验证**: Pydantic Schemas
- **测试**: pytest + pytest-asyncio

### 前端技术栈
- **框架**: React + TypeScript
- **路由**: React Router v6
- **状态管理**: useState, useEffect
- **样式**: Tailwind CSS
- **图标**: lucide-react
- **HTTP 客户端**: axios (通过 apiClient)

### 数据模型设计
```python
InsightCard:
  - id: UUID (主键)
  - task_id: UUID (外键 -> tasks.id)
  - title: String(500)
  - summary: Text
  - confidence: Numeric(5, 4)  # 0.0000 - 1.0000
  - time_window_days: Integer
  - subreddits: ARRAY(String(100))
  - evidences: List[Evidence] (关系)

Evidence:
  - id: UUID (主键)
  - insight_card_id: UUID (外键 -> insight_cards.id)
  - post_url: String(500)
  - excerpt: Text
  - timestamp: DateTime(timezone=True)
  - subreddit: String(100)
  - score: Numeric(5, 4)  # 0.0000 - 1.0000
```

---

## 🔧 修复的问题

### 1. SQLAlchemy unique() 方法错误
**问题**: 使用 `joinedload()` 加载集合关系时，需要调用 `.unique()` 去重  
**解决**: 在 `get_insight` 端点中添加 `result.unique().scalar_one_or_none()`

### 2. 密码哈希格式约束
**问题**: 测试中使用纯文本密码导致约束违反  
**解决**: 使用 `hash_password()` 函数生成正确的 bcrypt 哈希

### 3. 任务状态约束
**问题**: 创建 `completed` 状态的任务时缺少 `completed_at` 字段  
**解决**: 为 `completed` 状态的任务添加 `completed_at=datetime.now(timezone.utc)`

---

## 📝 待办事项

### 短期（下一步）
1. **生成洞察卡片数据**: 需要实现分析引擎生成洞察卡片的逻辑
2. **前端 E2E 测试**: 使用 Playwright 测试完整的用户流程
3. **性能优化**: 添加缓存机制，优化大量证据的加载

### 中期
1. **洞察卡片导出**: 支持导出洞察卡片为 PDF/JSON
2. **洞察卡片分享**: 支持分享洞察卡片链接
3. **洞察卡片评分**: 允许用户对洞察卡片进行评分和反馈

### 长期
1. **洞察卡片推荐**: 基于用户历史推荐相关洞察
2. **洞察卡片趋势**: 展示洞察卡片的时间趋势
3. **洞察卡片对比**: 支持多个洞察卡片的对比分析

---

## ✅ Checkpoint 验证

**目标**: 洞察卡片 v0 上线，证据链可展示

### 验证清单
- [x] 数据模型创建完成
- [x] API 端点实现完成
- [x] 集成测试全部通过
- [x] 前端组件创建完成
- [x] 前端页面创建完成
- [x] 路由配置完成
- [x] 类型定义完整
- [x] 服务层实现完整
- [x] 报告页面集成完成

**结论**: ✅ **洞察卡片 v0 已成功上线，证据链可展示功能已实现！**

---

## 📚 相关文档

- **PRD**: `.specify/specs/005-data-quality-optimization`
- **任务列表**: `.specify/specs/006-2025-10-21-项目优化重构/tasks.md`
- **数据模型**: `backend/app/models/insight.py`
- **API 文档**: `backend/app/api/routes/insights.py`
- **前端组件**: `frontend/src/components/InsightCard.tsx`, `frontend/src/components/EvidencePanel.tsx`
- **前端页面**: `frontend/src/pages/InsightsPage.tsx`

---

**报告生成时间**: 2025-10-22  
**报告生成人**: Augment Agent

