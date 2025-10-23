import { describe, it, expect, vi, beforeEach } from 'vitest';

// Prepare axios mock before importing the client module
const mockGet = vi.fn();
vi.mock('axios', () => {
  return {
    default: {
      create: () => ({
        get: mockGet,
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      }),
    },
  } as any;
});

describe('client.checkApiHealth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should call GET /healthz and return true on 200', async () => {
    const client = await import('@/api/client');
    mockGet.mockResolvedValueOnce({ status: 200 } as any);
    const ok = await client.checkApiHealth();
    expect(mockGet).toHaveBeenCalledWith('/healthz');
    expect(ok).toBe(true);
  });

  it('should return false on error', async () => {
    const client = await import('@/api/client');
    mockGet.mockRejectedValueOnce(new Error('network'));
    const ok = await client.checkApiHealth();
    expect(ok).toBe(false);
  });
});
