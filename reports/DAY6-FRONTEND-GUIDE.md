# Day 6 Frontend 开发指南

> **角色**: Frontend Agent (全栈前端)
> **日期**: 2025-10-12 (Day 6)
> **核心任务**: API联调 + ProgressPage开发
> **预计用时**: 7小时

---

## 🎯 今日目标

1. ✅ API集成测试联调通过
2. ✅ 修复React测试警告
3. ✅ ProgressPage组件开发
4. ✅ SSE客户端集成
5. ✅ TypeScript 0 errors

---

## 📋 详细任务清单

### 上午任务 (9:00-12:00)

#### ✅ 任务1: API集成测试联调 (9:00-10:00, 1小时)

**目标**: 确认Backend服务运行,运行集成测试

**执行步骤**:

```bash
# 1. 确认Backend服务运行
curl http://localhost:8000/health
# 期望: {"status": "healthy"}

# 2. 运行集成测试
cd frontend
npm test -- integration.test.ts

# 3. 预期结果: 8/8 tests passed
```

**如果测试失败,排查步骤**:

```typescript
// 问题1: NETWORK_ERROR
// 解决: 检查Backend是否启动

// 问题2: 401 Unauthorized
// 解决: 更新测试Token

// 问题3: CORS错误
// 解决: 检查Backend CORS配置

// 更新测试Token
// frontend/src/api/__tests__/integration.test.ts
const TEST_TOKEN = 'eyJ...';  // 从Backend获取新Token
```

**验收标准**:
- [ ] 8/8 集成测试通过
- [ ] 无CORS错误
- [ ] 无认证问题

---

#### ✅ 任务2: 修复React act()警告 (10:00-11:00, 1小时)

**目标**: 修复InputPage测试中的act()警告

**修复方案**:

```typescript
// frontend/src/pages/__tests__/InputPage.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { InputPage } from '../InputPage';

// 修复1: 使用waitFor等待状态更新
it('disables submit button until minimum characters are met', async () => {
  render(
    <BrowserRouter>
      <InputPage />
    </BrowserRouter>
  );

  const textarea = screen.getByRole('textbox', { name: /产品描述/i });
  const submitButton = screen.getByRole('button', { name: /开始分析/i });

  // 初始状态应该禁用
  expect(submitButton).toBeDisabled();

  // 输入少于最小长度
  fireEvent.change(textarea, { target: { value: 'short' } });

  // 等待状态更新
  await waitFor(() => {
    expect(submitButton).toBeDisabled();
  });

  // 输入足够长度
  fireEvent.change(textarea, {
    target: { value: 'AI笔记应用测试产品描述' }
  });

  // 等待状态更新
  await waitFor(() => {
    expect(submitButton).not.toBeDisabled();
  });
});

// 修复2: 使用userEvent代替fireEvent
it('allows quick fill from sample prompts', async () => {
  const user = userEvent.setup();

  render(
    <BrowserRouter>
      <InputPage />
    </BrowserRouter>
  );

  const textarea = screen.getByRole('textbox', { name: /产品描述/i });

  // 使用userEvent
  await user.click(textarea);
  await user.type(textarea, 'AI笔记应用示例描述');

  // 等待状态更新
  await waitFor(() => {
    expect(textarea).toHaveValue('AI笔记应用示例描述');
  });
});

// 修复3: Mock异步操作
it('submits product description and navigates to progress page', async () => {
  const mockNavigate = vi.fn();
  vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
      ...actual,
      useNavigate: () => mockNavigate,
    };
  });

  render(
    <BrowserRouter>
      <InputPage />
    </BrowserRouter>
  );

  const textarea = screen.getByRole('textbox', { name: /产品描述/i });
  const button = screen.getByRole('button', { name: /开始分析/i });

  // 输入描述
  fireEvent.change(textarea, {
    target: { value: 'AI笔记应用完整测试描述内容' }
  });

  // 等待按钮启用
  await waitFor(() => {
    expect(button).not.toBeDisabled();
  });

  // 点击提交
  fireEvent.click(button);

  // 等待API调用完成和导航
  await waitFor(() => {
    expect(mockNavigate).toHaveBeenCalled();
  }, { timeout: 3000 });
});
```

**验收标准**:
- [ ] 所有act()警告消失
- [ ] 测试仍然100%通过
- [ ] 使用正确的测试实践

---

#### ✅ 任务3: ProgressPage组件设计 (11:00-12:00, 1小时)

**目标**: 设计ProgressPage的状态管理和布局

**状态管理设计**:

