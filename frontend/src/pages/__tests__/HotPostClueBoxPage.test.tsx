import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HotPostClueBoxPage from '../hotpost/HotPostClueBoxPage';

vi.mock('@/services/hotpostClues.service', () => ({
  getClueBox: vi.fn(),
  toggleClueFavorite: vi.fn(),
}));

import * as clueService from '@/services/hotpostClues.service';

describe('HotPostClueBoxPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(clueService.getClueBox).mockResolvedValue({
      items: [
        {
          id: 'clue-1',
          title: '很多团队开始把项目管理抱怨，转成对 Linear 的偏好',
          one_liner: '讨论已经走到换不换的阶段。',
          audience: '产品经理',
          why_now: '替代意向变强。',
          primary_tag: 'both',
          secondary_tags: ['switch'],
          preview_quotes: [{ text: '我们每天都在跟它搏斗。', community: 'r/projectmanagement', permalink: 'https://reddit.com/1' }],
          hotpost_detail_url: '/hotpost/lab/search',
          published_at: '2026-04-03T08:00:00Z',
          favorited: true,
        },
      ],
      next_cursor: null,
    });
    vi.mocked(clueService.toggleClueFavorite).mockResolvedValue({ favorited: false });
  });

  it('应该展示线索箱并支持取消收藏', async () => {
    render(
      <MemoryRouter initialEntries={['/hotpost/box']}>
        <Routes>
          <Route path="/hotpost/box" element={<HotPostClueBoxPage />} />
          <Route path="/hotpost/clues/:clueId" element={<div>detail</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText('很多团队开始把项目管理抱怨，转成对 Linear 的偏好')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: '收藏' }));
    await waitFor(() => expect(clueService.toggleClueFavorite).toHaveBeenCalledWith('clue-1', 'remove'));
  });
});
