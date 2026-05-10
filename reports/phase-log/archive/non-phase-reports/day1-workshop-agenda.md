# Day 1 Schema Workshop 议程

> **时间**: 2025-10-10 14:00-16:00（2小时）
> **参与者**: Backend Agent A, Backend Agent B, Frontend Agent
> **目标**: 锁定前后端 Schema 契约，确保后续开发无阻塞

---

## 📋 Workshop 目标

### 核心目标
1. ✅ 确认所有 Pydantic Schema 定义
2. ✅ 锁定字段命名约定
3. ✅ 确认枚举类型完整列表
4. ✅ 确认可选字段和默认值规则
5. ✅ 确认数据验证规则
6. ✅ 确认 API 请求/响应格式
7. ✅ 全员签字确认 Schema 契约

### 交付物
- [ ] 完整的 Pydantic Schema 定义文档
- [ ] 前后端字段映射表
- [ ] 枚举类型定义文档
- [ ] 验证规则文档
- [ ] API 请求/响应示例（JSON）

---

## 🗣️ 议程（2小时）

### 第一部分：数据模型确认（30分钟）

#### 1.1 Users 表 Schema（5分钟）
**Backend A 主讲**

需要确认的字段：
- [ ] `id`: UUID - 生成方式？
- [ ] `email`: string - 验证规则？（正则表达式）
- [ ] `password_hash`: string - 加密算法？（bcrypt）
- [ ] `created_at`: timestamp - 格式？（ISO 8601）
- [ ] `last_login_at`: timestamp | null - 可选？
- [ ] `is_active`: boolean - 默认值？（true）
- [ ] `subscription_tier`: enum - 枚举值？（free/pro/enterprise）
- [ ] `subscription_expires_at`: timestamp | null - 可选？

**Frontend 需要确认**:
- 前端是否需要 `password_hash`？（应该不需要）
- 日期时间格式是否为 ISO 8601？

---

#### 1.2 Tasks 表 Schema（10分钟）
**Backend A 主讲**

需要确认的字段：
- [ ] `id`: UUID
- [ ] `user_id`: UUID - 外键关联
- [ ] `product_description`: string - **验证规则**：10-2000字符
  - 是否允许空格？
  - 是否允许特殊字符？
  - 是否允许换行符？
- [ ] `status`: enum - **TaskStatus**
  - 'pending'
  - 'processing'
  - 'completed'
  - 'failed'
- [ ] `error_message`: string | null - 仅在 status='failed' 时存在？
- [ ] `created_at`: timestamp
- [ ] `updated_at`: timestamp
- [ ] `completed_at`: timestamp | null - 仅在 status='completed' 时存在？

**Frontend 需要确认**:
- `product_description` 的前端验证规则必须与后端一致
- `error_message` 的格式？（纯文本还是结构化？）
- `status` 枚举值是否会扩展？

---

#### 1.3 Analysis 表 Schema（15分钟）
**Backend A 主讲**

需要确认的字段：
- [ ] `id`: UUID
- [ ] `task_id`: UUID - 1:1 关系
- [ ] `insights`: JSONB - **核心字段**，需要详细定义结构
- [ ] `sources`: JSONB - 数据溯源信息
- [ ] `confidence_score`: decimal(3,2) - 范围 0.00-1.00
- [ ] `analysis_version`: string - 默认 '1.0'
- [ ] `created_at`: timestamp

**insights 字段结构**（重点讨论）:
```json
{
  "pain_points": [
    {
      "description": "string",
      "frequency": "number",
      "sentiment_score": "number (-1.0 to 1.0)",
      "example_posts": [
        {
          "community": "string",
          "content": "string",
          "upvotes": "number",
          "url": "string?",        // 待确认
          "author": "string?",     // 待确认
          "created_at": "string?"  // 待确认
        }
      ]
    }
  ],
  "competitors": [
    {
      "name": "string",
      "mentions": "number",
      "sentiment": "enum (positive/negative/mixed)",
      "strengths": ["string"],
      "weaknesses": ["string"]
    }
  ],
  "opportunities": [
    {
      "description": "string",
      "relevance_score": "number (0.0 to 1.0)",
      "potential_users": "string",
      "source_communities": ["string"]
    }
  ]
}
```