```typescript
// frontend/src/pages/ProgressPage.tsx

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

interface ProgressState {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;  // 0-100
  currentStep: string;
  estimatedTime: number;  // 剩余秒数
  error: string | null;
}

interface SSEEvent {
  event: 'connected' | 'progress' | 'completed' | 'error';
  data: {
    percentage?: number;
    step?: string;
    message?: string;
  };
}

export const ProgressPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [state, setState] = useState<ProgressState>({
    taskId: taskId || '',
    status: 'pending',
    progress: 0,
    currentStep: '准备开始分析...',
    estimatedTime: 270,  // 5分钟 = 270秒
    error: null,
  });

  // SSE连接管理
  useEffect(() => {
    // TODO: 建立SSE连接
    // TODO: 处理事件更新
    // TODO: 错误处理和重连
  }, [taskId]);

  return (
    <div className="progress-container">
      {/* UI实现见下午任务 */}
    </div>
  );
};
```

**页面布局设计**:

```
┌─────────────────────────────────────┐
│                                     │
│        正在分析您的产品...           │
│                                     │
│   ████████████████░░░░░░  60%       │
│                                     │
│   当前步骤: 正在提取商业信号         │
│   预计剩余: 1分30秒                  │
│                                     │
│   ✓ 智能社区发现 (已完成)            │
│   ✓ 并行数据采集 (已完成)            │
│   ⟳ 统一信号提取 (进行中)            │
│   ○ 智能排序输出 (等待中)            │
│                                     │
│   [取消分析]  [切换到轮询模式]       │
│                                     │
└─────────────────────────────────────┘
```

---

### 下午任务 (14:00-18:00)

#### ✅ 任务4: ProgressPage UI实现 (14:00-16:00, 2小时)

**完整实现**:

```typescript
// frontend/src/pages/ProgressPage.tsx

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ROUTES } from '@/routes';
import { ProgressBar } from '@/components/ProgressBar';
import { StepIndicator } from '@/components/StepIndicator';
import './ProgressPage.css';

interface ProgressState {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  estimatedTime: number;
  error: string | null;
}

interface Step {
  id: string;
  name: string;
  status: 'completed' | 'processing' | 'pending';
  estimatedTime: number;
}

export const ProgressPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [state, setState] = useState<ProgressState>({
    taskId: taskId || '',
    status: 'pending',
    progress: 0,
    currentStep: '准备开始分析...',
    estimatedTime: 270,
    error: null,
  });

  const [steps, setSteps] = useState<Step[]>([
    {
      id: 'discovery',
      name: '智能社区发现',
      status: 'pending',
      estimatedTime: 30,
    },
    {
      id: 'collection',
      name: '并行数据采集',
      status: 'pending',
      estimatedTime: 120,
    },
    {
      id: 'extraction',
      name: '统一信号提取',
      status: 'pending',
      estimatedTime: 90,
    },
    {
      id: 'ranking',
      name: '智能排序输出',
      status: 'pending',
      estimatedTime: 30,
    },
  ]);

  const [usePolling, setUsePolling] = useState(false);

  // SSE连接管理 (详见任务5)
  useEffect(() => {
    if (!taskId) {
      navigate(ROUTES.HOME);
      return;
    }

    // TODO: 建立SSE连接
    // 详见任务5实现
  }, [taskId, navigate]);

  const handleCancel = async () => {
    if (confirm('确定要取消分析吗?')) {
      // TODO: 调用取消API
      navigate(ROUTES.HOME);
    }
  };

  const handleSwitchToPolling = () => {
    setUsePolling(true);
    // TODO: 停止SSE,启动轮询
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
  };

  return (
    <div className="progress-container">
      <header className="progress-header">
        <h1>正在分析您的产品...</h1>
        <p className="subtitle">
          {state.status === 'processing'
            ? '我们正在分析Reddit上的相关讨论'
            : '准备开始分析'}
        </p>
      </header>

      <div className="progress-content">
        {/* 进度条 */}
        <ProgressBar percentage={state.progress} />

        {/* 当前状态 */}
        <div className="current-status">
          <div className="status-item">
            <span className="label">当前步骤:</span>
            <span className="value">{state.currentStep}</span>
          </div>
          <div className="status-item">
            <span className="label">预计剩余:</span>
            <span className="value">{formatTime(state.estimatedTime)}</span>
          </div>
        </div>

        {/* 步骤指示器 */}
        <div className="steps-container">
          {steps.map((step) => (
            <StepIndicator
              key={step.id}
              name={step.name}
              status={step.status}
              estimatedTime={step.estimatedTime}
            />
          ))}
        </div>

        {/* 错误提示 */}
        {state.error && (
          <div className="error-banner" role="alert">
            <span className="error-icon">⚠️</span>
            <span className="error-message">{state.error}</span>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="actions">
          <button
            onClick={handleCancel}
            className="btn-cancel"
            disabled={state.status === 'completed'}
          >
            取消分析
          </button>

          {!usePolling && (
            <button
              onClick={handleSwitchToPolling}
              className="btn-secondary"
            >
              切换到轮询模式
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
```

