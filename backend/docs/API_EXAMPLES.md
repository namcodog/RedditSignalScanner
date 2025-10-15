# Reddit Signal Scanner API Examples

This document provides concrete request/response snippets for the four core
endpoints delivered by Backend A on Day 5. All examples assume the FastAPI app
is running locally on `http://localhost:8000` and that you already possess a
valid JWT access token (`{TOKEN}`).

> **Headers used below**
>
> ```
> Authorization: Bearer {TOKEN}
> Content-Type: application/json
> Accept: application/json
> ```

---

## 1. Create Analysis Task — `POST /api/analyze`

### Request

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "一款 AI 驱动的笔记应用，帮助研究者自动组织和连接想法"
  }'
```

### Successful Response — `201 Created`

```json
{
  "task_id": "9742949d-853d-4f1c-9f85-8e0f56684474",
  "status": "pending",
  "created_at": "2025-10-11T01:05:43.921000+00:00",
  "estimated_completion": "2025-10-11T01:10:43.921000+00:00",
  "sse_endpoint": "/api/analyze/stream/9742949d-853d-4f1c-9f85-8e0f56684474"
}
```

### Error Responses

- `400 Bad Request` — product description fails validation.
- `401 Unauthorized` — token missing/invalid.
- `404 Not Found` — token subject does not map to an existing user.

---

## 2. Poll Task Status — `GET /api/status/{task_id}`

### Request

```bash
curl http://localhost:8000/api/status/9742949d-853d-4f1c-9f85-8e0f56684474 \
  -H "Authorization: Bearer {TOKEN}"
```

### Successful Response — `200 OK`

```json
{
  "task_id": "9742949d-853d-4f1c-9f85-8e0f56684474",
  "status": "processing",
  "progress": 50,
  "message": "任务正在处理",
  "error": null,
  "retry_count": 0,
  "failure_category": null,
  "last_retry_at": null,
  "dead_letter_at": null,
  "updated_at": "2025-10-11T01:07:12.203000+00:00"
}
```

### Error Responses

- `401 Unauthorized` — token invalid.
- `403 Forbidden` — task belongs to another user.
- `404 Not Found` — task id not recognised.

---

## 3. Stream Task Progress — `GET /api/analyze/stream/{task_id}`

### Request (keep connection open)

```bash
curl -N http://localhost:8000/api/analyze/stream/9742949d-853d-4f1c-9f85-8e0f56684474 \
  -H "Authorization: Bearer {TOKEN}"
```

### Event Stream (SSE)

```
event: connected
data: {"task_id": "9742949d-853d-4f1c-9f85-8e0f56684474"}

event: progress
data: {
  "task_id": "9742949d-853d-4f1c-9f85-8e0f56684474",
  "status": "processing",
  "progress": 50,
  "message": "任务正在处理",
  "error": null,
  "updated_at": "2025-10-11T01:07:12.203000+00:00"
}

event: completed
data: {
  "task_id": "9742949d-853d-4f1c-9f85-8e0f56684474",
  "status": "completed",
  "progress": 100,
  "message": "分析完成",
  "error": null,
  "updated_at": "2025-10-11T01:09:54.880000+00:00"
}

event: close
data: {"task_id": "9742949d-853d-4f1c-9f85-8e0f56684474"}
```

### Error Responses

- `403 Forbidden` — cross-tenant access attempt.
- `404 Not Found` — task id invalid.

---

## 4. Fetch Analysis Report — `GET /api/report/{task_id}`

### Request

```bash
curl http://localhost:8000/api/report/9742949d-853d-4f1c-9f85-8e0f56684474 \
  -H "Authorization: Bearer {TOKEN}"
