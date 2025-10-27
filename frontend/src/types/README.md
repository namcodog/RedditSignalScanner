# TypeScript 类型定义文档

> **创建日期**: 2025-10-10 Day 1
> **基于**: Schema 契约 `reports/phase-log/schema-contract.md`
> **状态**: ✅ 已完成并与后端对齐

---

## 📋 概述

本目录包含 Reddit Signal Scanner 前端的完整 TypeScript 类型定义，与后端 Pydantic Schema 完全对齐。

---

## 📁 文件结构

```
src/types/
├── index.ts              # 统一导出（推荐使用）
├── user.types.ts         # 用户相关类型
├── task.types.ts         # 任务相关类型
├── analysis.types.ts     # 分析结果类型
├── report.types.ts       # 报告类型
├── sse.types.ts          # SSE 事件类型
├── api.types.ts          # API 通用类型
└── README.md             # 本文档
```

---

## 🎯 核心原则

### 1. 类型安全零容忍
- ❌ 禁止使用 `any`
- ❌ 禁止使用 `unknown` 而不进行类型守卫
- ❌ 禁止使用 `as` 类型断言（除非绝对必要）
- ✅ 所有 API 响应必须有完整类型定义
- ✅ 所有组件 props 必须有类型定义

### 2. 命名约定
- **接口/类型**: PascalCase（如 `UserResponse`, `TaskStatus`）
- **枚举/字面量**: PascalCase 或字符串联合，按照 PRD 规范输出
- **字段**: snake_case（如 `task_id`, `product_description`），与 PRD-02 完全一致
- **常量**: UPPER_SNAKE_CASE（如 `ERROR_CODES`）

### 3. 与后端对齐
- 所有类型定义与 `reports/phase-log/schema-contract.md` 完全一致
- 字段命名统一使用 snake_case（与后端 PRD 保持一致）
- 枚举值与后端完全一致
- 可选字段使用 `?` 标记

---

## 📚 使用示例

### 导入类型

```typescript
// 推荐：从统一导出导入
import { User, TaskStatus, AnalyzeRequest } from '@/types';

// 或者从具体文件导入
import { User } from '@/types/user.types';
import { TaskStatus } from '@/types/task.types';
```

### 使用枚举

```typescript
import { TaskStatus } from '@/types';

const status: TaskStatus = TaskStatus.PENDING;

// 类型守卫
function isCompleted(status: TaskStatus): boolean {
  return status === TaskStatus.COMPLETED;
}
```

### 使用接口

```typescript
import { AnalyzeRequest, AnalyzeResponse } from '@/types';

// 请求数据（与 PRD-02 定义一致）
const request: AnalyzeRequest = {
  product_description: 'AI笔记应用，帮助研究者自动组织和连接想法',
};

// 响应数据（保留 snake_case 字段）
const response: AnalyzeResponse = {
  task_id: '123e4567-e89b-12d3-a456-426614174000',
  status: TaskStatus.PENDING,
  created_at: '2025-01-21T10:30:00.123Z',
  estimated_completion: '2025-01-21T10:35:00.123Z',
  sse_endpoint: '/api/analyze/stream/123e4567-e89b-12d3-a456-426614174000',
};
```

### 使用泛型类型

```typescript
import { ApiResponse, User } from '@/types';

// API 响应包装
const userResponse: ApiResponse<User> = {
  data: {
    id: '123',
    email: 'user@example.com',
    createdAt: '2025-01-21T10:30:00.123Z',
    isActive: true,
    subscriptionTier: SubscriptionTier.FREE,
  },
  meta: {
    requestId: 'req-123',
    timestamp: '2025-01-21T10:30:00.123Z',
  },
};
```

### 处理可选字段

```typescript
import { Task } from '@/types';

function handleTask(task: Task): void {
  // 可选字段需要类型守卫
  if (task.error_message !== undefined) {
    console.error('Task failed:', task.error_message);
  }
  
  if (task.completed_at !== undefined) {
    console.log('Task completed at:', task.completed_at);
  }
}
```

---

## 🔍 类型定义清单

### user.types.ts
- ✅ `SubscriptionTier` 枚举（3 个值）
- ✅ `User` 接口
- ✅ `RegisterRequest` 接口
- ✅ `LoginRequest` 接口
- ✅ `AuthResponse` 接口
- ✅ `UpdateUserRequest` 接口

