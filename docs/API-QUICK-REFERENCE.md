# Reddit Signal Scanner - API 快速索引

**版本**: v0.1.0  
**生成时间**: 2025-10-22  
**基础路径**: `/api`

---

## 快速导航

- [认证相关](#认证相关) (2个接口)
- [分析任务](#分析任务) (4个接口)
- [报告与洞察](#报告与洞察) (5个接口)
- [管理后台](#管理后台) (13个接口)
- [系统监控](#系统监控) (3个接口)

---

## 认证相关

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | 无 |
| POST | `/api/auth/login` | 用户登录 | 无 |

---

## 分析任务

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/analyze` | 创建分析任务 | JWT |
| GET | `/api/status/{task_id}` | 获取任务状态 | JWT |
| GET | `/api/analyze/stream/{task_id}` | SSE实时进度流 | JWT |
| GET | `/api/tasks/stats` | 获取任务队列统计 | JWT |

---

## 报告与洞察

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/report/{task_id}` | 获取分析报告 | JWT |
| OPTIONS | `/api/report/{task_id}` | CORS预检 | 无 |
| GET | `/api/insights` | 获取洞察卡片列表 | JWT |
| GET | `/api/insights/{insight_id}` | 获取单个洞察卡片 | JWT |
| GET | `/api/metrics` | 获取质量指标 | JWT |

---

## 管理后台

### 仪表盘

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/admin/dashboard/stats` | 仪表盘统计 | Admin |
| GET | `/api/admin/tasks/recent` | 最近任务列表 | Admin |
| GET | `/api/admin/users/active` | 活跃用户列表 | Admin |

### 社区管理

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/admin/communities/summary` | 社区验收列表 | Admin |
| GET | `/api/admin/communities/template` | 下载导入模板 | Admin |
| POST | `/api/admin/communities/import` | 上传并导入社区 | Admin |
| GET | `/api/admin/communities/import-history` | 导入历史 | Admin |
| GET | `/api/admin/communities/pool` | 查看社区池 | Admin |
| GET | `/api/admin/communities/discovered` | 查看待审核社区 | Admin |
| POST | `/api/admin/communities/approve` | 批准社区 | Admin |
| POST | `/api/admin/communities/reject` | 拒绝社区 | Admin |
| DELETE | `/api/admin/communities/{name}` | 禁用社区 | Admin |

### Beta反馈

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/beta/feedback` | 提交Beta反馈 | JWT |
| GET | `/api/admin/beta/feedback` | 查看反馈列表 | Admin |

---

## 系统监控

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/healthz` | 健康检查 | 无 |
| GET | `/api/diag/runtime` | 运行时诊断 | 无 |
| GET | `/api/tasks/diag` | 任务诊断 | JWT |

---

## 完整接口列表（按模块分类）

### 1. 认证模块 (auth)

```
POST   /api/auth/register          # 用户注册
POST   /api/auth/login             # 用户登录
```

### 2. 分析任务模块 (analysis)

```
POST   /api/analyze                # 创建分析任务
GET    /api/analyze/stream/{id}    # SSE实时进度流
```

### 3. 任务状态模块 (status)

```
GET    /api/status/{task_id}       # 获取任务状态
GET    /api/tasks/stats            # 获取队列统计
GET    /api/tasks/diag             # 任务诊断
```

### 4. 报告模块 (reports)

```
GET    /api/report/{task_id}       # 获取分析报告
OPTIONS /api/report/{task_id}      # CORS预检
```

### 5. 洞察卡片模块 (insights)

```
GET    /api/insights               # 获取洞察卡片列表
GET    /api/insights/{id}          # 获取单个洞察卡片
```

### 6. 质量指标模块 (metrics)

```
GET    /api/metrics                # 获取质量指标
```

### 7. Beta反馈模块 (beta)

```
POST   /api/beta/feedback          # 提交Beta反馈
```

### 8. 管理后台 - 仪表盘 (admin)

```
GET    /api/admin/dashboard/stats  # 仪表盘统计
GET    /api/admin/tasks/recent     # 最近任务列表
GET    /api/admin/users/active     # 活跃用户列表
```

### 9. 管理后台 - 社区管理 (admin)

```
GET    /api/admin/communities/summary         # 社区验收列表
GET    /api/admin/communities/template        # 下载导入模板
POST   /api/admin/communities/import          # 上传并导入社区
GET    /api/admin/communities/import-history  # 导入历史
GET    /api/admin/communities/pool            # 查看社区池
GET    /api/admin/communities/discovered      # 查看待审核社区
POST   /api/admin/communities/approve         # 批准社区
POST   /api/admin/communities/reject          # 拒绝社区
DELETE /api/admin/communities/{name}          # 禁用社区
```

### 10. 管理后台 - Beta反馈 (admin)

```
GET    /api/admin/beta/feedback    # 查看反馈列表
```

### 11. 健康检查 (health)

```
GET    /api/healthz                # 健康检查
GET    /api/diag/runtime           # 运行时诊断
```

---

## 按HTTP方法分类

### GET 请求 (20个)

```
/api/status/{task_id}
/api/analyze/stream/{task_id}
/api/tasks/stats
/api/tasks/diag
/api/report/{task_id}
/api/insights
/api/insights/{insight_id}
/api/metrics
/api/admin/dashboard/stats
/api/admin/tasks/recent
/api/admin/users/active
/api/admin/communities/summary
/api/admin/communities/template
/api/admin/communities/import-history
/api/admin/communities/pool
/api/admin/communities/discovered
/api/admin/beta/feedback
/api/healthz
/api/diag/runtime
```

### POST 请求 (6个)

```
/api/auth/register
/api/auth/login
/api/analyze
/api/beta/feedback
/api/admin/communities/import
/api/admin/communities/approve
/api/admin/communities/reject
```

### DELETE 请求 (1个)

```
/api/admin/communities/{name}
```

### OPTIONS 请求 (1个)

```
/api/report/{task_id}
```

---

## 认证要求分类

### 无需认证 (5个)

```
POST   /api/auth/register
POST   /api/auth/login
OPTIONS /api/report/{task_id}
GET    /api/healthz
GET    /api/diag/runtime
```

### 需要JWT认证 (9个)

```
POST   /api/analyze
GET    /api/status/{task_id}
GET    /api/analyze/stream/{task_id}
GET    /api/tasks/stats
GET    /api/tasks/diag
GET    /api/report/{task_id}
GET    /api/insights
GET    /api/insights/{insight_id}
GET    /api/metrics
POST   /api/beta/feedback
```

### 需要Admin认证 (13个)

```
GET    /api/admin/dashboard/stats
GET    /api/admin/tasks/recent
GET    /api/admin/users/active
GET    /api/admin/communities/summary
GET    /api/admin/communities/template
POST   /api/admin/communities/import
GET    /api/admin/communities/import-history
GET    /api/admin/communities/pool
GET    /api/admin/communities/discovered
POST   /api/admin/communities/approve
POST   /api/admin/communities/reject
DELETE /api/admin/communities/{name}
GET    /api/admin/beta/feedback
```

---

## 常用场景示例

### 场景1：用户注册并创建分析任务

```bash
# 1. 注册
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}

# 2. 创建分析任务
POST /api/analyze
Authorization: Bearer <token>
{
  "product_description": "一款帮助开发者快速构建API的SaaS工具"
}

# 3. 监听SSE进度
GET /api/analyze/stream/{task_id}
Authorization: Bearer <token>

# 4. 获取报告
GET /api/report/{task_id}
Authorization: Bearer <token>
```

### 场景2：管理员查看系统状态

```bash
# 1. 登录（管理员账号）
POST /api/auth/login
{
  "email": "admin@example.com",
  "password": "AdminPassword123!"
}

# 2. 查看仪表盘
GET /api/admin/dashboard/stats
Authorization: Bearer <admin_token>

# 3. 查看最近任务
GET /api/admin/tasks/recent?limit=50
Authorization: Bearer <admin_token>

# 4. 查看社区验收列表
GET /api/admin/communities/summary?page=1&page_size=50
Authorization: Bearer <admin_token>
```

### 场景3：前端轮询任务状态

```bash
# 1. 创建任务后获得task_id
POST /api/analyze
→ 返回 task_id

# 2. 轮询任务状态（每2秒）
GET /api/status/{task_id}
Authorization: Bearer <token>

# 3. 当status=completed时，获取报告
GET /api/report/{task_id}
Authorization: Bearer <token>
```

---

## 错误码快速参考

| 状态码 | 说明 | 常见原因 |
|--------|------|----------|
| 200 | 成功 | - |
| 201 | 创建成功 | 注册、创建任务 |
| 204 | 无内容 | OPTIONS预检 |
| 400 | 请求参数错误 | 缺少必填字段、格式错误 |
| 401 | 未认证 | Token缺失或无效 |
| 403 | 无权限 | 非管理员访问管理接口、访问他人任务 |
| 404 | 资源不存在 | 任务、用户、社区不存在 |
| 409 | 资源冲突 | 邮箱已注册、任务未完成 |
| 500 | 服务器错误 | 内部错误 |
| 503 | 服务不可用 | Celery队列不可用 |

---

## 前端联调检查清单

### 认证流程
- [ ] 注册接口正常
- [ ] 登录接口正常
- [ ] Token存储到localStorage
- [ ] 请求头自动添加Authorization

### 分析任务流程
- [ ] 创建任务接口正常
- [ ] SSE连接建立成功
- [ ] 进度事件正常接收
- [ ] 完成事件触发报告获取
- [ ] 报告数据正确展示

### 错误处理
- [ ] 401错误跳转登录页
- [ ] 403错误提示无权限
- [ ] 404错误提示资源不存在
- [ ] 网络错误友好提示

### 管理后台
- [ ] 管理员权限验证
- [ ] 仪表盘数据正确
- [ ] 社区管理功能正常
- [ ] Excel导入导出正常

---

**总计**: 27个API接口  
**文档更新**: 2025-10-22  
**详细文档**: 参见 `API-REFERENCE.md`  
**算法文档**: 参见 `ALGORITHM-FLOW.md`

