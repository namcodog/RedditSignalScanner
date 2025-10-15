# API 客户端设计文档

> **创建日期**: 2025-10-10 Day 2
> **基于**: PRD-02 API 设计规范
> **状态**: ✅ 技术方案已完成

---

## 📋 概述

本文档描述 Reddit Signal Scanner 前端的 API 客户端设计，包括 HTTP 客户端（Axios）和 SSE 客户端的完整实现方案。

---

## 🎯 设计目标

1. **类型安全**: 所有 API 调用都有完整的 TypeScript 类型定义
2. **统一错误处理**: 集中处理 API 错误，提供一致的错误信息
3. **自动认证**: 自动添加 JWT token 到请求头
4. **SSE 优先**: 优先使用 SSE 实时推送，自动降级到轮询
5. **易于使用**: 提供简洁的 API 和 Hooks

---

## 🏗️ 架构设计

### 1. HTTP 客户端（Axios）

#### 核心功能
- ✅ 基于 Axios 封装
- ✅ 自动添加认证 token
- ✅ 统一错误处理
- ✅ 请求/响应拦截器
- ✅ 请求 ID 追踪

#### 文件结构
```
src/api/
├── client.ts           # Axios 客户端配置
├── analyze.api.ts      # 分析任务 API
├── auth.api.ts         # 认证 API
└── index.ts            # 统一导出
```

#### 使用示例
```typescript
import { createAnalyzeTask } from '@/api';

// 创建分析任务
const response = await createAnalyzeTask({
  productDescription: 'AI笔记应用，帮助研究者自动组织和连接想法',
});

console.log(response.taskId);
```

---

### 2. SSE 客户端

#### 核心功能
- ✅ 基于 EventSource API
- ✅ 自动重连机制（最多 5 次）
- ✅ 心跳检测（30 秒超时）
- ✅ 自动降级到轮询
- ✅ 连接状态管理

#### 文件结构
```
src/api/
├── sse.client.ts       # SSE 客户端实现
└── index.ts            # 统一导出
```

#### 使用示例
```typescript
import { createTaskProgressSSE } from '@/api';

// 创建 SSE 客户端
const sseClient = createTaskProgressSSE(
  taskId,
  (event) => {
    console.log('收到事件:', event);
  },
  (status) => {
    console.log('连接状态:', status);
  }
);

// 连接
sseClient.connect();

// 断开
sseClient.disconnect();
```

---

### 3. 自定义 Hooks

#### useSSE Hook

**功能**:
- 管理 SSE 连接生命周期
- 自动重连
- 自动降级到轮询
- React 组件集成

**使用示例**:
```typescript
import { useSSE } from '@/hooks/useSSE';

const ProgressPage = () => {
  const { status, latestEvent, isPolling } = useSSE({
    taskId: '123e4567-e89b-12d3-a456-426614174000',
    autoConnect: true,
    enableFallback: true,
    onEvent: (event) => {
      console.log('收到事件:', event);
    },
  });
  
  return (
    <div>
      <p>连接状态: {status}</p>
      <p>是否轮询: {isPolling ? '是' : '否'}</p>
      {latestEvent && (
        <p>进度: {latestEvent.percentage}%</p>
      )}
    </div>
  );
};
```

---

## 📡 API 端点映射

### 1. 分析任务 API

| 方法 | 端点 | 函数 | 说明 |
|------|------|------|------|
| POST | /api/analyze | `createAnalyzeTask()` | 创建分析任务 |
| GET | /api/analyze/stream/{taskId} | `createTaskProgressSSE()` | SSE 实时进度 |
| GET | /api/status/{taskId} | `getTaskStatus()` | 查询任务状态（轮询） |
| GET | /api/report/{taskId} | `getAnalysisReport()` | 获取分析报告 |

### 2. 认证 API

| 方法 | 端点 | 函数 | 说明 |
|------|------|------|------|
| POST | /api/auth/register | `register()` | 用户注册 |
| POST | /api/auth/login | `login()` | 用户登录 |
| GET | /api/auth/me | `getCurrentUser()` | 获取当前用户 |

---

## 🔄 SSE 降级策略

### 降级流程

```
1. 尝试建立 SSE 连接
   ↓
2. SSE 连接失败或超时
   ↓
3. 自动切换到轮询模式
   ↓
4. 每 2 秒轮询一次任务状态
   ↓
5. 任务完成或失败时停止轮询
```

### 降级触发条件

- SSE 连接失败（网络错误）
- SSE 连接超时（30 秒无心跳）
- 重连次数超过上限（5 次）
- 浏览器不支持 EventSource

### 降级后的行为

- 自动切换到 `GET /api/status/{taskId}` 轮询
- 轮询间隔: 2 秒
- 模拟 SSE 事件格式，保持前端代码一致
- 在 UI 上提示用户已切换到轮询模式

---

## 🛡️ 错误处理

