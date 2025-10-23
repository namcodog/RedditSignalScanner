/**
 * useSSE Hook 测试
 *
 * 覆盖 PRD-02 中 SSE 连接/降级逻辑。
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useSSE } from '../useSSE';

const hoisted = vi.hoisted(() => ({
  createTaskProgressSSE: vi.fn(),
  getTaskStatus: vi
    .fn()
    .mockResolvedValue({
      task_id: 'task-1',
      status: 'processing',
      progress: 10,
      percentage: 10,
      message: '准备中',
      current_step: '准备中',
      error: null,
      sse_endpoint: '/api/analyze/stream/task-1',
      retry_count: 0,
      failure_category: null,
      last_retry_at: null,
      dead_letter_at: null,
      updated_at: new Date().toISOString(),
    }),
}));

vi.mock('@/api', () => hoisted);

const mockCreateTaskProgressSSE = hoisted.createTaskProgressSSE;
const getTaskStatusMock = hoisted.getTaskStatus;

const connectMock = vi.fn();
const disconnectMock = vi.fn();
const handlers: {
  onEvent: (event: any) => void;
  onStatus: (status: any) => void;
} = {
  onEvent: () => {},
  onStatus: () => {},
};

describe('useSSE', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    connectMock.mockReset();
    disconnectMock.mockReset();
    handlers.onEvent = () => {};
    handlers.onStatus = () => {};
    getTaskStatusMock.mockReset();
    getTaskStatusMock.mockResolvedValue({
      task_id: 'task-1',
      status: 'processing',
      progress: 10,
      percentage: 10,
      message: '准备中',
      current_step: '准备中',
      error: null,
      sse_endpoint: '/api/analyze/stream/task-1',
      retry_count: 0,
      failure_category: null,
      last_retry_at: null,
      dead_letter_at: null,
      updated_at: new Date().toISOString(),
    });
    mockCreateTaskProgressSSE.mockImplementation(
      (_taskId: string, onEvent: (event: any) => void, onStatus?: (status: any) => void, _endpoint?: string) => {
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
    getTaskStatusMock.mockClear();
  });

  afterEach(() => {
    /* no-op */
  });

  it('自动连接并更新状态', async () => {
    const { result } = renderHook(() =>
      useSSE({
        taskId: 'task-1',
        autoConnect: true,
      })
    );

    await act(async () => {
      handlers.onStatus('connected');
    });

    expect(connectMock).toHaveBeenCalled();
    expect(result.current.status).toBe('connected');

    await act(async () => {
      handlers.onEvent({
        event: 'progress',
        task_id: 'task-1',
        progress: 40,
        status: 'processing',
        message: '处理中',
      });
    });

    expect(result.current.latestEvent).toMatchObject({
      event: 'progress',
      progress: 40,
    });
  });

  it('手动切换到轮询模式时会触发任务查询', async () => {
    const { result } = renderHook(() =>
      useSSE({
        taskId: 'task-1',
        autoConnect: false,
        enableFallback: true,
        pollingInterval: 500,
      })
    );

    await act(async () => {
      result.current.switchToPolling();
    });

    await waitFor(() => {
      expect(getTaskStatusMock).toHaveBeenCalledWith('task-1');
    });

    expect(getTaskStatusMock).toHaveBeenCalledWith('task-1');
  });
});