**sources 字段结构**:
```json
{
  "communities": ["string"],
  "posts_analyzed": "number",
  "cache_hit_rate": "number (0.0 to 1.0)",
  "analysis_duration_seconds": "number",
  "reddit_api_calls": "number"
}
```

**Frontend 需要确认**:
- `example_posts` 的完整字段列表
- 数组字段的最大长度限制
- `sentiment_score` 和 `relevance_score` 的精度

---

### 第二部分：API 契约确认（40分钟）

#### 2.1 字段命名约定（10分钟）
**全员讨论**

**选项 A**: 后端统一 snake_case，前端自行转换
```json
// 后端响应
{
  "task_id": "uuid",
  "product_description": "string",
  "created_at": "2025-01-21T10:30:00Z"
}

// 前端转换后
{
  "taskId": "uuid",
  "productDescription": "string",
  "createdAt": "2025-01-21T10:30:00Z"
}
```

**选项 B**: 后端直接返回 camelCase
```json
// 后端响应（已转换）
{
  "taskId": "uuid",
  "productDescription": "string",
  "createdAt": "2025-01-21T10:30:00Z"
}
```

**决策**:
- [ ] 选择方案 A 还是 B？
- [ ] 如果选 A，前端使用什么转换工具？（humps / lodash / 自定义）
- [ ] 转换规则是否需要文档化？

---

#### 2.2 日期时间格式（5分钟）
**Backend A 确认**

**建议方案**: ISO 8601 格式，UTC 时区
```
2025-01-21T10:30:00Z
```

**需要确认**:
- [ ] 是否统一使用 UTC？
- [ ] 是否包含毫秒？（如 `2025-01-21T10:30:00.123Z`）
- [ ] 前端是否需要本地化显示？

---

#### 2.3 枚举类型定义（10分钟）
**Backend A 主讲**

**已知枚举**:
1. `TaskStatus`: 'pending' | 'processing' | 'completed' | 'failed'
2. `SubscriptionTier`: 'free' | 'pro' | 'enterprise'
3. `Sentiment`: 'positive' | 'negative' | 'mixed'
4. `ErrorSeverity`: 'info' | 'warning' | 'error' | 'critical'

**需要确认**:
- [ ] 是否有其他枚举类型？
- [ ] 枚举值是否会在未来扩展？
- [ ] 是否需要枚举的显示文本映射？
  ```typescript
  const TaskStatusLabels = {
    pending: '等待处理',
    processing: '正在分析',
    completed: '分析完成',
    failed: '分析失败'
  };
  ```

---

#### 2.4 可选字段和默认值（10分钟）
**Backend A 主讲**

**需要明确的可选字段**:
- [ ] `error_message`: 仅在 `status='failed'` 时存在
- [ ] `completed_at`: 仅在 `status='completed'` 时存在
- [ ] `last_login_at`: 用户首次登录时为 null
- [ ] `subscription_expires_at`: 免费用户为 null
- [ ] `example_posts.url`: 是否总是存在？
- [ ] `example_posts.author`: 是否总是存在？

**TypeScript 表示**:
```typescript
interface Task {
  id: string;
  errorMessage?: string;        // 可选
  completedAt?: string;          // 可选
}
```

---

#### 2.5 数据验证规则（5分钟）
**Backend A 主讲**

**需要确认的验证规则**:
- [ ] `product_description`: 10-2000 字符
  - 是否包含空格？
  - 是否允许特殊字符？
  - 是否允许换行符？
- [ ] `email`: 正则表达式？
- [ ] `password`: 最小长度？（建议 8 字符）
- [ ] `sentiment_score`: -1.0 到 1.0（包含边界值）
- [ ] `confidence_score`: 0.00 到 1.00（小数位数）

