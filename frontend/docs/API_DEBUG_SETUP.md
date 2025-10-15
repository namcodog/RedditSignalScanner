# API 调试工具准备文档

> **创建日期**: 2025-10-10 Day 4
> **用途**: Day 5 API 对接准备

---

## 📋 概述

本文档描述前端开发者在 Day 5 API 对接时需要准备的调试工具和环境。

---

## 🛠️ 调试工具清单

### 1. VS Code 扩展

#### Thunder Client（推荐）
- **用途**: 轻量级 API 测试工具，集成在 VS Code 中
- **安装**: VS Code Extensions → 搜索 "Thunder Client"
- **优点**: 
  - ✅ 无需离开编辑器
  - ✅ 支持环境变量
  - ✅ 支持 SSE 测试
  - ✅ 可保存请求历史

#### REST Client
- **用途**: 在 `.http` 文件中编写和执行 HTTP 请求
- **安装**: VS Code Extensions → 搜索 "REST Client"
- **优点**:
  - ✅ 请求即代码，可版本控制
  - ✅ 支持变量和环境
  - ✅ 语法简洁

---

### 2. 浏览器工具

#### Chrome DevTools
- **用途**: 
  - 查看网络请求
  - 调试 SSE 连接
  - 查看 LocalStorage
- **快捷键**: `F12` 或 `Cmd+Option+I` (Mac)

#### EventSource Monitor（Chrome 扩展）
- **用途**: 监控 SSE 连接和事件
- **安装**: Chrome Web Store → 搜索 "EventSource Monitor"

---

### 3. 命令行工具

#### curl
- **用途**: 快速测试 API 端点
- **示例**:
  ```bash
  # 测试创建任务
  curl -X POST http://localhost:8000/api/analyze \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer {token}" \
    -d '{"productDescription": "测试产品描述，至少10个字符"}'
  
  # 测试 SSE 连接
  curl -N http://localhost:8000/api/analyze/stream/{task_id} \
    -H "Authorization: Bearer {token}"
  ```

#### httpie（可选）
- **用途**: 更友好的 HTTP 客户端
- **安装**: `brew install httpie`
- **示例**:
  ```bash
  http POST localhost:8000/api/analyze \
    productDescription="测试产品" \
    Authorization:"Bearer {token}"
  ```

---

## 📝 API 测试准备

### 1. 创建测试请求集合

创建 `frontend/api-tests/` 目录，存放测试请求：

```
frontend/api-tests/
├── auth.http           # 认证相关请求
├── analyze.http        # 分析任务请求
├── sse-test.http       # SSE 连接测试
└── README.md           # 使用说明
```

---

### 2. 环境变量配置

创建 `frontend/api-tests/.env` 文件：

```bash
# API 基础 URL
API_BASE_URL=http://localhost:8000

# 测试用户凭证（Day 5 交接会获取）
TEST_EMAIL=test@example.com
TEST_PASSWORD=testpassword123

# 测试 Token（Day 5 交接会获取）
TEST_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# 测试任务 ID（Day 5 交接会获取）
TEST_TASK_ID=123e4567-e89b-12d3-a456-426614174000
```

---

### 3. REST Client 请求示例

创建 `frontend/api-tests/auth.http`:

```http
### 变量定义
@baseUrl = http://localhost:8000
@email = test@example.com
@password = testpassword123

### 用户注册
POST {{baseUrl}}/api/auth/register
Content-Type: application/json

{
  "email": "{{email}}",
  "password": "{{password}}"
}

### 用户登录
POST {{baseUrl}}/api/auth/login
Content-Type: application/json

{
  "email": "{{email}}",
  "password": "{{password}}"
}

### 获取当前用户
GET {{baseUrl}}/api/auth/me
Authorization: Bearer {{token}}
```

创建 `frontend/api-tests/analyze.http`:

```http
### 变量定义
@baseUrl = http://localhost:8000
@token = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

### 创建分析任务
POST {{baseUrl}}/api/analyze
Content-Type: application/json
Authorization: Bearer {{token}}

{
  "productDescription": "AI笔记应用，帮助研究者自动组织和连接想法，支持多种格式导入导出"
}

### 查询任务状态
GET {{baseUrl}}/api/status/{{taskId}}
Authorization: Bearer {{token}}

### 获取分析报告
GET {{baseUrl}}/api/report/{{taskId}}
Authorization: Bearer {{token}}
```

---

## 🔍 SSE 调试方法

### 方法 1: curl 命令

```bash
# 连接 SSE 端点
curl -N http://localhost:8000/api/analyze/stream/{task_id} \
  -H "Authorization: Bearer {token}"

# 输出示例:
# event: connected
# data: {"taskId":"123e4567-e89b-12d3-a456-426614174000"}
#
# event: progress
# data: {"status":"processing","percentage":25,"currentStep":"社区发现"}
```

### 方法 2: Chrome DevTools

1. 打开 Chrome DevTools (`F12`)
2. 切换到 **Network** 标签
3. 筛选 **EventSource** 类型
4. 点击 SSE 请求，查看 **EventStream** 标签
5. 实时查看接收到的事件

### 方法 3: JavaScript 测试脚本

创建 `frontend/api-tests/sse-test.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <title>SSE 测试</title>
</head>
<body>
  <h1>SSE 连接测试</h1>
  <div id="status">未连接</div>
  <div id="events"></div>
  
  <script>
    const taskId = 'YOUR_TASK_ID';
    const token = 'YOUR_TOKEN';
    const url = `http://localhost:8000/api/analyze/stream/${taskId}?token=${token}`;
    
    const eventSource = new EventSource(url);
    
    eventSource.onopen = () => {
      document.getElementById('status').textContent = '已连接';
    };
    
    eventSource.onmessage = (event) => {
      const div = document.createElement('div');
      div.textContent = `收到事件: ${event.data}`;
      document.getElementById('events').appendChild(div);
    };
    
    eventSource.onerror = (error) => {
      document.getElementById('status').textContent = '连接错误';
      console.error('SSE 错误:', error);
    };
  </script>
</body>
</html>
```

---

## 📋 Day 5 API 交接会检查清单

### 准备工作
- [ ] 安装 Thunder Client 或 REST Client 扩展
- [ ] 创建 `frontend/api-tests/` 目录
- [ ] 准备测试请求模板

### 交接会中获取
- [ ] 后端 API 基础 URL（通常是 `http://localhost:8000`）
- [ ] 测试用户凭证（email + password）
- [ ] 测试 JWT token
- [ ] 测试任务 ID（用于测试 SSE 和报告端点）
- [ ] API 文档链接（OpenAPI/Swagger）

### 交接会后验证
- [ ] 测试所有 4 个 API 端点
- [ ] 验证 SSE 连接成功
- [ ] 验证 JWT 认证工作正常
- [ ] 记录任何差异或问题

---

## 🚨 常见问题排查

### 问题 1: CORS 错误

**错误信息**:
```
Access to fetch at 'http://localhost:8000/api/analyze' from origin 'http://localhost:3006' 
has been blocked by CORS policy
```

**解决方案**:
- 确认后端已配置 CORS 允许 `http://localhost:3006`
- 联系 Backend Agent 检查 CORS 配置

---

### 问题 2: SSE 连接失败

**错误信息**:
```
EventSource's response has a MIME type ("text/html") that is not "text/event-stream"
```

**解决方案**:
- 确认后端 SSE 端点返回正确的 Content-Type
- 检查 URL 是否正确
- 检查 Authorization header 是否正确

---

### 问题 3: 401 未授权

**错误信息**:
```
{"detail": "Could not validate credentials"}
```

**解决方案**:
- 检查 JWT token 是否过期
- 重新登录获取新 token
- 确认 Authorization header 格式: `Bearer {token}`

---

## 📚 参考资料

- [Thunder Client 文档](https://www.thunderclient.com/docs)
- [REST Client 文档](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
- [EventSource API 文档](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [curl 文档](https://curl.se/docs/)

---

**最后更新**: 2025-10-10 Day 4  
**状态**: ✅ 调试工具准备完成，等待 Day 5 API 交接会

