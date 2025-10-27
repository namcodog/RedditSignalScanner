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

vi.mock('@/api/analyze.api', () => ({
  createAnalyzeTask: (...args: unknown[]) => mockCreateAnalyzeTask(...args),
}));

vi.mock('@/api/auth.api', () => ({
  register: (...args: unknown[]) => mockRegister(...args),
  isAuthenticated: () => mockIsAuthenticated(),
}));

const renderInputPage = async () => {
  let result;
  await act(async () => {
    result = render(
      <MemoryRouter>
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

    // 默认情况下，假设用户已认证，避免触发自动认证流程
    mockIsAuthenticated.mockReturnValue(true);
  });

  it('disables submit button until minimum characters are met', async () => {
    await renderInputPage();
    const submitButton = screen.getByTestId('submit-button');
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
    const sampleButton = screen.getByRole('button', { name: /示例 1/i });

    await act(async () => {
      await userEvent.click(sampleButton);
    });

    const textarea = screen.getByRole('textbox', { name: /产品描述/i }) as HTMLTextAreaElement;

    // 等待状态更新
    await waitFor(() => {
      expect(textarea.value).toMatch(/忙碌专业人士进行餐食准备/);
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

    const submitButton = screen.getByTestId('submit-button');

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

    const submitButton = screen.getByTestId('submit-button');

    await act(async () => {
      await userEvent.click(submitButton);
    });

    // 等待错误提示出现
    const alert = await screen.findByRole('alert');
    await waitFor(() => {
      expect(alert).toHaveTextContent('任务创建失败');
    });
  });
});
