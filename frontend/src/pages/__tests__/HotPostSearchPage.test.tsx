import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HotPostSearchPage from '../hotpost/HotPostSearchPage';

vi.mock('@/services/hotpost.service', () => ({
  searchHotPost: vi.fn(),
}));

import * as hotpostService from '@/services/hotpost.service';

describe('HotPostSearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(hotpostService.searchHotPost).mockResolvedValue({
      query_id: 'hotpost-q1',
      status: 'queued',
    } as any);
  });

  it('应该在 rant 模式下把标签确认结果带进 query_parse_override', async () => {
    render(
      <MemoryRouter initialEntries={['/hotpost']}>
        <Routes>
          <Route path="/hotpost" element={<HotPostSearchPage />} />
          <Route path="/hotpost/result/:queryId" element={<div>result</div>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByText('用户声音证据'));
    fireEvent.change(screen.getByLabelText(/关键词 \/ 话题/i), {
      target: { value: '为什么大家说 Codex 比 Claude 更能听懂长指令' },
    });

    expect(screen.getByText('搜索标签确认')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('类型'), {
      target: { value: 'compare' },
    });
    fireEvent.change(screen.getByPlaceholderText('例如：Notion AI'), {
      target: { value: 'Codex' },
    });
    fireEvent.change(screen.getByPlaceholderText('例如：Claude'), {
      target: { value: 'Claude' },
    });
    fireEvent.change(screen.getByPlaceholderText('例如：改写成空话、听懂长指令、总是崩掉'), {
      target: { value: '听懂长指令' },
    });
    fireEvent.change(screen.getByPlaceholderText('例如：AI coding、视频剪辑、团队协作'), {
      target: { value: 'AI coding' },
    });

    fireEvent.click(screen.getByRole('button', { name: /开始扫描/i }));

    await waitFor(() => {
      expect(hotpostService.searchHotPost).toHaveBeenCalledTimes(1);
    });

    expect(hotpostService.searchHotPost).toHaveBeenCalledWith({
      query: '为什么大家说 Codex 比 Claude 更能听懂长指令',
      mode: 'rant',
      query_parse_override: {
        query_kind: 'compare',
        subject: 'Codex',
        compare_target: 'Claude',
        focus: '听懂长指令',
        scenario: 'AI coding',
      },
    });
  });
});
