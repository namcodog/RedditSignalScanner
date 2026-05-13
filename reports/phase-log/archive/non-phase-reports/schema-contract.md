# Schema 契约文档（前后端数据契约）

> **创建日期**: 2025-10-10 Day 1
> **Workshop 时间**: 14:00-16:00
> **参与者**: Backend Agent A, Backend Agent B, Frontend Agent
> **状态**: ✅ 已签字确认，锁定不可修改

---

## 📋 契约概述

本文档定义了 Reddit Signal Scanner 前后端的完整数据契约，包括：
1. 字段命名约定
2. 数据类型定义
3. 枚举类型列表
4. 可选字段规则
5. 数据验证规则
6. API 请求/响应格式
7. 错误响应格式

**重要**: 本契约一旦签字确认，后续不得随意修改。如需修改，必须全员讨论并重新签字。

---

## 1. 核心决策

### 1.1 字段命名约定

**决策**: 后端 API 响应使用 camelCase，前端 TypeScript 使用 camelCase

**实现方式**:
- 后端数据库: snake_case（如 `product_description`）
- 后端 Pydantic: 使用 `alias_generator` 自动转换为 camelCase
- 后端 API 响应: camelCase（如 `productDescription`）
- 前端 TypeScript: camelCase（如 `productDescription`）

**示例**:
```python
# 后端 Pydantic Model
class TaskResponse(BaseModel):
    task_id: str = Field(alias="taskId")
    product_description: str = Field(alias="productDescription")
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True
        alias_generator = to_camel
```

```typescript
// 前端 TypeScript Interface
interface TaskResponse {
  taskId: string;
  productDescription: string;
  createdAt: string;
}
```

---

### 1.2 日期时间格式

**决策**: ISO 8601 格式，UTC 时区，包含毫秒

**格式**: `YYYY-MM-DDTHH:mm:ss.sssZ`

**示例**: `2025-01-21T10:30:00.123Z`

**后端实现**:
```python
from datetime import datetime

# 序列化
datetime.utcnow().isoformat() + 'Z'
```

**前端处理**:
```typescript
// 解析
const date = new Date('2025-01-21T10:30:00.123Z');

// 格式化（使用 dayjs）
import dayjs from 'dayjs';
const formatted = dayjs(dateString).format('YYYY-MM-DD HH:mm:ss');
```

---

### 1.3 枚举类型完整列表

#### TaskStatus（任务状态）
```python
# 后端
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

```typescript
// 前端
enum TaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}
```

#### SubscriptionTier（订阅等级）
```python
# 后端
class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
```

```typescript
// 前端
enum SubscriptionTier {
  FREE = 'free',
  PRO = 'pro',
  ENTERPRISE = 'enterprise'
}
```

#### Sentiment（情感倾向）
```python
# 后端
class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
```

```typescript
// 前端
enum Sentiment {
  POSITIVE = 'positive',
  NEGATIVE = 'negative',
  MIXED = 'mixed'
}
```

#### ErrorSeverity（错误严重级别）
```python
# 后端
class ErrorSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

```typescript
// 前端
enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}
```

#### SSEEventType（SSE 事件类型）
```python
# 后端
class SSEEventType(str, Enum):
    CONNECTED = "connected"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"
    CLOSE = "close"
    HEARTBEAT = "heartbeat"
```

```typescript
// 前端
enum SSEEventType {
  CONNECTED = 'connected',
  PROGRESS = 'progress',
  COMPLETED = 'completed',
  ERROR = 'error',
  CLOSE = 'close',
  HEARTBEAT = 'heartbeat'
}
```

#### RecoveryStrategy（恢复策略）
```python
# 后端
class RecoveryStrategy(str, Enum):
    FALLBACK_TO_CACHE = "fallback_to_cache"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    DELAY_PROCESSING = "delay_processing"
    PARTIAL_RESULTS = "partial_results"
```

```typescript
// 前端
enum RecoveryStrategy {
  FALLBACK_TO_CACHE = 'fallback_to_cache',
  RETRY_WITH_BACKOFF = 'retry_with_backoff',
  DELAY_PROCESSING = 'delay_processing',
  PARTIAL_RESULTS = 'partial_results'
}
```

---

### 1.4 可选字段规则

**规则**: 使用 `?` 标记可选字段，明确出现条件

