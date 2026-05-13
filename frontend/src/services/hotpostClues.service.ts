import { apiClient } from '@/api/client';
import type { ClueBoxTab, ClueDetail, ClueListResponse, ClueListTab } from '@/types/hotpostClues';

const HOTPOST_CLUES_BASE = '/hotpost';
const HOTPOST_SESSION_KEY = 'hotpost_clue_session_id';

const getSessionId = (): string => {
  const existing = localStorage.getItem(HOTPOST_SESSION_KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  localStorage.setItem(HOTPOST_SESSION_KEY, created);
  return created;
};

const clueHeaders = () => ({ 'X-Session-Id': getSessionId() });

export const listClues = async (tab: ClueListTab = 'all'): Promise<ClueListResponse> => {
  const response = await apiClient.get<ClueListResponse>(`${HOTPOST_CLUES_BASE}/clues`, { headers: clueHeaders(), params: { tab } });
  return response.data;
};

export const getClueDetail = async (clueId: string): Promise<ClueDetail> => {
  const response = await apiClient.get<ClueDetail>(`${HOTPOST_CLUES_BASE}/clues/${clueId}`, { headers: clueHeaders() });
  return response.data;
};

export const toggleClueFavorite = async (clueId: string, action: 'add' | 'remove'): Promise<{ favorited: boolean }> => {
  const response = await apiClient.post<{ favorited: boolean }>(`${HOTPOST_CLUES_BASE}/clues/${clueId}/favorite`, { action }, { headers: clueHeaders() });
  return response.data;
};

export const recordClueCopy = async (clueId: string, type: 'validate' | 'write'): Promise<void> => {
  await apiClient.post(`${HOTPOST_CLUES_BASE}/clues/${clueId}/copy`, { type }, { headers: clueHeaders() });
};

export const getClueBox = async (tab: ClueBoxTab): Promise<ClueListResponse> => {
  const response = await apiClient.get<ClueListResponse>(`${HOTPOST_CLUES_BASE}/clue-box`, { headers: clueHeaders(), params: { tab } });
  return response.data;
};