### task.types.ts
- ✅ `TaskStatus` 枚举（4 个值）
- ✅ `Task` 接口
- ✅ `AnalyzeRequest` 接口
- ✅ `AnalyzeResponse` 接口
- ✅ `TaskProgress` 接口
- ✅ `TaskStatusResponse` 接口

### analysis.types.ts
- ✅ `Sentiment` 枚举（3 个值）
- ✅ `ExamplePost` 接口
- ✅ `PainPoint` 接口
- ✅ `Competitor` 接口
- ✅ `Opportunity` 接口
- ✅ `Insights` 接口
- ✅ `Sources` 接口
- ✅ `Analysis` 接口

### report.types.ts
- ✅ `ExecutiveSummary` 接口
- ✅ `FallbackQuality` 接口
- ✅ `ReportMetadata` 接口
- ✅ `ReportResponse` 接口
- ✅ `report/schema.ts` 使用 Zod 对情感百分比（0-100）、置信度（0-1）等字段进行了边界约束，并由 `src/tests/contract/report-schema.contract.test.ts` 持续校验

### sse.types.ts
- ✅ `SSEEventType` 字符串联合类型
- ✅ `SSEConnectionStatus` 字符串联合类型
- ✅ `SSEBaseEvent` 接口
- ✅ `SSEConnectedEvent` 接口
- ✅ `SSEProgressEvent` 接口
- ✅ `SSECompletedEvent` 接口
- ✅ `SSEErrorEvent` 接口
- ✅ `SSECloseEvent` 接口
- ✅ `SSEHeartbeatEvent` 接口
- ✅ `SSEEvent` 联合类型
- ✅ `SSEEventHandler` 类型
- ✅ `SSEClientConfig` 接口

### api.types.ts
- ✅ `ErrorSeverity` 枚举（4 个值）
- ✅ `RecoveryStrategy` 枚举（4 个值）
- ✅ `ActionConfidence` 类型
- ✅ `FallbackQuality` 接口
- ✅ `RecoveryInfo` 接口
- ✅ `RecommendedAction` 接口
- ✅ `AlternativeAction` 接口
- ✅ `UserActions` 接口
- ✅ `ErrorDetail` 接口
- ✅ `ErrorResponse` 接口
- ✅ `ApiResponse<T>` 泛型接口
- ✅ `PaginationParams` 接口
- ✅ `PaginationMeta` 接口
- ✅ `PaginatedResponse<T>` 泛型接口
- ✅ `ERROR_CODES` 常量
- ✅ `ErrorCode` 类型

---

## ✅ 验证清单

### 与 Schema 契约对齐
- [x] 所有枚举值与后端完全一致
- [x] 所有字段命名使用 snake_case
- [x] 所有可选字段使用 `?` 标记
- [x] 所有日期时间字段使用 `string` 类型（ISO 8601）
- [x] 所有数值范围在注释中说明

### 类型安全
- [x] 无 `any` 类型
- [x] 无 `unknown` 类型（除非有类型守卫）
- [x] 无类型断言（`as`）
- [x] 所有接口字段有明确类型
- [x] 所有枚举有明确值

### 文档完整性
- [x] 所有接口有 JSDoc 注释
- [x] 所有字段有中文说明
- [x] 所有可选字段说明出现条件
- [x] 所有数值字段说明范围

---

## 🔄 更新记录

| 日期 | 版本 | 变更说明 | 负责人 |
|------|------|----------|--------|
| 2025-10-10 | 1.0 | 初始版本，基于 Schema 契约创建 | Frontend Agent |
| 2025-10-26 | 1.1 | 引入报告契约自动化校验与数值范围约束，新增 `src/tests/contract/report-schema.contract.test.ts` | Frontend Agent |

---

## 📞 联系方式

如有类型定义相关问题，请联系：
- **Frontend Agent**: 负责前端类型定义维护
- **Backend Agent A**: 负责后端 Pydantic Schema 维护

**重要**: 类型定义与 Schema 契约必须保持同步。如需修改，必须先更新 Schema 契约并全员签字。

---

**最后更新**: 2025-10-10 Day 1  
**状态**: ✅ 已完成并验证
