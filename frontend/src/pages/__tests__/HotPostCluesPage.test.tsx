import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HotPostCluesPage from '../hotpost/HotPostCluesPage';

vi.mock('@/services/hotpostClues.service', () => ({
  listClues: vi.fn(),
  toggleClueFavorite: vi.fn(),
}));

import * as clueService from '@/services/hotpostClues.service';

describe('HotPostCluesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(clueService.listClues).mockResolvedValue({
      items: [
        {
          id: 'clue-1',
          title: 'AI coding 一到大代码仓就容易乱改',
          one_liner: '大家已经不只是吐槽，而是在找替代做法。',
          audience: '研发团队',
          why_now: '近 7 天持续反复出现。',
          primary_tag: 'both',
          secondary_tags: ['pitfall'],
          preview_quotes: [
            { text: '它总在我没让它动的地方动手。', community: 'r/codex', permalink: 'https://reddit.com/1' },
            { text: '小项目还行，大仓库一上来就开始迷路。', community: 'r/artificial', permalink: 'https://reddit.com/2' },
          ],
          hotpost_detail_url: '/hotpost/lab/search',
          published_at: '2026-04-03T08:00:00Z',
          favorited: false,
        },
      ],
      next_cursor: null,
    });
    vi.mocked(clueService.toggleClueFavorite).mockResolvedValue({ favorited: true });
  });

  it('应该展示今日线索并支持收藏', async () => {
    render(
      <MemoryRouter initialEntries={['/hotpost']}>
        <Routes>
          <Route path="/hotpost" element={<HotPostCluesPage />} />
          <Route path="/hotpost/clues/:clueId" element={<div>detail</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText('AI coding 一到大代码仓就容易乱改')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: '收藏' }));

    await waitFor(() => expect(clueService.toggleClueFavorite).toHaveBeenCalledWith('clue-1', 'add'));
  });
});
