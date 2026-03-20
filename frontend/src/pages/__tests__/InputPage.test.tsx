import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import InputPage from '../InputPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');

  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockCreateAnalyzeTask = vi.fn();
const mockRegister = vi.fn();
const mockIsAuthenticated = vi.fn();
const mockGetInputGuidance = vi.fn();

vi.mock('@/api/analyze.api', () => ({
  createAnalyzeTask: (...args: unknown[]) => mockCreateAnalyzeTask(...args),
}));

vi.mock('@/api/auth.api', () => ({
  register: (...args: unknown[]) => mockRegister(...args),
  isAuthenticated: () => mockIsAuthenticated(),
}));

vi.mock('@/api/guidance.api', () => ({
  getInputGuidance: (...args: unknown[]) => mockGetInputGuidance(...args),
}));

const renderInputPage = async (initialEntries: any[] = ['/']) => {
  let result;
  await act(async () => {
    result = render(
      <MemoryRouter initialEntries={initialEntries}>
        <InputPage />
      </MemoryRouter>
    );
  });
  return result!;
};

describe('InputPage', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockCreateAnalyzeTask.mockReset();
    mockRegister.mockReset();
    mockIsAuthenticated.mockReset();
    mockGetInputGuidance.mockReset();
    mockGetInputGuidance.mockRejectedValue(new Error('skip guidance'));

    // 默认情况下，假设用户已认证，避免触发自动认证流程
    mockIsAuthenticated.mockReturnValue(true);
  });

  it('disables submit button until minimum characters are met', async () => {
    await renderInputPage();
    expect(screen.getByText('可能直接出完整结论')).toBeInTheDocument();
    expect(screen.getByText('中途返回不丢方向')).toBeInTheDocument();
    const submitButton = screen.getByRole('button', { name: '开始 5 分钟分析' });
    expect(submitButton).toBeDisabled();

    const textarea = screen.getByRole('textbox', { name: /产品描述/i });

    await act(async () => {
      await userEvent.type(textarea, 'short');
    });

    // 等待状态更新
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });

    await act(async () => {
      await userEvent.type(textarea, ' 描述满足最小字数要求');
    });

    // 等待状态更新
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
    });
  });

  it('allows quick fill from sample prompts', async () => {
    await renderInputPage();
    const sampleCardTitle = screen.getByText('跨境支付/收款');

    await act(async () => {
      await userEvent.click(sampleCardTitle);
    });

    const textarea = screen.getByRole('textbox', { name: /产品描述/i }) as HTMLTextAreaElement;

    // 等待状态更新 - 更新为新的示例提示词
    await waitFor(() => {
      expect(textarea.value).toMatch(/跨境电商卖家收款与结算效率分析/);
    });
  });

  it('submits product description and navigates to progress page', async () => {
    mockCreateAnalyzeTask.mockResolvedValue({
      task_id: '123e4567-e89b-12d3-a456-426614174000',
      status: 'pending',
      created_at: '2025-10-11T10:00:00Z',
      estimated_completion: '2025-10-11T10:05:00Z',
      sse_endpoint: '/api/analyze/stream/123',
    });

    await renderInputPage();

    const textarea = screen.getByRole('textbox', { name: /产品描述/i });

    await act(async () => {
      await userEvent.type(
        textarea,
        '一个帮助设计团队快速聚合用户反馈并生成会议纪要的助手。'
      );
    });

    const submitButton = screen.getByRole('button', { name: '开始 5 分钟分析' });

    await act(async () => {
      await userEvent.click(submitButton);
    });

    // 等待异步操作完成
    await waitFor(() => {
      expect(mockCreateAnalyzeTask).toHaveBeenCalledWith({
        product_description: '一个帮助设计团队快速聚合用户反馈并生成会议纪要的助手。',
      });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalled();
    }, { timeout: 3000 });

    // 验证导航参数
    expect(mockNavigate).toHaveBeenCalledWith('/progress/123e4567-e89b-12d3-a456-426614174000', {
      state: {
        createdAt: '2025-10-11T10:00:00Z',
        estimatedCompletion: '2025-10-11T10:05:00Z',
        sseEndpoint: '/api/analyze/stream/123',
        productDescription: '一个帮助设计团队快速聚合用户反馈并生成会议纪要的助手。',
      },
    });
  });

  it('fills official guidance samples but still submits a real analysis request', async () => {
    mockGetInputGuidance.mockResolvedValueOnce({
      examples: [
        {
          title: '官方示例',
          prompt: '一个帮助跨境卖家统一看清多平台回款、手续费和退款损耗的利润看板。',
          tags: ['跨境', '利润'],
          example_id: 'example-123',
        },
      ],
    });
    mockCreateAnalyzeTask.mockResolvedValue({
      task_id: '123e4567-e89b-12d3-a456-426614174001',
      status: 'pending',
      created_at: '2025-10-11T10:00:00Z',
      estimated_completion: '2025-10-11T10:05:00Z',
      sse_endpoint: '/api/analyze/stream/123',
    });

    await renderInputPage();

    await act(async () => {
      await userEvent.click(await screen.findByText('官方示例'));
    });

    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: '开始 5 分钟分析' }));
    });

    await waitFor(() => {
      expect(mockCreateAnalyzeTask).toHaveBeenCalledWith({
        product_description: '一个帮助跨境卖家统一看清多平台回款、手续费和退款损耗的利润看板。',
      });
    });

    expect(mockCreateAnalyzeTask.mock.calls[0]?.[0]).not.toHaveProperty('example_id');
  });

  it('submits topic_profile_id when guidance sample declares a golden path profile', async () => {
    mockGetInputGuidance.mockResolvedValueOnce({
      examples: [
        {
          title: '跨境支付/收款',
          prompt: '跨境卖家支付与收款效率分析，重点看 payout 延迟、手续费和风控冻结。',
          tags: ['跨境', '支付'],
          topic_profile_id: 'cross_border_payment_v1',
        },
      ],
    });
    mockCreateAnalyzeTask.mockResolvedValue({
      task_id: '123e4567-e89b-12d3-a456-426614174777',
      status: 'pending',
      created_at: '2025-10-11T10:00:00Z',
      estimated_completion: '2025-10-11T10:05:00Z',
      sse_endpoint: '/api/analyze/stream/123',
    });

    await renderInputPage();

    await act(async () => {
      await userEvent.click(await screen.findByText('跨境支付/收款'));
    });

    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: '开始 5 分钟分析' }));
    });

    await waitFor(() => {
      expect(mockCreateAnalyzeTask).toHaveBeenCalledWith({
        product_description: '跨境卖家支付与收款效率分析，重点看 payout 延迟、手续费和风控冻结。',
        topic_profile_id: 'cross_border_payment_v1',
      });
    });
  });

  it('shows error banner when API request fails', async () => {
    mockCreateAnalyzeTask.mockRejectedValue(new Error('network error'));

    await renderInputPage();

    const textarea = screen.getByRole('textbox', { name: /产品描述/i });

    await act(async () => {
      await userEvent.type(
        textarea,
        '一个帮助初创企业创始人追踪竞争对手动态的工具。'
      );
    });

    const submitButton = screen.getByRole('button', { name: '开始 5 分钟分析' });

    await act(async () => {
      await userEvent.click(submitButton);
    });

    expect(await screen.findByText('任务创建失败，请稍后重试或联系支持团队。')).toBeInTheDocument();
  });

  it('shows prefill banner and restores analysis direction from route state', async () => {
    await renderInputPage([
      {
        pathname: '/',
        state: {
          prefillProductDescription: '跨境卖家多平台利润追踪工具，解决手续费和回款分散的问题。',
          prefillSource: 'report',
          prefillHint: '已带回这次分析方向。你可以直接放大范围再跑一轮。',
        },
      },
    ]);

    expect(screen.getByText('已带回这次分析方向')).toBeInTheDocument();
    expect(screen.getByText('已带回这次分析方向。你可以直接放大范围再跑一轮。')).toBeInTheDocument();
    const textarea = screen.getByRole('textbox', { name: /产品描述/i }) as HTMLTextAreaElement;
    await waitFor(() => {
      expect(textarea.value).toContain('跨境卖家多平台利润追踪工具');
    });
  });
});
