/**
 * SSE (Server-Sent Events) 相关类型定义
 * 
 * 基于 PRD-02 API 设计规范 & Schema 契约: reports/phase-log/schema-contract.md
 * 最后更新: 2025-10-11 Day 5
 */

import type { TaskStatus } from './task.types';

/**
 * SSE 事件类型
 */
export type SSEEventType =
  | 'connected'
  | 'progress'
  | 'completed'
  | 'error'
  | 'close'
  | 'heartbeat';

/**
 * SSE 连接状态
 */
export type SSEConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'failed'
  | 'closed';

/**
 * SSE 基础事件接口
 */
export interface SSEBaseEvent {
  /** 事件类型 */
  event: SSEEventType;
  
  /** 任务 ID (UUID) */
  task_id: string;
  
  /** 事件时间戳 (ISO 8601) */
  timestamp?: string;
}

/**
 * SSE 连接成功事件
 */
export interface SSEConnectedEvent extends SSEBaseEvent {
  event: 'connected';
}

/**
 * SSE 进度更新事件
 */
export interface SSEProgressEvent extends SSEBaseEvent {
  event: 'progress';

  /** 任务状态 */
  status: TaskStatus;

  /** 完成百分比（0-100） */
  progress: number;

  /** 当前步骤消息 */
  message: string;

  /** 错误信息（进行中时应为 null） */
  error: string | null;

  /** 更新时间 (ISO 8601) */
  updated_at: string;

  /** 当前步骤名称（可选，用于兼容） */
  current_step?: string;

  /** 完成百分比（可选，用于兼容） */
  percentage?: number;

  /** 预计剩余时间（秒，可选） */
  estimated_remaining?: number;
}

/**
 * SSE 任务完成事件
 */
export interface SSECompletedEvent extends SSEBaseEvent {
  event: 'completed';

  /** 任务状态 */
  status: TaskStatus;

  /** 完成百分比（应为 100） */
  progress: number;

  /** 完成消息 */
  message: string;

  /** 错误信息（完成时应为 null） */
  error: string | null;

  /** 更新时间 (ISO 8601) */
  updated_at: string;
}

/**
 * SSE 错误事件
 */
export interface SSEErrorEvent extends SSEBaseEvent {
  event: 'error';
  
  /** 错误码 */
  error_code: string;
  
  /** 错误消息 */
  error_message: string;
  
  /** 是否可重试 */
  retryable: boolean;
}

/**
 * SSE 连接关闭事件
 */
export interface SSECloseEvent {
  event: 'close';

  /** 任务 ID (UUID) */
  task_id: string;
}

/**
 * SSE 心跳事件
 */
export interface SSEHeartbeatEvent extends SSEBaseEvent {
  event: 'heartbeat';
}

/**
 * SSE 事件联合类型
 */
export type SSEEvent =
  | SSEConnectedEvent
  | SSEProgressEvent
  | SSECompletedEvent
  | SSEErrorEvent
  | SSECloseEvent
  | SSEHeartbeatEvent;

/**
 * SSE 事件处理器类型
 */
export type SSEEventHandler = (event: SSEEvent) => void;

/**
 * SSE 客户端配置接口
 */
export interface SSEClientConfig {
  /** SSE 端点 URL */
  url: string;
  
  /** 重连间隔（毫秒），默认 3000 */
  reconnectInterval?: number;
  
  /** 最大重连次数，默认 5 */
  maxReconnectAttempts?: number;
  
  /** 心跳超时时间（毫秒），默认 30000 */
  heartbeatTimeout?: number;
  
  /** 事件处理器 */
  onEvent?: SSEEventHandler;
  
  /** 连接状态变化处理器 */
  onStatusChange?: (status: SSEConnectionStatus) => void;
}
