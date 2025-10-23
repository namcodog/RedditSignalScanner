# Reddit Signal Scanner - API 接口文档

**版本**: v0.1.0  
**生成时间**: 2025-10-22  
**基础路径**: `/api`  
**文档类型**: 前后端联调规范文档

---

## 目录

- [1. 认证模块 (Authentication)](#1-认证模块-authentication)
- [2. 分析任务模块 (Analysis)](#2-分析任务模块-analysis)
- [3. 任务状态模块 (Task Status)](#3-任务状态模块-task-status)
- [4. 报告模块 (Reports)](#4-报告模块-reports)
- [5. 洞察卡片模块 (Insights)](#5-洞察卡片模块-insights)
- [6. 质量指标模块 (Metrics)](#6-质量指标模块-metrics)
- [7. Beta反馈模块 (Beta Feedback)](#7-beta反馈模块-beta-feedback)
- [8. 管理后台模块 (Admin)](#8-管理后台模块-admin)
- [9. 健康检查 (Health Check)](#9-健康检查-health-check)
- [10. 算法调用链路图](#10-算法调用链路图)

---

## API 概览

| 模块 | 接口数量 | 认证要求 | 说明 |
|------|---------|---------|------|
| 认证模块 | 2 | 无 | 用户注册、登录 |
| 分析任务 | 1 | JWT | 创建分析任务 |
| 任务状态 | 3 | JWT | 查询任务状态、SSE流、队列统计 |
| 报告模块 | 2 | JWT | 获取分析报告 |
| 洞察卡片 | 2 | JWT | 获取洞察卡片列表和详情 |
| 质量指标 | 1 | JWT | 获取质量指标 |
| Beta反馈 | 1 | JWT | 提交Beta反馈 |
| 管理后台 | 13 | Admin JWT | 仪表盘、社区管理、反馈管理 |
| 健康检查 | 2 | 无 | 健康检查、运行时诊断 |
| **总计** | **27** | - | - |

---

## 通用说明

### 认证方式

所有需要认证的接口使用 **JWT Bearer Token**：

```http
Authorization: Bearer <access_token>
```

### 响应格式

#### 成功响应
```json
{
  "data": { ... },
  "code": 0,
  "trace_id": "abc123..."
}
```

#### 错误响应
```json
{
  "detail": "错误描述",
  "status_code": 400
}
```

### 通用错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或Token无效 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 1. 认证模块 (Authentication)

### 1.1 用户注册

**接口**: `POST /api/auth/register`  
**认证**: 无  
**标签**: `auth`

#### 请求体

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "membership_level": "free"
}
```

**字段说明**:
- `email` (string, required): 用户邮箱
- `password` (string, required): 密码
- `membership_level` (string, optional): 会员等级，默认 `free`，可选 `free|pro|enterprise`

#### 响应 (201 Created)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-10-23T10:00:00Z",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "membership_level": "free"
  }
}
```

#### 错误响应

- `409 Conflict`: 邮箱已注册

```json
{
  "detail": "Email is already registered"
}
```

---

### 1.2 用户登录

**接口**: `POST /api/auth/login`  
**认证**: 无  
**标签**: `auth`

#### 请求体

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### 响应 (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-10-23T10:00:00Z",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "membership_level": "free"
  }
}
```

#### 错误响应

- `401 Unauthorized`: 邮箱或密码错误

```json
{
  "detail": "Invalid email or password"
}
```

---

## 2. 分析任务模块 (Analysis)

### 2.1 创建分析任务

**接口**: `POST /api/analyze`  
**认证**: JWT  
**标签**: `analysis`

#### 请求体

```json
{
  "product_description": "一款帮助开发者快速构建API的SaaS工具"
}
```

**字段说明**:
- `product_description` (string, required): 产品描述，用于分析

#### 响应 (201 Created)

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2025-10-22T10:00:00Z",
  "estimated_completion": "2025-10-22T10:05:00Z",
  "sse_endpoint": "/api/analyze/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

**响应头**:
```http
Location: /api/analyze/stream/550e8400-e29b-41d4-a716-446655440000
```

#### 错误响应

- `401 Unauthorized`: Token无效
- `404 Not Found`: 用户不存在
- `503 Service Unavailable`: 分析队列不可用

---

## 3. 任务状态模块 (Task Status)

### 3.1 获取任务状态

**接口**: `GET /api/status/{task_id}`  
**认证**: JWT  
**标签**: `status`

#### 路径参数

- `task_id` (UUID, required): 任务ID

#### 响应 (200 OK)

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 50,
  "message": "正在并行采集数据...",
  "error": null,
  "retry_count": 0,
  "failure_category": null,
  "last_retry_at": null,
  "dead_letter_at": null,
  "updated_at": "2025-10-22T10:02:30Z"
}
```

**状态枚举**:
- `pending`: 任务排队中
- `processing`: 任务正在处理
- `completed`: 分析完成
- `failed`: 任务失败

#### 错误响应

- `404 Not Found`: 任务不存在
- `403 Forbidden`: 无权访问该任务

---

### 3.2 SSE实时进度流

**接口**: `GET /api/analyze/stream/{task_id}`  
**认证**: JWT  
**标签**: `analysis`  
**响应类型**: `text/event-stream`

#### 路径参数

- `task_id` (UUID, required): 任务ID

#### SSE事件流

```
event: connected
data: {"task_id": "550e8400-e29b-41d4-a716-446655440000"}

event: progress
data: {"task_id": "550e8400-...", "status": "processing", "progress": 25, "message": "正在发现相关社区...", "updated_at": "2025-10-22T10:01:00Z"}

event: progress
data: {"task_id": "550e8400-...", "status": "processing", "progress": 50, "message": "正在并行采集数据...", "updated_at": "2025-10-22T10:02:00Z"}

event: completed
data: {"task_id": "550e8400-...", "status": "completed", "progress": 100, "message": "分析完成", "updated_at": "2025-10-22T10:05:00Z"}

event: close
data: {"task_id": "550e8400-e29b-41d4-a716-446655440000"}
```

**事件类型**:
- `connected`: 连接建立
- `progress`: 进度更新
- `completed`: 任务完成
- `error`: 任务失败
- `heartbeat`: 心跳（每30秒）
- `close`: 连接关闭

---

## 5. 洞察卡片模块 (Insights)

### 5.1 获取洞察卡片列表

**接口**: `GET /api/insights`
**认证**: JWT
**标签**: `insights`

#### 查询参数

- `task_id` (UUID, optional): 按任务ID过滤
- `entity_filter` (string, optional): 按实体过滤（暂未实现）
- `limit` (integer, optional): 每页数量，默认10，范围1-100
- `offset` (integer, optional): 偏移量，默认0

#### 响应 (200 OK)

```json
{
  "total": 50,
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "API文档自动化需求强烈",
      "summary": "在r/webdev等社区中，开发者频繁提到API文档维护困难...",
      "confidence": 0.85,
      "time_window_days": 30,
      "subreddits": ["r/webdev", "r/programming"],
      "evidences": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440000",
          "post_url": "https://reddit.com/r/webdev/comments/...",
          "excerpt": "我们团队在API文档上花费了太多时间...",
          "timestamp": "2025-10-20T15:30:00Z",
          "subreddit": "r/webdev",
          "score": 0.9
        }
      ],
      "created_at": "2025-10-22T10:05:00Z",
      "updated_at": "2025-10-22T10:05:00Z"
    }
  ]
}
```

#### 错误响应

- `404 Not Found`: 任务不存在
- `403 Forbidden`: 无权访问该任务

---

### 5.2 获取单个洞察卡片

**接口**: `GET /api/insights/{insight_id}`
**认证**: JWT
**标签**: `insights`

#### 路径参数

- `insight_id` (UUID, required): 洞察卡片ID

#### 响应 (200 OK)

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "API文档自动化需求强烈",
  "summary": "在r/webdev等社区中，开发者频繁提到API文档维护困难...",
  "confidence": 0.85,
  "time_window_days": 30,
  "subreddits": ["r/webdev", "r/programming"],
  "evidences": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440000",
      "post_url": "https://reddit.com/r/webdev/comments/...",
      "excerpt": "我们团队在API文档上花费了太多时间...",
      "timestamp": "2025-10-20T15:30:00Z",
      "subreddit": "r/webdev",
      "score": 0.9
    }
  ],
  "created_at": "2025-10-22T10:05:00Z",
  "updated_at": "2025-10-22T10:05:00Z"
}
```

#### 错误响应

- `404 Not Found`: 洞察卡片不存在
- `403 Forbidden`: 无权访问该洞察卡片

---

## 6. 质量指标模块 (Metrics)

### 6.1 获取质量指标

**接口**: `GET /api/metrics`
**认证**: JWT
**标签**: `metrics`

#### 查询参数

- `start_date` (date, optional): 开始日期，默认7天前，格式：YYYY-MM-DD
- `end_date` (date, optional): 结束日期，默认今天，格式：YYYY-MM-DD

#### 请求示例

```http
GET /api/metrics?start_date=2025-10-15&end_date=2025-10-21
```

#### 响应 (200 OK)

```json
[
  {
    "date": "2025-10-15",
    "collection_success_rate": 0.93,
    "deduplication_rate": 0.15,
    "processing_time_p50": 120.5,
    "processing_time_p95": 180.2
  },
  {
    "date": "2025-10-16",
    "collection_success_rate": 0.95,
    "deduplication_rate": 0.12,
    "processing_time_p50": 115.3,
    "processing_time_p95": 175.8
  }
]
```

**字段说明**:
- `collection_success_rate`: 数据采集成功率 (0.0-1.0)
- `deduplication_rate`: 去重率 (0.0-1.0)
- `processing_time_p50`: 处理时间中位数（秒）
- `processing_time_p95`: 处理时间95分位数（秒）

---

## 7. Beta反馈模块 (Beta Feedback)

### 7.1 提交Beta反馈

**接口**: `POST /api/beta/feedback`
**认证**: JWT
**标签**: `beta`

#### 请求体

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "satisfaction": 4,
  "missing_communities": ["r/golang", "r/rust"],
  "comments": "分析结果很准确，但希望能覆盖更多技术社区"
}
```

**字段说明**:
- `task_id` (UUID, required): 任务ID
- `satisfaction` (integer, required): 满意度评分，范围1-5
- `missing_communities` (array, optional): 缺失的社区列表
- `comments` (string, optional): 反馈意见

#### 响应 (201 Created)

```json
{
  "code": 0,
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "990e8400-e29b-41d4-a716-446655440000",
    "satisfaction": 4,
    "missing_communities": ["r/golang", "r/rust"],
    "comments": "分析结果很准确，但希望能覆盖更多技术社区",
    "created_at": "2025-10-22T10:10:00Z"
  },
  "trace_id": "abc123..."
}
```

#### 错误响应

- `404 Not Found`: 任务不存在
- `403 Forbidden`: 任务不属于当前用户

---

## 8. 管理后台模块 (Admin)

### 8.1 仪表盘统计

**接口**: `GET /api/admin/dashboard/stats`
**认证**: Admin JWT
**标签**: `admin`

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "total_users": 1250,
    "total_tasks": 5680,
    "tasks_today": 45,
    "tasks_completed_today": 38,
    "avg_processing_time": 125.5,
    "cache_hit_rate": 0.92,
    "active_workers": 3
  },
  "trace_id": "abc123..."
}
```

---

### 8.2 最近任务列表

**接口**: `GET /api/admin/tasks/recent`
**认证**: Admin JWT
**标签**: `admin`

#### 查询参数

- `limit` (integer, optional): 返回数量，默认50，范围1-200

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_email": "user@example.com",
        "status": "completed",
        "created_at": "2025-10-22T10:00:00Z",
        "completed_at": "2025-10-22T10:05:00Z",
        "processing_seconds": 300.5,
        "confidence_score": 0.85,
        "analysis_version": "1.0",
        "posts_analyzed": 1500,
        "cache_hit_rate": 0.92,
        "communities_count": 10,
        "reddit_api_calls": 50,
        "pain_points_count": 8,
        "competitors_count": 5,
        "opportunities_count": 12
      }
    ],
    "total": 50
  },
  "trace_id": "abc123..."
}
```

---

### 8.3 活跃用户列表

**接口**: `GET /api/admin/users/active`
**认证**: Admin JWT
**标签**: `admin`

#### 查询参数

- `limit` (integer, optional): 返回数量，默认50，范围1-200

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "user_id": "990e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "tasks_last_7_days": 15,
        "last_task_at": "2025-10-22T09:30:00Z"
      }
    ],
    "total": 50
  },
  "trace_id": "abc123..."
}
```

---

### 8.4 社区验收列表

**接口**: `GET /api/admin/communities/summary`
**认证**: Admin JWT
**标签**: `admin`

#### 查询参数

- `q` (string, optional): 搜索关键词
- `status` (string, optional): 状态筛选，可选 `green|yellow|red`
- `tag` (string, optional): 标签筛选
- `sort` (string, optional): 排序方式，默认 `cscore_desc`，可选 `cscore_desc|hit_desc`
- `page` (integer, optional): 页码，默认1
- `page_size` (integer, optional): 每页数量，默认50，范围1-200

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "community": "r/webdev",
        "hit_7d": 250,
        "last_crawled_at": "2025-10-22T09:00:00Z",
        "dup_ratio": 0.12,
        "spam_ratio": 0.0,
        "topic_score": 0.85,
        "c_score": 85,
        "status_color": "green",
        "labels": ["状态:正常", "质量:优秀"]
      }
    ],
    "total": 100
  },
  "trace_id": "abc123..."
}
```

