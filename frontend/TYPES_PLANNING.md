# Frontend TypeScript 类型定义规划

> **创建日期**: 2025-10-10 Day 1
> **目的**: 基于 PRD-01/02/05/06 定义完整的前端类型系统
> **状态**: ✅ 已确认（Workshop 2025-10-10 15:50 签字）
> **参考**: `reports/phase-log/schema-contract.md`

---

## 1. 核心原则

### 1.1 类型安全零容忍
- ❌ 禁止使用 `any`
- ❌ 禁止使用 `unknown` 而不进行类型守卫
- ❌ 禁止使用 `as` 类型断言（除非绝对必要）
- ✅ 所有 API 响应必须有完整类型定义
- ✅ 所有组件 props 必须有类型定义
- ✅ 使用 Zod 进行运行时验证

### 1.2 命名约定
- **接口/类型**: PascalCase（如 `UserResponse`, `TaskStatus`）
- **枚举**: PascalCase（如 `TaskStatus.PENDING`）
- **字段**: camelCase（前端）或 snake_case（API 响应）
- **常量**: UPPER_SNAKE_CASE（如 `MAX_DESCRIPTION_LENGTH`）

---

## 2. 类型定义结构

### 2.1 用户相关类型（user.types.ts）

```typescript
/**
 * 用户账户信息
 * 对应后端 users 表
 */
export interface User {
  id: string;                    // UUID
  email: string;
  createdAt: string;             // ISO 8601
  lastLoginAt?: string;          // ISO 8601, 可选
  isActive: boolean;
  subscriptionTier: SubscriptionTier;
  subscriptionExpiresAt?: string; // ISO 8601, 可选
}

/**
 * 订阅等级枚举
 */
export enum SubscriptionTier {
  FREE = 'free',
  PRO = 'pro',
  ENTERPRISE = 'enterprise'
}

/**
 * 用户注册请求
 */
export interface RegisterRequest {
  email: string;
  password: string;
}

/**
 * 用户登录请求
 */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * 认证响应
 */
export interface AuthResponse {
  message: string;
  accessToken: string;
  tokenType: 'bearer';
  user: User;
}
```

---

### 2.2 任务相关类型（task.types.ts）

```typescript
/**
 * 任务状态枚举
 * 必须与后端 task_status ENUM 完全一致
 */
export enum TaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

/**
 * 任务信息
 * 对应后端 tasks 表
 */
export interface Task {
  id: string;                    // UUID
  userId: string;                // UUID
  productDescription: string;    // 10-2000 字符
  status: TaskStatus;
  errorMessage?: string;         // 仅在 status='failed' 时存在
  createdAt: string;             // ISO 8601
  updatedAt: string;             // ISO 8601
  completedAt?: string;          // ISO 8601, 仅在 status='completed' 时存在
}

/**
 * 创建分析任务请求
 */
export interface AnalyzeRequest {
  productDescription: string;
}

/**
 * 创建分析任务响应
 */
export interface AnalyzeResponse {
  taskId: string;
  status: TaskStatus;
  createdAt: string;
  estimatedCompletion: string;
  sseEndpoint: string;
}

/**
 * 任务状态查询响应
 */
export interface TaskStatusResponse {
  taskId: string;
  status: TaskStatus;
  progress?: {
    currentStep: string;
    completedSteps: string[];
    totalSteps: number;
    percentage: number;
  };
  createdAt: string;
  estimatedCompletion?: string;
  completedAt?: string;
  analysisSummary?: {
    communitiesAnalyzed: number;
    postsProcessed: number;
    insightsFound: number;
    confidenceScore: number;
  };
  reportAvailable?: boolean;
  error?: ErrorResponse;
}
```

---

### 2.3 分析结果类型（analysis.types.ts）

```typescript
/**
 * 示例帖子
 */
export interface ExamplePost {
  community: string;             // 如 "r/productivity"
  content: string;
  upvotes: number;
  url?: string;                  // 待 Workshop 确认
  author?: string;               // 待 Workshop 确认
  createdAt?: string;            // 待 Workshop 确认
}

/**
 * 用户痛点
 */
export interface PainPoint {
  description: string;
  frequency: number;             // 出现频率
  sentimentScore: number;        // -1.0 到 1.0
  examplePosts: ExamplePost[];
}

/**
 * 竞品情报
 */
export interface Competitor {
  name: string;
  mentions: number;
  sentiment: 'positive' | 'negative' | 'mixed';
  strengths: string[];
  weaknesses: string[];
}

/**
 * 商业机会
 */
export interface Opportunity {
  description: string;
  relevanceScore: number;        // 0.0 到 1.0
  potentialUsers: string;
  sourceCommunities: string[];
}

/**
 * 分析洞察（核心结果）
 */
export interface Insights {
  painPoints: PainPoint[];
  competitors: Competitor[];
  opportunities: Opportunity[];
}

/**
 * 数据溯源信息
 */
export interface Sources {
  communities: string[];
  postsAnalyzed: number;
  cacheHitRate: number;          // 0.0 到 1.0
  analysisDurationSeconds: number;
  redditApiCalls: number;
}

/**
 * 分析结果
 * 对应后端 analyses 表
 */
export interface Analysis {
  id: string;                    // UUID
  taskId: string;                // UUID
  insights: Insights;
  sources: Sources;
  confidenceScore: number;       // 0.00 到 1.00
  analysisVersion: string;
  createdAt: string;             // ISO 8601
}
```

---

### 2.4 报告类型（report.types.ts）

