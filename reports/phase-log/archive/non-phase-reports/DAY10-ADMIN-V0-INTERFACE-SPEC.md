# Admin Dashboard v0界面规范

> **参考界面**: https://v0-reddit-signal-scanner.vercel.app
> **制定时间**: 2025-10-14
> **制定人**: Lead
> **用途**: Admin Dashboard UI实现的详细规范

---

## 🎯 总体要求

**核心原则**: UI必须与v0界面的视觉和交互**完全一致**

**验收标准**:
- 视觉还原度: 100%
- 交互还原度: 100%
- 功能完整度: 100%（UI层面）

---

## 📐 界面结构

### 1. 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Reddit Signal Scanner - Admin Dashboard                    │
│  系统正常                                                     │
├─────────────────────────────────────────────────────────────┤
│  [社区验收] [算法验收] [用户反馈] [生成 Patch] [一键开 PR]   │
├─────────────────────────────────────────────────────────────┤
│  社区列表表格                                                 │
│  ┌──────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐    │
│  │社区名│7天 │最后│重复│垃圾│主题│C-  │状态│标签│操作│    │
│  │      │命中│抓取│率  │率  │分  │Score│    │    │    │    │
│  ├──────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤    │
│  │r/... │ 83 │... │8.0%│6.0%│ 74 │ 82 │正常│... │... │    │
│  │r/... │ 45 │... │18% │12% │ 52 │ 48 │异常│... │... │    │
│  │r/... │ 67 │... │12% │8.0%│ 68 │ 65 │警告│... │... │    │
│  └──────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 UI元素详细规范

### 1. 页面标题

**文本**: "Reddit Signal Scanner - Admin Dashboard"

**样式**:
- 字体大小: 24px
- 字体粗细: Bold
- 颜色: #1a1a1a
- 位置: 页面顶部居中或左对齐

---

### 2. 系统状态

**文本**: "系统正常"

**样式**:
- 字体大小: 14px
- 颜色: #22c55e (绿色)
- 位置: 标题下方
- 可能的状态:
  - "系统正常" (绿色)
  - "系统警告" (黄色)
  - "系统异常" (红色)

---

### 3. 功能按钮组

**按钮列表**:
1. 社区验收
2. 算法验收
3. 用户反馈
4. 生成 Patch
5. 一键开 PR

**样式**:
- 按钮类型: 主要按钮 (Primary Button)
- 背景色: #3b82f6 (蓝色)
- 文字颜色: #ffffff (白色)
- 圆角: 4px
- 内边距: 8px 16px
- 字体大小: 14px
- 间距: 8px

**布局**:
- 水平排列
- 左对齐或居中
- 响应式：小屏幕时垂直堆叠