---

### 8.5 下载社区导入模板

**接口**: `GET /api/admin/communities/template`
**认证**: Admin JWT
**标签**: `admin`

#### 响应 (200 OK)

返回Excel文件（.xlsx格式）

**响应头**:
```http
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="community_template.xlsx"
```

---

### 8.6 上传并导入社区

**接口**: `POST /api/admin/communities/import`
**认证**: Admin JWT
**标签**: `admin`
**Content-Type**: `multipart/form-data`

#### 请求体

- `file` (file, required): Excel模板文件（.xlsx）
- `dry_run` (boolean, optional): true=仅验证，false=验证并导入，默认false

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "success": true,
    "imported_count": 25,
    "skipped_count": 3,
    "errors": []
  },
  "trace_id": "abc123..."
}
```

---

### 8.7 查询社区导入历史

**接口**: `GET /api/admin/communities/import-history`
**认证**: Admin JWT
**标签**: `admin`

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "aa0e8400-e29b-41d4-a716-446655440000",
        "filename": "communities_2025-10-22.xlsx",
        "imported_count": 25,
        "imported_at": "2025-10-22T08:00:00Z",
        "imported_by": "admin@example.com"
      }
    ],
    "total": 10
  },
  "trace_id": "abc123..."
}
```

---

### 8.8 查看社区池

