# 🎯 Frontend Agent - 报告页面重构任务

**分配给**: Frontend Agent  
**优先级**: P0 - 阻塞发布  
**截止时间**: 立即完成  
**参考网站**: https://v0-reddit-business-signals.vercel.app

---

## 📋 任务概述

根据用户反馈，当前报告页面与参考网站存在较大差距，需要进行 1:1 还原。

### 用户反馈的问题

1. ❌ Tab 的视觉和交互与参考网站不一致
2. ❌ 概览 Tab 缺少热门社区，视觉不对
3. ❌ 用户痛点卡片样式差距大
4. ❌ 竞品分析视觉不对
5. ❌ 商业机会卡片样式差距大
6. ❌ Tab 显示比例与参考网站不一致

---

## 📐 设计规范

详细设计规范请查看：`reports/phase-log/DAY12-REPORT-PAGE-DESIGN-SPEC.md`

---

## 🔧 具体修改任务

### Task 1: 页面头部优化

**文件**: `frontend/src/pages/ReportPage.tsx`

**修改内容**:
1. 添加"分享"按钮（在"导出PDF"和"开始新分析"之间）
2. 添加"已分析产品"卡片（在标题下方）
3. 修改"导出报告"按钮文字为"导出PDF"
4. 优化4个统计卡片的样式

**参考代码**:
```tsx
{/* 分享按钮 */}
<button className="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium">
  <Share2 className="mr-2 h-4 w-4" />
  分享
</button>

{/* 已分析产品卡片 */}
<div className="rounded-lg border border-border bg-muted/50 p-4">
  <p className="text-sm font-medium text-muted-foreground mb-2">已分析产品</p>
  <p className="text-sm text-foreground">{productDescription}</p>
</div>
```

---

### Task 2: 概览 Tab 优化

**文件**: `frontend/src/pages/ReportPage.tsx`

**修改内容**:
1. 优化市场情感卡片样式（3个情感指标横向排列）
2. 添加热门社区卡片
3. 移除执行摘要和分析元数据

**热门社区数据结构**:
```typescript
interface TopCommunity {
  name: string;          // 如 "r/startups"
  members: number;       // 如 1200000
  relevance: number;     // 如 89 (百分比)
}
```

**参考代码**:
```tsx
{/* 热门社区 */}
<div className="rounded-lg border border-border bg-card p-6">
  <h3 className="text-lg font-semibold mb-4">热门社区</h3>
  <div className="space-y-4">
    {topCommunities.map((community) => (
      <div key={community.name} className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-blue-600">{community.name}</h4>
          <span className="text-sm text-muted-foreground">
            {community.members.toLocaleString()} 成员
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-600" 
              style={{ width: `${community.relevance}%` }}
            />
          </div>
          <span className="text-sm font-medium">{community.relevance}% 相关</span>
        </div>
      </div>
    ))}
  </div>
</div>
```

---

### Task 3: 用户痛点 Tab 优化

**文件**: `frontend/src/components/PainPointsList.tsx`

**修改内容**:
1. 添加严重程度标签（高/中/低，带颜色）
2. 添加用户示例引用（3条，带引号）
3. 优化卡片样式

**数据结构**:
```typescript
interface PainPoint {
  title: string;
  severity: 'high' | 'medium' | 'low';
  mentions: number;
  description: string;
  userExamples: string[];  // 3条用户引用
}
```

**参考代码**:
```tsx
{/* 严重程度标签 */}
<span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
  severity === 'high' ? 'bg-red-100 text-red-800' :
  severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
  'bg-green-100 text-green-800'
}`}>
  {severity === 'high' ? '高' : severity === 'medium' ? '中' : '低'}
</span>

{/* 用户示例 */}
<div className="mt-4">
  <h4 className="text-sm font-semibold mb-2">用户示例：</h4>
  <div className="space-y-2">
    {userExamples.map((example, i) => (
      <p key={i} className="text-sm italic text-muted-foreground bg-muted/50 p-3 rounded">
        "{example}"
      </p>
    ))}
  </div>
</div>
```

---

### Task 4: 竞品分析 Tab 优化

**文件**: `frontend/src/components/CompetitorsList.tsx`

**修改内容**:
1. 添加市场份额显示（大号、蓝色）
2. 优化优势/劣势列表样式（带颜色圆点）
3. 优化卡片布局

**数据结构**:
```typescript
interface Competitor {
  name: string;
  mentions: number;
  marketShare: number;  // 百分比
  strengths: string[];
  weaknesses: string[];
}
```

**参考代码**:
```tsx
{/* 市场份额 */}
<div className="text-3xl font-bold text-blue-600 mb-2">
  {marketShare}% 市场份额
</div>

{/* 优势列表 */}
<div className="mt-4">
  <h4 className="text-sm font-semibold mb-2">优势</h4>
  <ul className="space-y-1">
    {strengths.map((strength, i) => (
      <li key={i} className="flex items-start gap-2 text-sm">
        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-green-600 flex-shrink-0" />
        <span>{strength}</span>
      </li>
    ))}
  </ul>
</div>

{/* 劣势列表 */}
<div className="mt-4">
  <h4 className="text-sm font-semibold mb-2">劣势</h4>
  <ul className="space-y-1">
    {weaknesses.map((weakness, i) => (
      <li key={i} className="flex items-start gap-2 text-sm">
        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-red-600 flex-shrink-0" />
        <span>{weakness}</span>
      </li>
    ))}
  </ul>
</div>
```

---

### Task 5: 商业机会 Tab 优化

**文件**: `frontend/src/components/OpportunitiesList.tsx`

**修改内容**:
1. 添加关键洞察列表（4条，带蓝色圆点）
2. 优化卡片样式
3. 移除潜在用户数和相关性分数

**数据结构**:
```typescript
interface Opportunity {
  title: string;
  description: string;
  keyInsights: string[];  // 4条关键洞察
}
```

**参考代码**:
```tsx
{/* 关键洞察 */}
<div className="mt-4">
  <h4 className="text-sm font-semibold mb-2">关键洞察：</h4>
  <ul className="space-y-2">
    {keyInsights.map((insight, i) => (
      <li key={i} className="flex items-start gap-2 text-sm">
        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-blue-600 flex-shrink-0" />
        <span>{insight}</span>
      </li>
    ))}
  </ul>
</div>
```

---

### Task 6: Tab 样式优化

**文件**: `frontend/src/components/ui/tabs.tsx` 或 `frontend/src/pages/ReportPage.tsx`

**修改内容**:
1. 选中状态：蓝色下划线 + 蓝色文字
2. 未选中状态：灰色文字
3. 悬停状态：文字变深
4. 优化间距和字体

**参考样式**:
```tsx
{/* Tab 触发器 */}
<TabsTrigger 
  value="overview"
  className="data-[state=active]:border-b-2 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 text-muted-foreground hover:text-foreground transition-colors"
>
  概览
</TabsTrigger>
```

---

## ✅ 验收标准

1. **视觉一致性**: 与参考网站 https://v0-reddit-business-signals.vercel.app 视觉效果 90% 以上一致
2. **功能完整性**: 所有现有功能（导出、导航等）正常工作
3. **响应式设计**: 在不同屏幕尺寸下都能正常显示
4. **类型安全**: 无 TypeScript 错误
5. **性能**: 页面加载和切换流畅，无卡顿

---

## 📝 提交要求

完成后请提交：
1. 修改后的代码文件
2. 测试截图或录屏
3. 修复报告（使用四问框架）

---

**开始时间**: 立即  
**预计完成时间**: 2小时  
**分配人**: Lead (AI Agent)  
**执行人**: Frontend Agent