#### Task 相关
- `errorMessage?`: 仅在 `status='failed'` 时存在
- `completedAt?`: 仅在 `status='completed'` 时存在

#### User 相关
- `lastLoginAt?`: 首次注册时为 null
- `subscriptionExpiresAt?`: 免费用户为 null

#### Analysis 相关
- `confidenceScore`: 必填（0.00-1.00）

#### ExamplePost 相关
- `url?`: 可选，Reddit 帖子链接
- `author?`: 可选，作者用户名
- `createdAt?`: 可选，帖子创建时间

#### ErrorResponse 相关
- `recovery?`: 可选，仅在有恢复策略时存在
- `userActions?`: 可选，仅在有用户操作建议时存在

---

### 1.5 数据验证规则

#### productDescription（产品描述）
- **长度**: 10-2000 字符
- **允许**: 空格、换行符、特殊字符
- **不允许**: 纯空格（trim 后至少 10 字符）
- **前端验证**:
  ```typescript
  const schema = z.string()
    .min(10, '产品描述至少需要10个字符')
    .max(2000, '产品描述最多2000个字符')
    .refine(val => val.trim().length >= 10, '产品描述不能为纯空格');
  ```

#### email（邮箱）
- **正则**: `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`
- **前端验证**:
  ```typescript
  const schema = z.string().email('邮箱格式不正确');
  ```

#### password（密码）
- **最小长度**: 8 字符
- **复杂度**: 无要求（初版保持简单）
- **前端验证**:
  ```typescript
  const schema = z.string().min(8, '密码至少需要8个字符');
  ```

#### sentimentScore（情感分数）
- **范围**: -1.0 到 1.0（包含边界）
- **精度**: 2 位小数
- **前端验证**:
  ```typescript
  const schema = z.number().min(-1.0).max(1.0);
  ```

#### confidenceScore（置信度分数）
- **范围**: 0.00 到 1.00（包含边界）
- **精度**: 2 位小数
- **前端验证**:
  ```typescript
  const schema = z.number().min(0.00).max(1.00);
  ```

---

## 2. 完整数据模型定义

### 2.1 User（用户）

```typescript
interface User {
  id: string;                          // UUID
  email: string;                       // 邮箱
  createdAt: string;                   // ISO 8601
  lastLoginAt?: string;                // ISO 8601, 可选
  isActive: boolean;                   // 账户状态
  subscriptionTier: SubscriptionTier;  // 订阅等级
  subscriptionExpiresAt?: string;      // ISO 8601, 可选
}
```

### 2.2 Task（任务）

```typescript
interface Task {
  id: string;                    // UUID
  userId: string;                // UUID
  productDescription: string;    // 10-2000 字符
  status: TaskStatus;            // 任务状态
  errorMessage?: string;         // 可选，仅在 failed 时存在
  createdAt: string;             // ISO 8601
  updatedAt: string;             // ISO 8601
  completedAt?: string;          // ISO 8601, 可选
}
```

### 2.3 Analysis（分析结果）

```typescript
interface Analysis {
  id: string;                    // UUID
  taskId: string;                // UUID
  insights: Insights;            // 核心分析结果
  sources: Sources;              // 数据溯源
  confidenceScore: number;       // 0.00-1.00
  analysisVersion: string;       // 如 "1.0"
  createdAt: string;             // ISO 8601
}

interface Insights {
  painPoints: PainPoint[];
  competitors: Competitor[];
  opportunities: Opportunity[];
}

interface PainPoint {
  description: string;
  frequency: number;
  sentimentScore: number;        // -1.0 到 1.0
  examplePosts: ExamplePost[];
}

interface Competitor {
  name: string;
  mentions: number;
  sentiment: Sentiment;
  strengths: string[];           // 建议最多 10 项
  weaknesses: string[];          // 建议最多 10 项
}

interface Opportunity {
  description: string;
  relevanceScore: number;        // 0.0 到 1.0
  potentialUsers: string;
  sourceCommunities: string[];
}

interface ExamplePost {
  community: string;             // 如 "r/productivity"
  content: string;               // 帖子内容摘要
  upvotes: number;               // 点赞数
  url?: string;                  // 可选，Reddit 链接
  author?: string;               // 可选，作者用户名
  createdAt?: string;            // 可选，ISO 8601
}

interface Sources {
  communities: string[];
  postsAnalyzed: number;
  cacheHitRate: number;          // 0.0 到 1.0
  analysisDurationSeconds: number;
  redditApiCalls: number;
}
```

