import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '@/api/client';

vi.mock('@/api/client');

describe('analyze.api (P1 改进)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  it('createAnalyzeTask 应携带超时配置并返回数据', async () => {
    const { createAnalyzeTask } = await import('@/api/analyze.api');

    const payload = { product_description: 'A'.repeat(20) } as any;
    vi.mocked(client.apiClient.post).mockResolvedValue({ data: { task_id: 't1' } } as any);

    const result = await createAnalyzeTask(payload);

    expect(client.apiClient.post).toHaveBeenCalledWith(
      '/analyze',
      payload,
      expect.objectContaining({ timeout: expect.any(Number) })
    );
    expect(result).toEqual({ task_id: 't1' });
  });

  it('createAnalyzeTask 超时应抛出友好错误', async () => {
    const { createAnalyzeTask } = await import('@/api/analyze.api');

    const payload = { product_description: 'B'.repeat(20) } as any;
    const timeoutError: any = new Error('timeout of 20000ms exceeded');
    timeoutError.code = 'ECONNABORTED';

    vi.mocked(client.apiClient.post).mockRejectedValue(timeoutError);

    await expect(createAnalyzeTask(payload)).rejects.toThrow('请求超时，请稍后重试');
  });

  it('getAnalysisReport 应使用缓存（同一 taskId 第二次不再请求）', async () => {
    const { getAnalysisReport } = await import('@/api/analyze.api');

    const report = { task_id: 't2', report: { executive_summary: {} } } as any;
    vi.mocked(client.apiClient.get).mockResolvedValue({ data: report } as any);

    const r1 = await getAnalysisReport('t2');
    const r2 = await getAnalysisReport('t2');

    expect(r1).toEqual(report);
    expect(r2).toEqual(report);
    expect(client.apiClient.get).toHaveBeenCalledTimes(1);
  });
});