```typescript
/**
 * 执行摘要
 */
export interface ExecutiveSummary {
  totalCommunities: number;
  keyInsights: number;
  topOpportunity: string;
}

/**
 * 报告元数据
 */
export interface ReportMetadata {
  analysisVersion: string;
  confidenceScore: number;
  processingTimeSeconds: number;
  cacheHitRate: number;
  recoveryApplied: any | null;   // 待 Workshop 确认具体类型
}

/**
 * 完整报告响应
 */
export interface ReportResponse {
  taskId: string;
  generatedAt: string;           // ISO 8601
  report: {
    executiveSummary: ExecutiveSummary;
    painPoints: PainPoint[];
    competitors: Competitor[];
    opportunities: Opportunity[];
  };
  metadata: ReportMetadata;
}
```

---

### 2.5 SSE 事件类型（sse.types.ts）

```typescript
/**
 * SSE 事件类型
 */
export enum SSEEventType {
  CONNECTED = 'connected',
  PROGRESS = 'progress',
  COMPLETED = 'completed',
  ERROR = 'error',
  CLOSE = 'close',
  HEARTBEAT = 'heartbeat'
}

/**
 * SSE 进度事件
 */
export interface SSEProgressEvent {
  event: SSEEventType;
  taskId: string;
  status?: TaskStatus;
  currentStep?: string;
  percentage?: number;
  estimatedRemaining?: number;  // 秒
  processingTime?: number;      // 秒
  reportAvailable?: boolean;
  error?: ErrorResponse;
}

/**
 * SSE 连接状态
 */
export enum SSEConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error'
}
```

---

### 2.6 API 通用类型（api.types.ts）

```typescript
/**
 * 错误严重级别
 */
export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

/**
 * 错误恢复策略
 */
export interface ErrorRecovery {
  strategy: string;
  autoApplied: boolean;
  fallbackQuality?: {
    cacheCoverage: number;
    dataFreshnessHours: number;
    estimatedAccuracy: number;
  };
  retryInfo?: {
    retryAfter: string;          // ISO 8601
    maxRetries: number;
    currentAttempt: number;
  };
}

/**
 * 用户可执行操作
 */
export interface UserAction {
  action: string;
  label: string;
  confidence?: 'high' | 'medium' | 'low';
  waitTime?: number;             // 秒
}

/**
 * 错误响应
 */
export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    severity: ErrorSeverity;
    timestamp: string;           // ISO 8601
    requestId: string;
    recovery?: ErrorRecovery;
    userActions?: {
      recommended: UserAction;
      alternatives: UserAction[];
    };
    internal?: {
      component: string;
      operation: string;
      rateLimitReset?: string;   // ISO 8601
    };
  };
}

/**
 * API 响应包装器（泛型）
 */
export interface ApiResponse<T> {
  data?: T;
  error?: ErrorResponse;
  meta?: {
    requestId: string;
    timestamp: string;
    version: string;
  };
}
```

---

## 3. Workshop 确认结果（2025-10-10 15:50）✅

### 3.1 字段命名 ✅
- [x] 前端统一使用 camelCase
- [x] 后端 API 响应也使用 camelCase（Pydantic alias_generator 自动转换）
- [x] 无需手动转换层

**决策**: 后端数据库保持 snake_case，API 响应自动转换为 camelCase，前端直接使用。

---

### 3.2 可选字段 ✅
- [x] `ExamplePost` 完整字段: `community`, `content`, `upvotes`, `url?`, `author?`, `createdAt?`
- [x] `errorMessage?`: 仅在 `status='failed'` 时存在
- [x] `completedAt?`: 仅在 `status='completed'` 时存在
- [x] `recovery?`: 可选，仅在有恢复策略时存在
- [x] `userActions?`: 可选，仅在有用户操作建议时存在

**决策**: 所有可选字段使用 TypeScript `?` 标记，明确出现条件。

---

### 3.3 数据验证 ✅
- [x] `productDescription`: 10-2000 字符，允许空格/换行/特殊字符，trim 后至少 10 字符
- [x] `sentimentScore`: -1.0 到 1.0，2 位小数
- [x] `confidenceScore`: 0.00 到 1.00，2 位小数
- [x] 数组字段: `strengths` 和 `weaknesses` 建议最多 10 项

**决策**: 前后端验证规则完全一致，使用 Zod 实现。

---

### 3.4 枚举扩展 ✅
- [x] 确认 6 个枚举类型（TaskStatus, SubscriptionTier, Sentiment, ErrorSeverity, SSEEventType, RecoveryStrategy）
- [x] 枚举值暂不扩展（初版锁定）
- [x] 需要枚举的显示文本映射（前端实现）

**决策**: 6 个枚举类型完整定义，前后端值完全一致。

---

## 4. 下一步行动

### Workshop 后 ✅
1. [x] 根据 Workshop 决策更新类型定义
2. [ ] 创建实际的 TypeScript 文件
3. [ ] 添加 JSDoc 注释
4. [ ] 使用 Zod 创建运行时验证 Schema

### 晚上任务（18:00-20:00）
1. [ ] 创建 `src/types/` 目录结构
2. [ ] 实现所有类型定义文件（6 个文件）
   - [ ] `user.types.ts`
   - [ ] `task.types.ts`
   - [ ] `analysis.types.ts`
   - [ ] `report.types.ts`
   - [ ] `sse.types.ts`
   - [ ] `api.types.ts`
3. [ ] 创建 `index.ts` 统一导出
4. [ ] 编写类型使用示例和 JSDoc 注释

---

**维护者**: Frontend Agent
**最后更新**: 2025-10-10 16:00
**状态**: ✅ Workshop 已确认，准备实现

