/**
 * sse.client 测试
 *
 * 验证 PRD-02 定义的 SSE 客户端连接流程与事件处理。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createTaskProgressSSE } from '../sse.client';

const { fetchEventSourceMock } = vi.hoisted(() => ({
  fetchEventSourceMock: vi.fn(),
}));

vi.mock('@microsoft/fetch-event-source', () => ({
  fetchEventSource: fetchEventSourceMock,
}));

describe('SSEClient', () => {
  beforeEach(() => {
    fetchEventSourceMock.mockReset();
    localStorage.clear();
  });

  it('创建任务 SSE 客户端时拼接正确 URL', async () => {
    const client = createTaskProgressSSE('task-123', vi.fn(), vi.fn());
    expect(typeof (client as any).connect).toBe('function');

    expect(fetchEventSourceMock).toHaveBeenCalledTimes(0);
    // 触发一次连接以验证 URL
    fetchEventSourceMock.mockResolvedValueOnce(undefined);
    await client.connect();

    const expectedBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
    expect(fetchEventSourceMock).toHaveBeenCalledWith(
      `${expectedBaseUrl}/api/analyze/stream/task-123`,
      expect.any(Object)
    );
  });

  it('连接时附带 Bearer token 并转发事件', async () => {
    const onEvent = vi.fn();
    const onStatus = vi.fn();
    const client = createTaskProgressSSE('task-123', onEvent, onStatus);

    localStorage.setItem('auth_token', 'token-xyz');

    fetchEventSourceMock.mockImplementationOnce(async (_url, options) => {
      await options?.onopen?.({ ok: true } as Response);
      options?.onmessage?.({
        event: 'progress',
        data: JSON.stringify({
          task_id: 'task-123',
          status: 'processing',
          progress: 50,
          message: '分析中',
        }),
      } as any);
      return undefined;
    });

    await client.connect();

    expect(onStatus).toHaveBeenCalledWith('connected');
    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'progress',
        progress: 50,
        message: '分析中',
      })
    );

    const lastCall = fetchEventSourceMock.mock.calls[
      fetchEventSourceMock.mock.calls.length - 1
    ]!;
    const [, options] = lastCall;
    expect(options?.headers).toEqual({
      Authorization: 'Bearer token-xyz',
    });
  });
});