```

### Successful Response — `200 OK`

```json
{
  "task_id": "9742949d-853d-4f1c-9f85-8e0f56684474",
  "status": "completed",
  "analysis": {
    "id": "a3a3597b-130c-4c7a-a68a-69073cf7d4f8",
    "task_id": "9742949d-853d-4f1c-9f85-8e0f56684474",
    "insights": {
      "pain_points": [],
      "competitors": [],
      "opportunities": []
    },
    "sources": {
      "communities": [],
      "posts_analyzed": 0,
      "cache_hit_rate": 0.0,
      "analysis_duration_seconds": null,
      "reddit_api_calls": null
    },
    "confidence_score": null,
    "analysis_version": "1.0",
    "created_at": "2025-10-11T01:09:54.880000+00:00"
  },
  "report": {
    "id": "49b70d8c-0d70-4d78-8ad1-df5f83d0a70f",
    "analysis_id": "a3a3597b-130c-4c7a-a68a-69073cf7d4f8",
    "html_content": "<html>report</html>",
    "template_version": "1.0",
    "generated_at": "2025-10-11T01:09:54.880000+00:00"
  }
}
```

### Error Responses

- `403 Forbidden` — task owned by another user.
- `404 Not Found` — task/analysis/report missing.
- `409 Conflict` — task has not yet completed.

---

## Authentication Notes

- All endpoints require Bearer tokens signed with the project JWT secret.
- For Day 5 hand-off, run `python scripts/generate_test_token.py` (see section 2
  in the Day 5 task assignment) to obtain two pre-generated test users and their
  tokens.
- Tokens default to a seven-day validity window. Regenerate as needed for local
  testing; never reuse them in production environments.

---

## 5. Admin — Community Excel Import

> 需要使用 Admin 账户（见 `ADMIN_EMAILS` 配置）获取的 Token。

### 5.1 下载 Excel 模板 — `GET /api/admin/communities/template`

```bash
curl -L http://localhost:8000/api/admin/communities/template \
  -H "Authorization: Bearer {ADMIN_TOKEN}" \
  --output community_template.xlsx
```

成功响应返回 Excel (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)。

### 5.2 上传并导入 — `POST /api/admin/communities/import`

```bash
curl -X POST http://localhost:8000/api/admin/communities/import \
  -H "Authorization: Bearer {ADMIN_TOKEN}" \
  -F "file=@/path/to/communities.xlsx" \
  -F "dry_run=false"
```

#### 成功响应（`200 OK`）

```json
{
  "code": 0,
  "data": {
    "status": "success",
    "summary": {
      "total": 3,
      "valid": 3,
      "invalid": 0,
      "duplicates": 0,
      "imported": 3
    },
    "communities": [
      {"name": "r/startups", "tier": "gold", "status": "imported"},
      {"name": "r/Entrepreneur", "tier": "gold", "status": "imported"},
      {"name": "r/SaaS", "tier": "silver", "status": "imported"}
    ]
  },
  "trace_id": "1f2e3d4c5b6a"
}
```

#### 验证失败示例（`200 OK`，`status=error`）

```json
{
  "code": 0,
  "data": {
    "status": "error",
    "summary": {
      "total": 2,
      "valid": 1,
      "invalid": 1,
      "duplicates": 0,
      "imported": 0
    },
    "communities": [
      {"name": "startups", "tier": "premium", "status": "invalid"},
      {"name": "r/Existing", "tier": "gold", "status": "validated"}
    ],
    "errors": [
      {
        "row": 2,
        "field": "name",
        "value": "startups",
        "error": "社区名称必须以 r/ 开头"
      },
      {
        "row": 2,
        "field": "tier",
        "value": "premium",
        "error": "tier 必须是 seed/gold/silver/admin 之一"
      }
    ]
  },
  "trace_id": "9c8b7a6d5e4f"
}
```

### 5.3 查看导入历史 — `GET /api/admin/communities/import-history`

```bash
curl http://localhost:8000/api/admin/communities/import-history \
  -H "Authorization: Bearer {ADMIN_TOKEN}"
```

#### 响应示例

```json
{
  "code": 0,
  "data": {
    "imports": [
      {
        "id": 2,
        "filename": "communities.xlsx",
        "uploaded_by": "admin@example.com",
        "uploaded_at": "2025-10-15T02:20:45.931000+00:00",
        "dry_run": false,
        "status": "success",
        "summary": {
          "total": 3,
          "valid": 3,
          "invalid": 0,
          "duplicates": 0,
          "imported": 3
        }
      }
    ]
  },
  "trace_id": "7b6c5d4e3f2a"
}
```
