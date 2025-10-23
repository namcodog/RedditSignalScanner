import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '@/api/client';

vi.mock('@/api/client', async (orig) => {
  const actual = await (orig as any)();
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      get: vi.fn(),
    },
  };
});

describe('client.checkApiHealth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call GET /healthz and return true on 200', async () => {
    vi.spyOn(client.apiClient, 'get').mockResolvedValue({ status: 200 } as any);
    const ok = await client.checkApiHealth();
    expect(client.apiClient.get).toHaveBeenCalledWith('/healthz');
    expect(ok).toBe(true);
  });

  it('should return false on error', async () => {
    vi.spyOn(client.apiClient, 'get').mockRejectedValue(new Error('network'));
    const ok = await client.checkApiHealth();
    expect(ok).toBe(false);
  });
});

