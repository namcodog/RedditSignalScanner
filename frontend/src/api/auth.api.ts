/**
 * 认证 API 服务
 * 
 * 基于 PRD-06 用户认证系统
 * 最后更新: 2025-10-10 Day 2
 */

import { apiClient, setAuthToken, clearAuthToken } from './client';
import type {
  RegisterRequest,
  LoginRequest,
  AuthResponse,
  User,
} from '@/types';
import { SubscriptionTier } from '@/types';

/**
 * 后端认证响应（snake_case）
 */
interface BackendAuthResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: {
    id: string;
    email: string;
  };
}

/**
 * 用户注册
 *
 * POST /api/auth/register
 *
 * @param request 注册请求
 * @returns 认证响应
 */
export const register = async (
  request: RegisterRequest
): Promise<AuthResponse> => {
  const response = await apiClient.post<BackendAuthResponse>('/auth/register', request);

  // 保存 token
  setAuthToken(response.data.access_token);

  // 转换为前端格式
  return {
    accessToken: response.data.access_token,
    tokenType: response.data.token_type,
    expiresIn: 86400, // 24小时（从 expires_at 计算）
    user: {
      id: response.data.user.id,
      email: response.data.user.email,
      createdAt: new Date().toISOString(),
      isActive: true,
      subscriptionTier: SubscriptionTier.FREE,
    },
  };
};

/**
 * 用户登录
 *
 * POST /api/auth/login
 *
 * @param request 登录请求
 * @returns 认证响应
 */
export const login = async (
  request: LoginRequest
): Promise<AuthResponse> => {
  const response = await apiClient.post<BackendAuthResponse>('/auth/login', request);

  // 保存 token
  setAuthToken(response.data.access_token);

  // 转换为前端格式
  return {
    accessToken: response.data.access_token,
    tokenType: response.data.token_type,
    expiresIn: 86400,
    user: {
      id: response.data.user.id,
      email: response.data.user.email,
      createdAt: new Date().toISOString(),
      isActive: true,
      subscriptionTier: SubscriptionTier.FREE,
    },
  };
};

/**
 * 用户登出
 */
export const logout = (): void => {
  clearAuthToken();
  // TODO: 跳转到登录页面
  // window.location.href = '/login';
};

/**
 * 获取当前用户信息
 *
 * GET /api/auth/me
 *
 * @returns 用户信息
 */
export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>('/auth/me');
  return response.data;
};

/**
 * 检查用户是否已登录
 */
export const isAuthenticated = (): boolean => {
  const token = localStorage.getItem('auth_token');
  return token !== null && token.length > 0;
};

