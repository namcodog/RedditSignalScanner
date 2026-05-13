import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HotPostClueDetailPage from '../hotpost/HotPostClueDetailPage';

vi.mock('@/services/hotpostClues.service', () => ({
  getClueDetail: vi.fn(),
  recordClueCopy: vi.fn(),
  toggleClueFavorite: vi.fn(),
}));

import * as clueService from '@/services/hotpostClues.service';

describe('HotPostClueDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(clueService.getClueDetail).mockResolvedValue({
      id: 'clue-1',
      title: 'AI coding 一到大代码仓就容易乱改',
      one_liner: '大家已经不只是吐槽，而是在找替代做法。',
      audience: '研发团队',
      why_now: '近 7 天持续反复出现。',
      primary_tag: 'both',
      secondary_tags: ['pitfall'],
      preview_quotes: [],
      full_quotes: [{ text: '它总在我没让它动的地方动手。', community: 'r/codex', permalink: 'https://reddit.com/1' }],
      source_meta: { observation_topic: 'AI Coding', time_window_days: 7, thread_count: 4, community_count: 2, intent_tags: ['明确阻塞'] },
      validation_sheet: { hypothesis: '验证假设', target_user: '研发团队', next_action: '访谈', success_signal: '愿意聊', stop_signal: '没人理', copy_payload: '验证小抄正文' },
      content_sheet: { core_thesis: '核心观点', angle: '避坑', title_hooks: ['标题1'], outline: ['提纲1'], quote_pack: ['原话1'], copy_payload: '内容小抄正文' },
      hotpost_detail_url: '/hotpost/lab/search',
      published_at: '2026-04-03T08:00:00Z',
      favorited: false,
    } as any);
  });

  it('应该展示线索详情和验证小抄', async () => {
    render(
      <MemoryRouter initialEntries={['/hotpost/clues/clue-1?sheet=validate']}>
        <Routes>
          <Route path="/hotpost/clues/:clueId" element={<HotPostClueDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText('AI coding 一到大代码仓就容易乱改')).toBeInTheDocument());
    expect(screen.getByText('验证小抄')).toBeInTheDocument();
    expect(screen.getByText('验证小抄正文')).toBeInTheDocument();
  });
});
