/**
 * 用户相关类型定义
 * 
 * 基于 Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-10 Day 1
 */

/**
 * 订阅等级枚举
 */
export enum SubscriptionTier {
  /** 免费版 */
  FREE = 'free',
  /** 专业版 */
  PRO = 'pro',
  /** 企业版 */
  ENTERPRISE = 'enterprise',
}

/**
 * 用户信息接口
 */
export interface User {
  /** 用户 ID (UUID) */
  id: string;
  
  /** 邮箱地址 */
  email: string;
  
  /** 账户创建时间 (ISO 8601) */
  createdAt: string;
  
  /** 最后登录时间 (ISO 8601)，首次注册时为 null */
  lastLoginAt?: string;
  
  /** 账户是否激活 */
  isActive: boolean;
  
  /** 订阅等级 */
  subscriptionTier: SubscriptionTier;
  
  /** 订阅过期时间 (ISO 8601)，免费用户为 null */
  subscriptionExpiresAt?: string;
}

/**
 * 注册请求接口
 */
export interface RegisterRequest {
  /** 邮箱地址 */
  email: string;
  
  /** 密码（最小 8 字符） */
  password: string;
}

/**
 * 登录请求接口
 */
export interface LoginRequest {
  /** 邮箱地址 */
  email: string;
  
  /** 密码 */
  password: string;
}

/**
 * 认证响应接口
 */
export interface AuthResponse {
  /** JWT 访问令牌 */
  accessToken: string;
  
  /** 令牌类型（通常为 "Bearer"） */
  tokenType: string;
  
  /** 令牌过期时间（秒） */
  expiresIn: number;
  
  /** 用户信息 */
  user: User;
}

/**
 * 用户信息更新请求接口
 */
export interface UpdateUserRequest {
  /** 新邮箱地址（可选） */
  email?: string;
  
  /** 新密码（可选，最小 8 字符） */
  password?: string;
}