---

## 3. API 请求/响应格式

### 3.1 POST /api/analyze（创建分析任务）

**请求**:
```json
{
  "productDescription": "AI笔记应用，帮助研究者自动组织和连接想法的智能工具"
}
```

**响应**:
```json
{
  "taskId": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "createdAt": "2025-01-21T10:30:00.123Z",
  "estimatedCompletion": "2025-01-21T10:35:00.123Z",
  "sseEndpoint": "/api/analyze/stream/123e4567-e89b-12d3-a456-426614174000"
}
```

### 3.2 GET /api/analyze/stream/{taskId}（SSE 实时推送）

**SSE 事件流**:
```
data: {"event": "connected", "taskId": "123e4567-e89b-12d3-a456-426614174000"}

data: {"event": "progress", "status": "processing", "currentStep": "community_discovery", "percentage": 25, "estimatedRemaining": 180}

event: completed
data: {"event": "completed", "taskId": "123e4567-e89b-12d3-a456-426614174000", "reportAvailable": true, "processingTime": 267}
```

### 3.3 GET /api/status/{taskId}（查询任务状态）

**响应（处理中）**:
```json
{
  "taskId": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "progress": {
    "currentStep": "community_discovery",
    "completedSteps": ["input_validation", "keyword_extraction"],
    "totalSteps": 4,
    "percentage": 50
  },
  "createdAt": "2025-01-21T10:30:00.123Z",
  "estimatedCompletion": "2025-01-21T10:35:00.123Z"
}
```

### 3.4 GET /api/report/{taskId}（获取分析报告）

**响应**:
```json
{
  "taskId": "123e4567-e89b-12d3-a456-426614174000",
  "generatedAt": "2025-01-21T10:34:30.123Z",
  "report": {
    "executiveSummary": {
      "totalCommunities": 18,
      "keyInsights": 23,
      "topOpportunity": "笔记应用间的数据迁移痛点"
    },
    "painPoints": [...],
    "competitors": [...],
    "opportunities": [...]
  },
  "metadata": {
    "analysisVersion": "1.0",
    "confidenceScore": 0.87,
    "processingTimeSeconds": 267,
    "cacheHitRate": 0.87,
    "recoveryApplied": null
  }
}
```

---

## 4. 错误响应格式

### 4.1 统一错误响应

```typescript
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    severity: ErrorSeverity;
    timestamp: string;
    requestId: string;
    recovery?: {
      strategy: RecoveryStrategy;
      autoApplied: boolean;
      fallbackQuality?: {
        cacheCoverage: number;
        dataFreshnessHours: number;
        estimatedAccuracy: number;
      };
    };
    userActions?: {
      recommended: {
        action: string;
        label: string;
        confidence: 'high' | 'medium' | 'low';
      };
      alternatives: Array<{
        action: string;
        label: string;
        waitTime?: number;
      }>;
    };
  };
}
```

### 4.2 常见错误码列表

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| `INVALID_DESCRIPTION` | 产品描述无效 | 400 |
| `TASK_NOT_FOUND` | 任务不存在 | 404 |
| `REPORT_NOT_READY` | 报告未生成 | 409 |
| `REDDIT_API_LIMIT` | Reddit API 限流 | 200（带 recovery） |
| `DATABASE_ERROR` | 数据库错误 | 500 |
| `ANALYSIS_TIMEOUT` | 分析超时 | 200（带 partial_results） |
| `RATE_LIMIT_EXCEEDED` | 请求频率过高 | 429 |
| `SSE_CONNECTION_FAILED` | SSE 连接失败 | 200（降级到轮询） |

---

## 5. 签字确认

我已阅读并同意以上 Schema 契约，承诺在后续开发中严格遵守。

**重要**: Schema 一旦确定，不得随意修改。如需修改，必须全员讨论并重新签字。

---

**签字**:

- **Backend Agent A**: ✅ 已确认（2025-10-10 15:50）
- **Backend Agent B**: ✅ 已确认（2025-10-10 15:50）
- **Frontend Agent**: ✅ 已确认（2025-10-10 15:50）

---

**文档版本**: 1.0
**创建时间**: 2025-10-10 14:00-16:00
**最后更新**: 2025-10-10 15:50
**状态**: ✅ 已锁定，不可修改
