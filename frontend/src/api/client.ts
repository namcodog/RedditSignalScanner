/**
 * API 客户端配置
 * 
 * 基于 PRD-02 API 设计规范
 * 最后更新: 2025-10-10 Day 2
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse, ErrorResponse } from '@/types';

/**
 * API 客户端配置接口
 */
export interface ApiClientConfig {
  /** API 基础 URL */
  baseURL: string;
  
  /** 请求超时时间（毫秒） */
  timeout: number;
  
  /** 是否自动添加认证 token */
  withAuth: boolean;
  
  /** 是否在请求中包含 credentials */
  withCredentials: boolean;
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG: ApiClientConfig = {
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8006',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  withAuth: true,
  withCredentials: false,
};

/**
 * 创建 Axios 实例
 */
const createAxiosInstance = (config: Partial<ApiClientConfig> = {}): AxiosInstance => {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };
  
  const instance = axios.create({
    baseURL: finalConfig.baseURL,
    timeout: finalConfig.timeout,
    withCredentials: finalConfig.withCredentials,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  });
  
  // 请求拦截器：添加认证 token
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      if (finalConfig.withAuth) {
        const token = getAuthToken();
        if (token !== null && config.headers !== undefined) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }

      // 添加请求 ID（用于追踪）
      if (config.headers !== undefined) {
        config.headers['X-Request-ID'] = generateRequestId();
      }

      // 开发模式日志
      if (import.meta.env.VITE_DEV_MODE && import.meta.env.VITE_LOG_API_REQUESTS) {
        console.log('[API Request]', {
          method: config.method?.toUpperCase(),
          url: config.url,
          headers: config.headers,
          data: config.data,
        });
      }

      return config;
    },
    (error: AxiosError) => {
      console.error('[API Request Error]', error);
      return Promise.reject(error);
    }
  );
  
  // 响应拦截器：统一错误处理
  instance.interceptors.response.use(
    (response) => {
      // 开发模式日志
      if (import.meta.env.VITE_DEV_MODE && import.meta.env.VITE_LOG_API_REQUESTS) {
        console.log('[API Response]', {
          status: response.status,
          url: response.config.url,
          data: response.data,
        });
      }

      // 成功响应直接返回
      return response;
    },
    (error: AxiosError<ErrorResponse>) => {
      // 统一错误处理
      return handleApiError(error);
    }
  );
  
  return instance;
};

/**
 * 获取认证 token
 */
const getAuthToken = (): string | null => {
  // 从 localStorage 获取 token
  return localStorage.getItem('auth_token');
};

/**
 * 设置认证 token
 */
export const setAuthToken = (token: string): void => {
  localStorage.setItem('auth_token', token);
};

/**
 * 清除认证 token
 */
export const clearAuthToken = (): void => {
  localStorage.removeItem('auth_token');
};

/**
 * 生成请求 ID
 */
const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
};

/**
 * 统一错误处理
 */
const handleApiError = (error: AxiosError<ErrorResponse>): Promise<never> => {
  // 开发模式详细日志（仅在启用 VITE_LOG_API_REQUESTS 时输出）
  if (import.meta.env.VITE_DEV_MODE && import.meta.env.VITE_LOG_API_REQUESTS) {
    console.error('[API Error]', {
      message: error.message,
      response: error.response,
      request: error.request,
    });
  }

    if (error.response !== undefined) {
      // 服务器返回错误响应
      const { status, data } = error.response;

    // 401 未授权：清除 token 并跳转登录
    // 注意：只有真正的认证错误才重定向，404 等其他错误不应该触发重定向
    if (status === 401) {
      console.error('[Auth Error] Token expired or invalid');
      clearAuthToken();
      // 跳转到登录页面（但不在登录页、注册页或报告页时才跳转）
      if (typeof window !== 'undefined' &&
          !window.location.pathname.includes('/login') &&
          !window.location.pathname.includes('/register') &&
          !window.location.pathname.includes('/report')) {
        window.location.href = '/login';
      }
    }

    // 403 无权限
    if (status === 403) {
      console.error('[Auth Error] Permission denied');
    }

    // 404 资源不存在（不触发登录重定向）
    if (status === 404) {
      console.error('[API Error] Resource not found');
    }

    // 409 冲突（如邮箱已存在）
    if (status === 409) {
      console.error('[API Error] Conflict:', data);
    }

    // 422 请求验证失败
    if (status === 422) {
      console.error('[Validation Error]', data);
    }

    // 429 限流：提示用户稍后重试
    if (status === 429) {
      console.warn('[API Error] Rate limit exceeded');
    }

    // 500 服务器错误
    if (status === 500) {
      console.error('[Server Error] Internal server error');
    }

    // 返回格式化的错误信息
    return Promise.reject({
      status,
      error: data.error,
      message: data.error?.message ?? '请求失败',
      code: data.error?.code ?? 'UNKNOWN_ERROR',
    });
  } else if (error.request !== undefined) {
    // 请求已发送但没有收到响应（网络错误）
    console.error('[Network Error] No response received');
    return Promise.reject({
      status: 0,
      message: '网络连接失败，请检查网络设置',
      code: 'NETWORK_ERROR',
    });
  } else {
    // 请求配置错误
    console.error('[Request Error]', error.message);
    return Promise.reject({
      status: 0,
      message: error.message ?? '请求配置错误',
      code: 'REQUEST_CONFIG_ERROR',
    });
  }
};

/**
 * 默认 API 客户端实例
 */
export const apiClient = createAxiosInstance();

/**
 * 创建自定义 API 客户端
 */
export const createApiClient = (config: Partial<ApiClientConfig> = {}): AxiosInstance => {
  return createAxiosInstance(config);
};

/**
 * API 响应包装器（泛型）
 */
export const wrapApiResponse = <T>(data: T): ApiResponse<T> => {
  return {
    data,
    meta: {
      requestId: generateRequestId(),
      timestamp: new Date().toISOString(),
    },
  };
};

/**
 * 检查 API 是否可用
 */
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/health');
    return response.status === 200;
  } catch {
    return false;
  }
};
