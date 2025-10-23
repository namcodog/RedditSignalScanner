/**
 * API 服务统一导出
 * 
 * 最后更新: 2025-10-10 Day 2
 */

// API 客户端
export {
  apiClient,
  createApiClient,
  setAuthToken,
  clearAuthToken,
  checkApiHealth,
} from './client';

// SSE 客户端
export {
  SSEClient,
  createSSEClient,
  createTaskProgressSSE,
} from './sse.client';

// 分析任务 API
export {
  createAnalyzeTask,
  getTaskStatus,
  getAnalysisReport,
  pollTaskUntilComplete,
  submitBetaFeedback,
} from './analyze.api';
export type { BetaFeedbackRequest, BetaFeedbackResponse } from './analyze.api';

// 认证 API
export {
  register,
  login,
  logout,
  getCurrentUser,
  isAuthenticated,
} from './auth.api';