**接口**: `GET /api/admin/communities/pool`
**认证**: Admin JWT
**标签**: `admin`

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "name": "r/webdev",
        "tier": "high",
        "categories": {"technology": true, "web": true},
        "description_keywords": {"api": true, "development": true},
        "daily_posts": 500,
        "avg_comment_length": 150,
        "quality_score": 0.85,
        "priority": "high",
        "user_feedback_count": 10,
        "discovered_count": 5,
        "is_active": true
      }
    ],
    "total": 200
  },
  "trace_id": "abc123..."
}
```

---

### 8.9 查看待审核社区

**接口**: `GET /api/admin/communities/discovered`
**认证**: Admin JWT
**标签**: `admin`

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "name": "r/golang",
        "discovered_from_keywords": {"go": true, "backend": true},
        "discovered_count": 3,
        "first_discovered_at": "2025-10-20T10:00:00Z",
        "last_discovered_at": "2025-10-22T09:00:00Z",
        "status": "pending"
      }
    ],
    "total": 15
  },
  "trace_id": "abc123..."
}
```

---

### 8.10 批准社区

**接口**: `POST /api/admin/communities/approve`
**认证**: Admin JWT
**标签**: `admin`

#### 请求体

```json
{
  "name": "r/golang",
  "tier": "medium",
  "categories": {"technology": true, "programming": true},
  "admin_notes": "优质技术社区，批准加入"
}
```

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "approved": "r/golang",
    "pool_is_active": true
  },
  "trace_id": "abc123..."
}
```

---

### 8.11 拒绝社区

**接口**: `POST /api/admin/communities/reject`
**认证**: Admin JWT
**标签**: `admin`

#### 请求体

```json
{
  "name": "r/spam_community",
  "admin_notes": "内容质量低，不符合标准"
}
```

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "rejected": "r/spam_community"
  },
  "trace_id": "abc123..."
}
```

