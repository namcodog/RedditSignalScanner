import { apiClient } from '@/api/client';
import { createSSEClient } from '@/api/sse.client';
import { SSEConnectionStatus, SSEEvent } from '@/types';
import {
  HotPostRequest,
  HotPostResponse,
  DeepDiveResponse,
  DeepDiveRequest,
} from '@/types/hotpost';

const HOTPOST_BASE = '/hotpost';

// Default mappings
const DEFAULT_TIME_FILTERS = {
  trending: 'week',
  opportunity: 'month',
  rant: 'all',
} as const;

/**
 * Initiate a HotPost search.
 * This might return a cached result immediately or a "queued" status.
 */
export const searchHotPost = async (
  request: HotPostRequest
): Promise<HotPostResponse> => {
  // Apply defaults
  const mode = request.mode || 'trending';
  const time_filter = request.time_filter || DEFAULT_TIME_FILTERS[mode];

  const payload = {
    ...request,
    mode,
    time_filter,
  };

  const response = await apiClient.post<HotPostResponse>(
    `${HOTPOST_BASE}/search`,
    payload
  );
  return response.data;
};

/**
 * Poll for the result of a specific query.
 * Used when the initial search returns a 'queued' status or for refreshing data.
 * Note: If the backend does not return an explicit 'status' field, assume success.
 */
export const getHotPostResult = async (
  queryId: string
): Promise<HotPostResponse> => {
  const response = await apiClient.get<HotPostResponse>(
    `${HOTPOST_BASE}/result/${queryId}`
  );
  return response.data;
};

/**
 * Generate a Deep Dive token for transitioning to the main report generation flow.
 * Requires authentication.
 */
export const generateDeepDiveToken = async (
  request: DeepDiveRequest
): Promise<DeepDiveResponse> => {
  const response = await apiClient.post<DeepDiveResponse>(
    `${HOTPOST_BASE}/deepdive`,
    request
  );
  return response.data;
};

/**
 * Subscribe to the HotPost SSE stream for queue updates and completion.
 */
export const subscribeToHotPostStream = (
  queryId: string,
  onEvent: (event: SSEEvent) => void,
  onStatusChange?: (status: SSEConnectionStatus) => void
) => {
  const client = createSSEClient({
    url: `${import.meta.env.VITE_API_BASE_URL || '/api'}${HOTPOST_BASE}/stream/${queryId}`,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    onEvent,
    onStatusChange: onStatusChange || (() => {}),
  });
  
  client.connect();
  return client;
};