# 前端状态管理方案

> **创建日期**: 2025-10-10 Day 4
> **状态**: 方案设计，等待 Day 5 实现

---

## 📋 概述

本文档描述 Reddit Signal Scanner 前端的状态管理方案设计。

---

## 🎯 状态管理需求

### 1. 全局状态

- **用户认证状态**: 登录状态、用户信息、JWT token
- **任务状态**: 当前任务 ID、任务状态、进度信息
- **SSE 连接状态**: 连接状态、最新事件

### 2. 页面状态

- **输入页面**: 表单数据、验证错误
- **等待页面**: 进度百分比、当前步骤、SSE 连接状态
- **报告页面**: 报告数据、加载状态

---

## 🏗️ 方案选型

### 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Context API** | 内置、无需依赖 | 性能问题（大量重渲染） | 简单状态 |
| **Zustand** | 轻量、简单、性能好 | 生态较小 | 中小型应用 ✅ |
| **Jotai** | 原子化、灵活 | 学习曲线 | 复杂状态 |
| **Redux Toolkit** | 生态完善、工具丰富 | 重量级、样板代码多 | 大型应用 |

### 推荐方案: **Zustand**

**理由**:
1. ✅ 轻量级（~1KB）
2. ✅ API 简单，学习成本低
3. ✅ 性能优秀（基于订阅模式）
4. ✅ TypeScript 支持好
5. ✅ 适合中小型 SPA

---

## 📦 状态结构设计

### 1. 认证状态（Auth Store）

```typescript
interface AuthState {
  // 状态
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  
  // 操作
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (email: string, password: string) => Promise<void>;
  getCurrentUser: () => Promise<void>;
}
```

### 2. 任务状态（Task Store）

```typescript
interface TaskState {
  // 状态
  currentTaskId: string | null;
  taskStatus: TaskStatus | null;
  progress: number;
  currentStep: string;
  errorMessage: string | null;
  
  // 操作
  createTask: (description: string) => Promise<string>;
  getTaskStatus: (taskId: string) => Promise<void>;
  resetTask: () => void;
}
```

### 3. SSE 连接状态（SSE Store）

```typescript
interface SSEState {
  // 状态
  connectionStatus: SSEConnectionStatus;
  latestEvent: SSEEvent | null;
  isPolling: boolean;
  
  // 操作
  connect: (taskId: string) => void;
  disconnect: () => void;
  handleEvent: (event: SSEEvent) => void;
}
```

### 4. 报告状态（Report Store）

```typescript
interface ReportState {
  // 状态
  report: ReportResponse | null;
  isLoading: boolean;
  error: string | null;
  
  // 操作
  fetchReport: (taskId: string) => Promise<void>;
  clearReport: () => void;
}
```

---

## 🔄 状态流转

### 完整流程

```
用户登录
  ↓
[AuthStore] 保存 token 和用户信息
  ↓
用户提交产品描述
  ↓
[TaskStore] 创建任务，保存 taskId
  ↓
跳转到等待页面
  ↓
[SSEStore] 建立 SSE 连接
  ↓
接收进度事件
  ↓
[TaskStore] 更新进度和当前步骤
  ↓
任务完成
  ↓
跳转到报告页面
  ↓
[ReportStore] 获取报告数据
```

---

## 📝 实现计划

### Day 5 实现

- [ ] 安装 Zustand: `npm install zustand`
- [ ] 创建 `src/stores/auth.store.ts`
- [ ] 创建 `src/stores/task.store.ts`
- [ ] 创建 `src/stores/sse.store.ts`
- [ ] 创建 `src/stores/report.store.ts`
- [ ] 创建 `src/stores/index.ts`（统一导出）

### Day 6-7 集成

- [ ] 在页面组件中使用 stores
- [ ] 测试状态流转
- [ ] 优化性能

---

## 🔐 持久化策略

### LocalStorage 持久化

**需要持久化的状态**:
- ✅ `AuthStore.token` - JWT token
- ✅ `AuthStore.user` - 用户信息
- ❌ `TaskStore` - 不持久化（任务是临时的）
- ❌ `SSEStore` - 不持久化（连接是临时的）
- ❌ `ReportStore` - 不持久化（报告可重新获取）

**实现方式**:
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set) => ({
      // ... state and actions
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    }
  )
);
```

---

## 🧪 测试策略

### 单元测试

- [ ] 测试每个 store 的 actions
- [ ] 测试状态更新逻辑
- [ ] 测试持久化逻辑

### 集成测试

- [ ] 测试多个 stores 之间的协作
- [ ] 测试完整的用户流程

---

## 📚 参考资料

- [Zustand 官方文档](https://github.com/pmndrs/zustand)
- [Zustand TypeScript 指南](https://github.com/pmndrs/zustand#typescript)
- [Zustand 持久化中间件](https://github.com/pmndrs/zustand#persist-middleware)

---

**最后更新**: 2025-10-10 Day 4  
**状态**: ✅ 方案设计完成，等待 Day 5 实现