**交互**:
- Hover: 背景色变深 (#2563eb)
- Click: 触发对应功能（Day 10可以是空函数）
- Disabled: 灰色背景，不可点击

---

### 4. 社区列表表格

#### 表格结构

**列定义**（共10列）:

| 列名 | 宽度 | 对齐 | 数据类型 | 示例 |
|------|------|------|----------|------|
| 社区名 | 150px | 左 | string | r/startups |
| 7天命中 | 80px | 右 | number | 83 |
| 最后抓取 | 150px | 左 | datetime | 2025/9/15 11:20:00 |
| 重复率 | 80px | 右 | percentage | 8.0% |
| 垃圾率 | 80px | 右 | percentage | 6.0% |
| 主题分 | 80px | 右 | number | 74 |
| C-Score | 80px | 右 | number | 82 |
| 状态 | 80px | 中 | enum | 正常/警告/异常 |
| 标签 | 200px | 左 | string | 核心主题:创业 |
| 操作 | 100px | 中 | button | [操作] |

#### 表格样式

**表头**:
- 背景色: #f3f4f6 (浅灰)
- 文字颜色: #374151 (深灰)
- 字体大小: 14px
- 字体粗细: 600 (Semi-bold)
- 内边距: 12px 16px
- 边框: 1px solid #e5e7eb

**表格行**:
- 背景色: #ffffff (白色)
- 奇数行背景色: #f9fafb (浅灰，可选)
- 文字颜色: #1f2937 (深灰)
- 字体大小: 14px
- 内边距: 12px 16px
- 边框: 1px solid #e5e7eb
- Hover: 背景色 #f3f4f6

**状态标签样式**:

| 状态 | 背景色 | 文字颜色 | 示例 |
|------|--------|----------|------|
| 正常 | #dcfce7 | #166534 | 正常 |
| 警告 | #fef3c7 | #92400e | 警告 |
| 异常 | #fee2e2 | #991b1b | 异常 |

**操作按钮**:
- 文本: "操作"
- 背景色: #e5e7eb (浅灰)
- 文字颜色: #374151 (深灰)
- 圆角: 4px
- 内边距: 4px 12px
- Hover: 背景色 #d1d5db

---

## 📊 示例数据

### 社区列表数据（至少3条）

```typescript
const exampleCommunities = [
  {
    name: 'r/startups',
    hits_7d: 83,
    last_crawled: '2025/9/15 11:20:00',
    duplicate_rate: 8.0,
    spam_rate: 6.0,
    topic_score: 74,
    c_score: 82,
    status: 'normal',
    tags: ['核心主题:创业'],
  },
  {
    name: 'r/technology',
    hits_7d: 45,
    last_crawled: '2025/9/14 08:30:00',
    duplicate_rate: 18.0,
    spam_rate: 12.0,
    topic_score: 52,
    c_score: 48,
    status: 'error',
    tags: ['黑名单风险:广告多'],
  },
  {
    name: 'r/ArtificialIntelligence',
    hits_7d: 67,
    last_crawled: '2025/9/15 14:45:00',
    duplicate_rate: 12.0,
    spam_rate: 8.0,
    topic_score: 68,
    c_score: 65,
    status: 'warning',
    tags: ['实验主题:AI'],
  },
];
```

---

## 🔧 技术实现建议

### 1. 组件结构

```typescript
// AdminDashboardPage.tsx
export function AdminDashboardPage() {
  return (
    <div className="admin-dashboard">
      <Header />
      <SystemStatus />
      <ActionButtons />
      <CommunityTable />
    </div>
  );
}

// 子组件
function Header() { /* 标题 */ }
function SystemStatus() { /* 系统状态 */ }
function ActionButtons() { /* 5个功能按钮 */ }
function CommunityTable() { /* 社区列表表格 */ }
```

### 2. 数据接口

```typescript
// admin.service.ts
export const adminService = {
  // 获取社区列表
  getCommunities: async (): Promise<CommunityData[]> => {
    const response = await apiClient.get('/admin/communities');
    return response.data;
  },

  // 获取系统状态
  getSystemStatus: async (): Promise<string> => {
    const response = await apiClient.get('/admin/system/status');
    return response.data.status;
  },

  // 功能按钮的API（Day 10可以先不实现）
  reviewCommunity: async () => { /* TODO */ },
  reviewAlgorithm: async () => { /* TODO */ },
  getUserFeedback: async () => { /* TODO */ },
  generatePatch: async () => { /* TODO */ },
  openPR: async () => { /* TODO */ },
};
```

### 3. CSS样式建议

```css
/* AdminDashboard.css */
.admin-dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.admin-dashboard h1 {
  font-size: 24px;
  font-weight: bold;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.system-status {
  font-size: 14px;
  color: #22c55e;
  margin-bottom: 24px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.action-buttons button {
  background-color: #3b82f6;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
}

.action-buttons button:hover {
  background-color: #2563eb;
}

.community-table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid #e5e7eb;
}

.community-table th {
  background-color: #f3f4f6;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  padding: 12px 16px;
  text-align: left;
  border: 1px solid #e5e7eb;
}

.community-table td {
  padding: 12px 16px;
  font-size: 14px;
  color: #1f2937;
  border: 1px solid #e5e7eb;
}

.community-table tr:hover {
  background-color: #f3f4f6;
}

.status-normal {
  background-color: #dcfce7;
  color: #166534;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

.status-warning {
  background-color: #fef3c7;
  color: #92400e;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

.status-error {
  background-color: #fee2e2;
  color: #991b1b;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}
```

---

## ✅ 验收检查清单

### UI还原度检查

- [ ] 页面标题文字和样式一致
- [ ] 系统状态显示和颜色一致
- [ ] 5个功能按钮文字、样式、布局一致
- [ ] 表格列数正确（10列）
- [ ] 表格列名正确
- [ ] 表格样式一致（表头、行、边框）
- [ ] 状态标签颜色正确（正常/警告/异常）
- [ ] 操作按钮样式一致
- [ ] 整体布局和间距一致
- [ ] 响应式布局正常

### 功能检查

- [ ] 页面可访问（/admin）
- [ ] 数据正确加载
- [ ] 表格数据正确渲染
- [ ] 功能按钮可点击（即使是空函数）
- [ ] 状态标签根据数据动态显示
- [ ] 权限验证正常（非admin用户403）

### 代码质量检查

- [ ] TypeScript 0错误
- [ ] 组件结构清晰
- [ ] 代码可维护
- [ ] 注释完整

---

## 📸 截图对比

**要求**:
1. 截取v0界面完整截图
2. 截取实现后的界面截图
3. 并排对比，标注差异
4. 差异必须<5%

**保存位置**: `reports/phase-log/DAY10-ADMIN-UI-COMPARISON.png`

---

## 🚨 注意事项

1. **优先级**: UI还原度 > 功能完整度
2. **Day 10目标**: 完成UI层面的100%还原，功能按钮可以先是空函数
3. **Day 11目标**: 补充功能按钮的后端逻辑
4. **质量标准**: 宁可延长时间，也要确保UI完全一致

---

## 📝 实施建议

### Day 10时间分配

| 阶段 | 时间 | 任务 |
|------|------|------|
| 阶段1 | 30分钟 | 访问v0界面，截图分析 |
| 阶段2 | 3-4小时 | 组件开发（标题、按钮、表格） |
| 阶段3 | 2-3小时 | 样式调整（确保与v0一致） |
| 阶段4 | 30分钟 | 测试和对比 |
| 阶段5 | 30分钟 | 修复差异 |

**总计**: 6-8小时

---

## 🎯 成功标志

1. ✅ UI与v0界面视觉完全一致
2. ✅ 所有UI元素正常显示
3. ✅ 表格数据正确渲染
4. ✅ 状态标签颜色正确
5. ✅ TypeScript 0错误
6. ✅ 截图对比差异<5%

---

**制定人**: Lead
**制定时间**: 2025-10-14
**参考界面**: https://v0-reddit-signal-scanner.vercel.app
**状态**: 📋 待实施

---

**记住**: "UI还原度100%，这是我们的承诺！" ✅