**前端需要**:
- 与后端完全一致的验证逻辑
- 使用 Zod 或 Yup 进行 schema 验证

---

### 第三部分：错误处理和 SSE（30分钟）

#### 3.1 错误响应格式（15分钟）
**Backend A 主讲**

**统一错误响应格式**（参考 PRD-02）:
```json
{
  "error": {
    "code": "REDDIT_API_LIMIT",
    "message": "Reddit API访问限制",
    "severity": "warning",
    "timestamp": "2025-01-21T10:30:00Z",
    "request_id": "req_123456789",
    "recovery": {
      "strategy": "fallback_to_cache",
      "auto_applied": true,
      "fallback_quality": {
        "cache_coverage": 0.87,
        "data_freshness_hours": 12,
        "estimated_accuracy": 0.91
      }
    },
    "user_actions": {
      "recommended": {
        "action": "accept_cached_analysis",
        "label": "接受缓存数据分析（推荐）",
        "confidence": "high"
      },
      "alternatives": [
        {
          "action": "retry_later",
          "label": "30分钟后重试获得最新数据",
          "wait_time": 1800
        }
      ]
    }
  }
}
```

**需要确认**:
- [ ] 错误码列表？
- [ ] 前端如何展示不同 severity 的错误？
- [ ] `user_actions` 的前端处理逻辑？

---

#### 3.2 SSE 事件格式（15分钟）
**Backend A 主讲**

**SSE 事件类型**:
1. `connected`: 连接成功
2. `progress`: 进度更新
3. `completed`: 任务完成
4. `error`: 错误事件
5. `close`: 连接关闭
6. `heartbeat`: 心跳（每 30 秒）

**事件数据格式**:
```
data: {"event": "connected", "task_id": "uuid"}

data: {"event": "progress", "status": "processing", "current_step": "community_discovery", "percentage": 25, "estimated_remaining": 180}

event: completed
data: {"event": "completed", "task_id": "uuid", "report_available": true, "processing_time": 267}
```

**需要确认**:
- [ ] 事件字段是否完整？
- [ ] 前端如何处理断线重连？
- [ ] 降级到轮询的触发条件？

---

### 第四部分：签字确认（20分钟）

#### 4.1 Schema 契约文档（10分钟）
**Backend A 整理**

创建 `reports/phase-log/schema-contract.md` 文档，包含：
- 所有 Pydantic Schema 定义
- 字段映射表
- 枚举类型列表
- 验证规则
- API 请求/响应示例

#### 4.2 全员签字（10分钟）
**全员参与**

在 `schema-contract.md` 底部签字确认：
```markdown
## 签字确认

我已阅读并同意以上 Schema 契约，承诺在后续开发中严格遵守。

- Backend Agent A: __________ (签名) 2025-10-10
- Backend Agent B: __________ (签名) 2025-10-10
- Frontend Agent: __________ (签名) 2025-10-10

**重要**: Schema 一旦确定，不得随意修改。如需修改，必须全员讨论并重新签字。
```

---

## ✅ Workshop 检查清单

### 会前准备
- [x] Frontend Agent 阅读 PRD-01/02/05/06
- [x] Frontend Agent 准备问题清单
- [x] Frontend Agent 创建类型定义规划

### 会中执行
- [ ] 确认所有数据模型字段
- [ ] 确认 API 契约
- [ ] 确认错误处理格式
- [ ] 确认 SSE 事件格式
- [ ] 创建 Schema 契约文档
- [ ] 全员签字确认

### 会后交付
- [ ] `reports/phase-log/schema-contract.md` 创建完成
- [ ] 全员签字确认
- [ ] Frontend Agent 更新 TypeScript 类型定义
- [ ] Backend Agent A 开始实现数据模型

---

**准备人**: Frontend Agent
**创建时间**: 2025-10-10 12:00
**Workshop 时间**: 2025-10-10 14:00-16:00
