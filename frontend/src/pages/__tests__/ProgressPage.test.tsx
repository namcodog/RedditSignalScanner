/**
 * ProgressPage 测试
 *
 * 目标覆盖 PRD-05 等待页关键交互：任务 ID 解析、SSE 进度渲染、完成态跳转。
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { render, screen, waitFor, act } from '@testing-library/react';
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
  getTaskStatus: vi.fn().mockResolvedValue({
    task_id: 'test-task-123',
    status: 'processing',
    progress: {
      percentage: 25,
      current_step: '数据收集中...',
      completed_steps: [],
      total_steps: 4,
    },
    created_at: new Date().toISOString(),
    estimated_completion: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
  }),
}));

describe('ProgressPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    connectMock.mockReset();
    disconnectMock.mockReset();
    handlers.onEvent = () => {};
    handlers.onStatus = () => {};
    mockCreateTaskProgressSSE.mockImplementation(
      (_taskId: string, onEvent: (event: any) => void, onStatus?: (status: string) => void) => {
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
    expect(screen.getByText('数据收集与处理')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockCreateTaskProgressSSE).toHaveBeenCalled();
    });

    const callArgs = mockCreateTaskProgressSSE.mock.calls[0];
    expect(callArgs[0]).toBe('test-task-123');
    expect(typeof callArgs[1]).toBe('function');
    expect(typeof callArgs[2]).toBe('function');

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
      expect(screen.getByText('智能分析与洞察生成')).toBeInTheDocument();
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
});