### HTTP 错误处理

```typescript
// 401 未授权
if (status === 401) {
  clearAuthToken();
  // 跳转到登录页面
}

// 429 限流
if (status === 429) {
  console.warn('API 请求频率过高，请稍后重试');
}

// 500 服务器错误
if (status >= 500) {
  console.error('服务器错误，请稍后重试');
}
```

### SSE 错误处理

```typescript
// SSE 连接错误
eventSource.onerror = (event) => {
  console.error('SSE 连接错误:', event);
  
  // 自动重连
  if (reconnectAttempts < maxReconnectAttempts) {
    reconnect();
  } else {
    // 降级到轮询
    switchToPolling();
  }
};
```

---

## 📊 性能优化

### 1. 请求优化

- ✅ 使用 Axios 拦截器统一处理
- ✅ 请求去重（防止重复提交）
- ✅ 请求超时控制（30 秒）
- ✅ 请求 ID 追踪

### 2. SSE 优化

- ✅ 心跳检测（30 秒）
- ✅ 自动重连（指数退避）
- ✅ 连接池管理（每用户最多 2 个连接）
- ✅ 事件缓冲区（1024 字节）

### 3. 轮询优化

- ✅ 轮询间隔: 2 秒（避免过度请求）
- ✅ 最大轮询次数: 150 次（5 分钟）
- ✅ 任务完成后立即停止轮询

---

## 🧪 测试策略

### 1. 单元测试

- [ ] Axios 拦截器测试
- [ ] SSE 客户端连接测试
- [ ] SSE 重连机制测试
- [ ] 错误处理测试

### 2. 集成测试

- [ ] API 调用端到端测试
- [ ] SSE 实时推送测试
- [ ] 降级到轮询测试
- [ ] 认证流程测试

### 3. 性能测试

- [ ] 并发 SSE 连接测试
- [ ] 轮询性能测试
- [ ] 内存泄漏测试

---

## 📝 使用指南

### 1. 创建分析任务

```typescript
import { createAnalyzeTask } from '@/api';

const handleSubmit = async (description: string) => {
  try {
    const response = await createAnalyzeTask({
      productDescription: description,
    });
    
    // 跳转到进度页面
    navigate(`/progress/${response.taskId}`);
  } catch (error) {
    console.error('创建任务失败:', error);
  }
};
```

### 2. 监听任务进度（SSE）

```typescript
import { useSSE } from '@/hooks/useSSE';

const ProgressPage = () => {
  const { taskId } = useParams();
  
  const { status, latestEvent, isPolling } = useSSE({
    taskId: taskId!,
    autoConnect: true,
    enableFallback: true,
    onEvent: (event) => {
      if (event.event === 'completed') {
        // 跳转到报告页面
        navigate(`/report/${taskId}`);
      }
    },
  });
  
  return (
    <div>
      {isPolling && <p>⚠️ 已切换到轮询模式</p>}
      <p>进度: {latestEvent?.percentage ?? 0}%</p>
    </div>
  );
};
```

### 3. 获取分析报告

```typescript
import { getAnalysisReport } from '@/api';

const ReportPage = () => {
  const { taskId } = useParams();
  const [report, setReport] = useState<ReportResponse | null>(null);
  
  useEffect(() => {
    const fetchReport = async () => {
      try {
        const data = await getAnalysisReport(taskId!);
        setReport(data);
      } catch (error) {
        console.error('获取报告失败:', error);
      }
    };
    
    void fetchReport();
  }, [taskId]);
  
  return (
    <div>
      {report && (
        <div>
          <h1>分析报告</h1>
          <p>痛点数量: {report.report.painPoints.length}</p>
          <p>竞品数量: {report.report.competitors.length}</p>
          <p>机会数量: {report.report.opportunities.length}</p>
        </div>
      )}
    </div>
  );
};
```

---

## 🔐 安全考虑

### 1. 认证 Token 管理

- ✅ Token 存储在 localStorage
- ✅ 自动添加到请求头
- ✅ 401 错误时自动清除 token
- ⚠️ 未来考虑使用 httpOnly cookie

### 2. CORS 配置

- ✅ 允许的源: `http://localhost:3006`
- ✅ 允许的方法: `GET`, `POST`
- ✅ 允许的头: `Content-Type`, `Authorization`

### 3. XSS 防护

- ✅ 所有用户输入都经过验证
- ✅ 使用 React 的自动转义
- ✅ 禁止 `dangerouslySetInnerHTML`

---

## 📚 参考文档

- [PRD-02 API 设计规范](../../docs/PRD/PRD-02-API设计.md)
- [Schema 契约文档](../../reports/phase-log/schema-contract.md)
- [Axios 官方文档](https://axios-http.com/)
- [EventSource API 文档](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

---

**最后更新**: 2025-10-10 Day 2  
**状态**: ✅ 技术方案已完成，等待 Day 5 实现

