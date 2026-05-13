/**
 * ProgressPage 测试
 *
 * 目标覆盖 PRD-05 等待页关键交互：任务 ID 解析、SSE 进度渲染、完成态跳转。
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProgressPage from '../ProgressPage';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom'
  );
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const hoisted = vi.hoisted(() => ({
  createTaskProgressSSE: vi.fn(),
  getTaskStatus: vi.fn(),
}));

vi.mock('@/api/sse.client', () => hoisted);

const mockCreateTaskProgressSSE = hoisted.createTaskProgressSSE;

// SSE 工厂 mock
const connectMock = vi.fn();
const disconnectMock = vi.fn();
const handlers: {
  onEvent: (event: any) => void;
  onStatus: (status: string) => void;
} = {
  onEvent: () => {},
  onStatus: () => {},
};

// 轮询 API mock
vi.mock('@/api/analyze.api', () => ({
  getTaskStatus: (...args: unknown[]) => hoisted.getTaskStatus(...args),
}));

const mockGetTaskStatus = hoisted.getTaskStatus;

describe('ProgressPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    connectMock.mockReset();
    disconnectMock.mockReset();
    handlers.onEvent = () => {};
    handlers.onStatus = () => {};
    mockGetTaskStatus.mockResolvedValue({
      task_id: 'test-task-123',
      status: 'processing',
      progress: 25,
      percentage: 25,
      message: '数据收集中...',
      current_step: '数据收集中...',
      stage: null,
      blocked_reason: null,
      next_action: null,
      details: null,
      error: null,
      sse_endpoint: '/api/analyze/stream/test-task-123',
      retry_count: 0,
      failure_category: null,
      last_retry_at: null,
      dead_letter_at: null,
      updated_at: new Date().toISOString(),
    });
    mockCreateTaskProgressSSE.mockImplementation(
      (
        _taskId: string,
        onEvent: (event: any) => void,
        onStatus?: (status: string) => void,
        _sseEndpoint?: string
      ) => {
        handlers.onEvent = onEvent;
        handlers.onStatus = onStatus ?? (() => {});
        return {
          connect: connectMock.mockImplementation(() => {
            handlers.onStatus('connected');
          }),
          disconnect: disconnectMock,
        };
      }
    );
  });

  it('渲染基础信息并发起 SSE 连接', async () => {
    render(
      <MemoryRouter initialEntries={['/progress/test-task-123']}>
        <Routes>
          <Route path="/progress/:taskId" element={<ProgressPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('正在分析您的产品')).toBeInTheDocument();
    expect(screen.getByText('系统正在抓取并分析真实讨论。')).toBeInTheDocument();
    expect(screen.getByText('中途返回不丢描述，系统会自动带回输入页。')).toBeInTheDocument();
    expect(screen.queryByText('发现的社区')).not.toBeInTheDocument();
    expect(screen.queryByText('已分析帖子')).not.toBeInTheDocument();
    expect(screen.queryByText('生成的洞察')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(mockCreateTaskProgressSSE).toHaveBeenCalled();
    });

    const callArgs = mockCreateTaskProgressSSE.mock.calls[0];
    expect(callArgs[0]).toBe('test-task-123');
    expect(typeof callArgs[1]).toBe('function');
    expect(typeof callArgs[2]).toBe('function');
    expect(callArgs[3]).toBe('/api/analyze/stream/test-task-123');

    await waitFor(() => {
      expect(connectMock).toHaveBeenCalled();
    });
  });

  it('收到进度事件时更新进度条与当前步骤', async () => {
    render(
      <MemoryRouter initialEntries={['/progress/test-task-123']}>
        <Routes>
          <Route path="/progress/:taskId" element={<ProgressPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(mockCreateTaskProgressSSE).toHaveBeenCalled());

    await act(async () => {
      handlers.onEvent({
        event: 'progress',
        progress: 75,
        task_id: 'test-task-123',
        status: 'processing',
        message: '分析中...',
        current_step: '智能分析与洞察生成',
      });
    });

    await waitFor(() => {
      expect(screen.getByText('75%')).toBeInTheDocument();
      expect(screen.getAllByText('智能分析与洞察生成').length).toBeGreaterThan(0);
    });
  });

  it('收到 completed 事件后跳转到报告页', async () => {
    render(
      <MemoryRouter initialEntries={['/progress/test-task-123']}>
        <Routes>
          <Route path="/progress/:taskId" element={<ProgressPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(mockCreateTaskProgressSSE).toHaveBeenCalled());

    await act(async () => {
      handlers.onEvent({
        event: 'completed',
        progress: 100,
        task_id: 'test-task-123',
        status: 'completed',
        message: '分析完成',
      });
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 2200));
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/report/test-task-123');
    });
  });

  it('warmup completed 时不自动跳转（要把原因和下一步说清楚）', async () => {
    render(
      <MemoryRouter initialEntries={['/progress/test-task-123']}>
        <Routes>
          <Route path="/progress/:taskId" element={<ProgressPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(mockCreateTaskProgressSSE).toHaveBeenCalled());

    await act(async () => {
      handlers.onEvent({
        event: 'completed',
        progress: 100,
        task_id: 'test-task-123',
        status: 'completed',
        message: '补量已下单：系统会在 2 分钟后自动再跑一次',
        stage: 'warmup',
        blocked_reason: 'insufficient_samples',
        next_action: 'auto_rerun_scheduled',
        details: {
          next_retry_at: '2025-12-29T00:00:00Z',
        },
      });
    });

    await waitFor(() => {
      expect(screen.getByText('阶段')).toBeInTheDocument();
      expect(screen.getAllByText('卡点原因').length).toBeGreaterThan(0);
      expect(screen.getAllByText('下一步').length).toBeGreaterThan(0);
      expect(screen.getByText('预计重试')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '先看当前结果' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '回输入页重跑' })).toBeInTheDocument();
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 2200));
    });

    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalledWith('/report/test-task-123');
    });
  });

  it('初始轮询快照也应该展示真实卡点信息', async () => {
    mockGetTaskStatus.mockResolvedValueOnce({
      task_id: 'test-task-123',
      status: 'completed',
      progress: 100,
      percentage: 100,
      message: '补量已下单：系统会在 2 分钟后自动再跑一次',
      current_step: '补量中...',
      stage: 'warmup',
      blocked_reason: 'insufficient_samples',
      next_action: 'auto_rerun_scheduled',
      details: {
        next_retry_at: '2025-12-29T00:00:00Z',
      },
      error: null,
      sse_endpoint: '/api/analyze/stream/test-task-123',
      retry_count: 0,
      failure_category: null,
      last_retry_at: null,
      dead_letter_at: null,
      updated_at: new Date().toISOString(),
    });

    render(
      <MemoryRouter initialEntries={['/progress/test-task-123']}>
        <Routes>
          <Route path="/progress/:taskId" element={<ProgressPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { name: '这次结果还在整理中', level: 2 })).toBeInTheDocument();
    expect(screen.getAllByText('卡点原因').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: '先看当前结果' })).toBeInTheDocument();

    expect(screen.queryByText('发现的社区')).not.toBeInTheDocument();
    expect(screen.queryByText('已分析帖子')).not.toBeInTheDocument();
    expect(screen.queryByText('生成的洞察')).not.toBeInTheDocument();
  });

  it('取消分析后应该回输入页并保留当前描述', async () => {
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: '/progress/test-task-123',
            state: {
              productDescription: '跨境卖家多平台利润追踪工具，解决手续费和回款分散的问题。',
              sseEndpoint: '/api/analyze/stream/test-task-123',
            },
          },
        ]}
      >
        <Routes>
          <Route path="/progress/:taskId" element={<ProgressPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(mockCreateTaskProgressSSE).toHaveBeenCalled());
    await userEvent.click(screen.getByRole('button', { name: '取消分析' }));
    await userEvent.click(screen.getByRole('button', { name: '回输入页' }));

    expect(mockNavigate).toHaveBeenCalledWith('/', {
      state: {
        prefillProductDescription: '跨境卖家多平台利润追踪工具，解决手续费和回款分散的问题。',
        prefillSource: 'restart-analysis',
        prefillHint: '已带回这次分析方向。你可以继续补描述，或者先缩小范围再重跑。',
      },
    });
  });

  it('失败态应该支持回输入页重跑并保留当前描述', async () => {
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: '/progress/test-task-123',
            state: {
              productDescription: '一个帮助自由职业者管理时间和发票的 SaaS 工具。',
              sseEndpoint: '/api/analyze/stream/test-task-123',
            },
          },
        ]}
      >
        <Routes>
          <Route path="/progress/:taskId" element={<ProgressPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(mockCreateTaskProgressSSE).toHaveBeenCalled());

    await act(async () => {
      handlers.onEvent({
        event: 'error',
        task_id: 'test-task-123',
        status: 'failed',
        error_message: '网络异常',
      });
    });

    const retryButton = await screen.findByRole('button', { name: '回输入页重跑' });
    await userEvent.click(retryButton);

    expect(mockNavigate).toHaveBeenCalledWith('/', {
      state: {
        prefillProductDescription: '一个帮助自由职业者管理时间和发票的 SaaS 工具。',
        prefillSource: 'restart-analysis',
        prefillHint: '已带回这次分析方向。你可以直接改描述后重跑，不用从零开始。',
      },
    });
  });
});