---

### 8.12 禁用社区

**接口**: `DELETE /api/admin/communities/{name}`
**认证**: Admin JWT
**标签**: `admin`

#### 路径参数

- `name` (string, required): 社区名称（URL编码）

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "disabled": "r/webdev"
  },
  "trace_id": "abc123..."
}
```

---

### 8.13 查看Beta反馈列表

**接口**: `GET /api/admin/beta/feedback`
**认证**: Admin JWT
**标签**: `admin`

#### 响应 (200 OK)

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "bb0e8400-e29b-41d4-a716-446655440000",
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "990e8400-e29b-41d4-a716-446655440000",
        "satisfaction": 4,
        "missing_communities": ["r/golang"],
        "comments": "希望增加更多技术社区",
        "created_at": "2025-10-22T10:10:00Z"
      }
    ],
    "total": 50
  },
  "trace_id": "abc123..."
}
```

---

## 9. 健康检查 (Health Check)

### 9.1 健康检查

**接口**: `GET /api/healthz`
**认证**: 无
**标签**: `health`

#### 响应 (200 OK)

```json
{
  "status": "ok"
}
```

---

### 9.2 运行时诊断

**接口**: `GET /api/diag/runtime`
**认证**: 无
**标签**: `health`

#### 响应 (200 OK)

