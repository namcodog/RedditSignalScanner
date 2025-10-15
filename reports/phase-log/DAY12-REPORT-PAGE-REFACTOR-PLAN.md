# 📋 报告页面重构计划

**目标**: 1:1 还原参考网站 https://v0-reddit-business-signals.vercel.app

---

## 任务清单

### ✅ Phase 1: 页面头部优化
- [ ] 添加"分享"按钮
- [ ] 添加"已分析产品"卡片
- [ ] 优化统计卡片样式（4个卡片）
- [ ] 修改"导出报告"为"导出PDF"

### ✅ Phase 2: Tab 导航优化
- [ ] 优化 Tab 样式（选中状态、悬停状态）
- [ ] 确保 Tab 切换流畅

### ✅ Phase 3: 概览 Tab
- [ ] 优化市场情感卡片样式
- [ ] 添加热门社区卡片
- [ ] 移除执行摘要和分析元数据（参考网站没有）

### ✅ Phase 4: 用户痛点 Tab
- [ ] 添加严重程度标签（高/中/低）
- [ ] 添加用户示例引用（3条）
- [ ] 优化卡片样式

### ✅ Phase 5: 竞品分析 Tab
- [ ] 添加市场份额显示
- [ ] 优化优势/劣势列表样式（带颜色圆点）
- [ ] 优化卡片布局

### ✅ Phase 6: 商业机会 Tab
- [ ] 添加关键洞察列表（4条）
- [ ] 优化卡片样式
- [ ] 移除潜在用户数和相关性分数（参考网站没有）

---

## 实施顺序

1. **先修改数据结构** - 确保后端返回的数据包含所有需要的字段
2. **再修改前端组件** - 按照设计规范重写组件
3. **最后优化样式** - 微调颜色、间距、字体

---

## 需要的数据字段

### 热门社区
```typescript
{
  name: string;          // 如 "r/startups"
  members: number;       // 如 1200000
  relevance: number;     // 如 89 (百分比)
}
```

### 用户痛点
```typescript
{
  title: string;         // 如 "缺乏个性化推荐"
  severity: 'high' | 'medium' | 'low';  // 严重程度
  mentions: number;      // 提及次数
  description: string;   // 描述
  userExamples: string[]; // 用户示例（3条）
}
```

### 竞品分析
```typescript
{
  name: string;          // 如 "Product Hunt平台"
  mentions: number;      // 提及次数
  marketShare: number;   // 市场份额百分比
  strengths: string[];   // 优势列表
  weaknesses: string[];  // 劣势列表
}
```

### 商业机会
```typescript
{
  title: string;         // 如 "AI驱动的个性化推荐"
  description: string;   // 描述
  keyInsights: string[]; // 关键洞察（4条）
}
```

---

## 注意事项

1. **保持现有功能** - 不要破坏现有的导出、导航等功能
2. **响应式设计** - 确保在不同屏幕尺寸下都能正常显示
3. **类型安全** - 更新 TypeScript 类型定义
4. **测试验证** - 每个阶段完成后都要测试

---

**开始时间**: 2025-10-13  
**预计完成**: 2025-10-13  
**负责人**: Lead (AI Agent)