**组件实现**:

```typescript
// frontend/src/components/ProgressBar.tsx

interface ProgressBarProps {
  percentage: number;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ percentage }) => {
  return (
    <div className="progress-bar-container">
      <div className="progress-bar-bg">
        <div
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <span className="progress-percentage">{percentage}%</span>
    </div>
  );
};

// frontend/src/components/StepIndicator.tsx

interface StepIndicatorProps {
  name: string;
  status: 'completed' | 'processing' | 'pending';
  estimatedTime: number;
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({
  name,
  status,
  estimatedTime,
}) => {
  const getIcon = () => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'processing':
        return '⟳';
      case 'pending':
        return '○';
    }
  };

  const getStatusClass = () => {
    return `step-indicator step-${status}`;
  };

  return (
    <div className={getStatusClass()}>
      <span className="step-icon">{getIcon()}</span>
      <span className="step-name">{name}</span>
      <span className="step-status">
        {status === 'completed' && '(已完成)'}
        {status === 'processing' && '(进行中)'}
        {status === 'pending' && '(等待中)'}
      </span>
    </div>
  );
};
```

**样式实现**:

```css
/* frontend/src/pages/ProgressPage.css */

.progress-container {
  max-width: 700px;
  margin: 80px auto;
  padding: 40px 20px;
}

.progress-header {
  text-align: center;
  margin-bottom: 40px;
}

.progress-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #1a1a1a;
}

.subtitle {
  font-size: 16px;
  color: #666;
}

.progress-content {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* 进度条 */
.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 16px;
}

.progress-bar-bg {
  flex: 1;
  height: 24px;
  background-color: #e1e5e9;
  border-radius: 12px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #0066cc 0%, #0052a3 100%);
  transition: width 0.5s ease;
}

.progress-percentage {
  font-size: 18px;
  font-weight: 600;
  color: #0066cc;
  min-width: 50px;
  text-align: right;
}

/* 当前状态 */
.current-status {
  display: flex;
  justify-content: space-between;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-item .label {
  font-size: 14px;
  color: #666;
}

.status-item .value {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

/* 步骤指示器 */
.steps-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.step-completed {
  background-color: #e8f5e9;
}

.step-processing {
  background-color: #fff3e0;
}

.step-pending {
  background-color: #f5f5f5;
}

.step-icon {
  font-size: 20px;
  width: 24px;
  text-align: center;
}

.step-completed .step-icon {
  color: #4caf50;
}

.step-processing .step-icon {
  color: #ff9800;
  animation: spin 1s linear infinite;
}

.step-pending .step-icon {
  color: #9e9e9e;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.step-name {
  flex: 1;
  font-size: 16px;
  font-weight: 500;
  color: #1a1a1a;
}

.step-status {
  font-size: 14px;
  color: #666;
}

/* 错误提示 */
.error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background-color: #fee;
  border: 1px solid #fcc;
  border-radius: 6px;
  color: #c33;
}

.error-icon {
  font-size: 20px;
}

/* 操作按钮 */
.actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}

.btn-cancel,
.btn-secondary {
  padding: 12px 32px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel {
  color: #dc3545;
  background-color: white;
  border: 1px solid #dc3545;
}

.btn-cancel:hover:not(:disabled) {
  background-color: #dc3545;
  color: white;
}

.btn-secondary {
  color: #666;
  background-color: white;
  border: 1px solid #ddd;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .progress-container {
    margin: 40px auto;
    padding: 20px 16px;
  }

  .progress-header h1 {
    font-size: 24px;
  }

  .current-status {
    flex-direction: column;
    gap: 16px;
  }

  .actions {
    flex-direction: column;
  }

  .btn-cancel,
  .btn-secondary {
    width: 100%;
  }
}
```

---

#### ✅ 任务5: SSE客户端集成 (16:00-18:00, 2小时)

**SSE服务实现**:

```typescript
// frontend/src/services/sse.service.ts

export type SSEEventType = 'connected' | 'progress' | 'completed' | 'error';

export interface SSEEventData {
  event: SSEEventType;
  percentage?: number;
  step?: string;
  message?: string;
  task_id?: string;
}

export type SSECallback = (event: SSEEventData) => void;

export class SSEService {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private taskId: string;

  constructor(taskId: string) {
    this.taskId = taskId;
  }

  connect(onEvent: SSECallback, onError: (error: string) => void): void {
    const url = `${import.meta.env.VITE_API_BASE_URL}/api/analyze/stream/${this.taskId}`;

    try {
      this.eventSource = new EventSource(url);

      this.eventSource.onopen = () => {
        console.log('[SSE] Connection established');
        this.reconnectAttempts = 0;
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data: SSEEventData = JSON.parse(event.data);
          console.log('[SSE] Received event:', data);
          onEvent(data);

          // 如果收到completed事件,关闭连接
          if (data.event === 'completed') {
            this.disconnect();
          }
        } catch (error) {
          console.error('[SSE] Failed to parse event data:', error);
        }
      };

      this.eventSource.onerror = (event) => {
        console.error('[SSE] Connection error:', event);

        // 尝试重连
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(
            `[SSE] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
          );

          setTimeout(() => {
            if (this.eventSource) {
              this.eventSource.close();
            }
            this.connect(onEvent, onError);
          }, this.reconnectDelay);
        } else {
          onError('SSE连接失败,已切换到轮询模式');
          this.disconnect();
        }
      };
    } catch (error) {
      console.error('[SSE] Failed to create EventSource:', error);
      onError('无法建立实时连接');
    }
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      console.log('[SSE] Connection closed');
    }
  }

  isConnected(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }
}
```

**ProgressPage中使用SSE**:

```typescript
// frontend/src/pages/ProgressPage.tsx (更新)

import { SSEService, SSEEventData } from '@/services/sse.service';

export const ProgressPage: React.FC = () => {
  // ... 其他state

  const [sseService, setSSEService] = useState<SSEService | null>(null);

  useEffect(() => {
    if (!taskId) {
      navigate(ROUTES.HOME);
      return;
    }

    // 建立SSE连接
    const service = new SSEService(taskId);

    const handleSSEEvent = (event: SSEEventData) => {
      switch (event.event) {
        case 'connected':
          console.log('[ProgressPage] SSE connected');
          setState((prev) => ({
            ...prev,
            status: 'processing',
          }));
          break;

        case 'progress':
          console.log('[ProgressPage] Progress update:', event.percentage);
          setState((prev) => ({
            ...prev,
            status: 'processing',
            progress: event.percentage || prev.progress,
            currentStep: event.step || prev.currentStep,
          }));

          // 更新步骤状态
          if (event.step) {
            updateStepStatus(event.step, event.percentage || 0);
          }
          break;

        case 'completed':
          console.log('[ProgressPage] Analysis completed');
          setState((prev) => ({
            ...prev,
            status: 'completed',
            progress: 100,
            currentStep: '分析完成',
          }));

          // 跳转到报告页
          setTimeout(() => {
            navigate(ROUTES.REPORT(taskId));
          }, 1500);
          break;

        case 'error':
          console.error('[ProgressPage] Analysis error:', event.message);
          setState((prev) => ({
            ...prev,
            status: 'failed',
            error: event.message || '分析失败,请重试',
          }));
          break;
      }
    };

    const handleSSEError = (error: string) => {
      console.error('[ProgressPage] SSE error:', error);
      setState((prev) => ({
        ...prev,
        error: error,
      }));
      setUsePolling(true);  // 切换到轮询模式
    };

    service.connect(handleSSEEvent, handleSSEError);
    setSSEService(service);

    // 清理函数
    return () => {
      service.disconnect();
    };
  }, [taskId, navigate]);

  const updateStepStatus = (stepName: string, percentage: number) => {
    setSteps((prev) =>
      prev.map((step) => {
        // 根据进度更新步骤状态
        if (percentage < 30) {
          return {
            ...step,
            status:
              step.id === 'discovery'
                ? 'processing'
                : 'pending',
          };
        } else if (percentage < 60) {
          return {
            ...step,
            status:
              step.id === 'discovery'
                ? 'completed'
                : step.id === 'collection'
                ? 'processing'
                : 'pending',
          };
        } else if (percentage < 90) {
          return {
            ...step,
            status:
              step.id === 'discovery' || step.id === 'collection'
                ? 'completed'
                : step.id === 'extraction'
                ? 'processing'
                : 'pending',
          };
        } else {
          return {
            ...step,
            status:
              step.id === 'ranking'
                ? 'processing'
                : 'completed',
          };
        }
      })
    );
  };

  // ... 其他代码
};
```

---

## 📊 今日验收清单

### 功能验收
- [ ] ✅ API集成测试8/8通过
- [ ] ✅ React act()警告修复
- [ ] ✅ ProgressPage组件完整实现
- [ ] ✅ SSE客户端正常工作
- [ ] ✅ 自动重连机制生效

### 测试验收
- [ ] ✅ 所有单元测试通过
- [ ] ✅ TypeScript编译0错误
- [ ] ✅ ESLint无警告
- [ ] ✅ 测试覆盖率>70%

### UI验收
- [ ] ✅ 进度条流畅显示
- [ ] ✅ 步骤状态正确更新
- [ ] ✅ 错误处理友好
- [ ] ✅ 响应式设计完整

---

**Day 6 Frontend 加油! 🚀**

ProgressPage是用户体验的关键,实时进度让等待不再焦虑!