```json
{
  "has_reddit_client": true,
  "app_env": "production",
  "sse_base_path": "/api/analyze/stream"
}
```

---

### 9.3 任务诊断

**接口**: `GET /api/tasks/diag`
**认证**: JWT
**标签**: `tasks`

#### 响应 (200 OK)

```json
{
  "has_reddit_client": true,
  "environment": "production"
}
```

---

### 3.3 获取任务队列统计

**接口**: `GET /api/tasks/stats`  
**认证**: JWT  
**标签**: `tasks`

#### 响应 (200 OK)

```json
{
  "active_workers": 2,
  "active_tasks": 3,
  "reserved_tasks": 5,
  "scheduled_tasks": 10,
  "total_tasks": 18
}
```

---

## 4. 报告模块 (Reports)

### 4.1 获取分析报告

**接口**: `GET /api/report/{task_id}`  
**认证**: JWT  
**标签**: `analysis`

#### 路径参数

- `task_id` (UUID, required): 任务ID

#### 响应 (200 OK)

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "generated_at": "2025-10-22T10:05:00Z",
  "product_description": "一款帮助开发者快速构建API的SaaS工具",
  "report": {
    "executive_summary": {
      "total_communities": 10,
      "key_insights": 25,
      "top_opportunity": "开发者需要更快的API文档生成工具"
    },
    "pain_points": [
      {
        "description": "API文档维护困难",
        "frequency": 45,
        "sentiment_score": -0.6,
        "evidence": ["帖子链接1", "帖子链接2"]
      }
    ],
    "competitors": [
      {
        "name": "Postman",
        "mentions": 120,
        "sentiment": "positive",
        "strengths": ["易用性好", "功能丰富"],
        "weaknesses": ["价格较高"]
      }
    ],
    "opportunities": [
      {
        "description": "自动化API测试需求强烈",
        "confidence": 0.85,
        "market_size": "large",
        "evidence_count": 30
      }
    ],
    "action_items": [
      {
        "problem_definition": "开发者在API文档维护上花费大量时间",
        "evidence_chain": [
          {"post_url": "https://reddit.com/...", "excerpt": "..."},
          {"post_url": "https://reddit.com/...", "excerpt": "..."}
        ],
        "suggested_actions": [
          "开发自动文档生成功能",
          "集成主流框架"
        ],
        "confidence": 0.85,
        "urgency": 0.9,
        "product_fit": 0.95,
        "priority": 0.73
      }
    ]
  },
  "metadata": {
    "analysis_version": "1.0",
    "confidence_score": 0.85,
    "processing_time_seconds": 120.5,
    "cache_hit_rate": 0.92,
    "total_mentions": 1500
  },
  "overview": {
    "sentiment": {
      "positive": 45,
      "negative": 30,
      "neutral": 25
    },
    "top_communities": [
      {
        "name": "r/webdev",
        "mentions": 250,
        "relevance": 92,
        "members": 1200000,
        "category": "technology",
        "daily_posts": 500,
        "avg_comment_length": 150,
        "from_cache": true
      }
    ]
  },
  "stats": {
    "total_mentions": 1500,
    "positive_mentions": 675,
    "negative_mentions": 450,
    "neutral_mentions": 375
  }
}
```

#### 错误响应

- `404 Not Found`: 任务、分析或报告不存在
- `403 Forbidden`: 无权访问该任务
- `409 Conflict`: 任务尚未完成

---

### 4.2 OPTIONS预检请求

**接口**: `OPTIONS /api/report/{task_id}`  
**认证**: 无  
**标签**: `analysis`

用于CORS预检请求。

#### 响应 (204 No Content)

---


