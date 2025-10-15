/**
 * SSE 自定义 Hook
 * 
 * 基于 PRD-02 API 设计规范
 * 最后更新: 2025-10-10 Day 2
 * 
 * 功能：
 * - 管理 SSE 连接生命周期
 * - 自动重连
 * - 自动降级到轮询
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { createTaskProgressSSE } from '@/api';
import { getTaskStatus } from '@/api';
import type {
  SSEEvent,
  SSEConnectionStatus,
  TaskStatusResponse,
} from '@/types';
import { TaskStatus } from '@/types';

/**
 * useSSE Hook 配置
 */
export interface UseSSEConfig {
  /** 任务 ID */
  taskId: string;
  
  /** 是否自动连接 */
  autoConnect?: boolean;
  
  /** 是否启用自动降级到轮询 */
  enableFallback?: boolean;
  
  /** 轮询间隔（毫秒） */
  pollingInterval?: number;
  
  /** SSE 事件处理器 */
  onEvent?: (event: SSEEvent) => void;
  
  /** 连接状态变化处理器 */
  onStatusChange?: (status: SSEConnectionStatus) => void;
  
  /** 降级到轮询时的回调 */
  onFallbackToPolling?: () => void;
}

/**
 * useSSE Hook 返回值
 */
export interface UseSSEReturn {
  /** 连接状态 */
  status: SSEConnectionStatus;
  
  /** 最新事件 */
  latestEvent: SSEEvent | null;
  
  /** 是否正在使用轮询模式 */
  isPolling: boolean;
  
  /** 手动连接 */
  connect: () => void;
  
  /** 手动断开 */
  disconnect: () => void;
  
  /** 手动切换到轮询模式 */
  switchToPolling: () => void;
}

/**
 * SSE 自定义 Hook
 */
export const useSSE = (config: UseSSEConfig): UseSSEReturn => {
  const {
    taskId,
    autoConnect = true,
    enableFallback = true,
    pollingInterval = 2000,
    onEvent,
    onStatusChange,
    onFallbackToPolling,
  } = config;
  
  const [status, setStatus] = useState<SSEConnectionStatus>('disconnected');
  const [latestEvent, setLatestEvent] = useState<SSEEvent | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  
  const sseClientRef = useRef<ReturnType<typeof createTaskProgressSSE> | null>(null);
  const pollingTimerRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);
  
  /**
   * 处理 SSE 事件
   */
  const handleEvent = useCallback((event: SSEEvent) => {
    if (!isMountedRef.current) return;
    
    setLatestEvent(event);
    
    if (onEvent !== undefined) {
      onEvent(event);
    }
  }, [onEvent]);
  
  /**
   * 处理连接状态变化
   */
  const handleStatusChange = useCallback((newStatus: SSEConnectionStatus) => {
    if (!isMountedRef.current) return;
    
    setStatus(newStatus);
    
    if (onStatusChange !== undefined) {
      onStatusChange(newStatus);
    }
    
    // SSE 连接失败时自动降级到轮询
    if (newStatus === 'failed' && enableFallback && !isPolling) {
      switchToPolling();
    }
  }, [onStatusChange, enableFallback, isPolling]);
  
  /**
   * 连接 SSE
   */
  const connect = useCallback(() => {
    if (sseClientRef.current !== null) {
      sseClientRef.current.disconnect();
    }
    
    sseClientRef.current = createTaskProgressSSE(
      taskId,
      handleEvent,
      handleStatusChange
    );
    
    sseClientRef.current.connect();
  }, [taskId, handleEvent, handleStatusChange]);
  
  /**
   * 断开 SSE
   */
  const disconnect = useCallback(() => {
    if (sseClientRef.current !== null) {
      sseClientRef.current.disconnect();
      sseClientRef.current = null;
    }
    
    if (pollingTimerRef.current !== null) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    
    setIsPolling(false);
  }, []);
  
  /**
   * 切换到轮询模式
   */
  const switchToPolling = useCallback(() => {
    if (isPolling) return;
    
    console.log('SSE 连接失败，切换到轮询模式');
    
    // 断开 SSE
    if (sseClientRef.current !== null) {
      sseClientRef.current.disconnect();
      sseClientRef.current = null;
    }
    
    setIsPolling(true);
    setStatus('disconnected');
    
    if (onFallbackToPolling !== undefined) {
      onFallbackToPolling();
    }
    
    // 开始轮询
    const poll = async () => {
      try {
        const taskStatus: TaskStatusResponse = await getTaskStatus(taskId);

        // 模拟 SSE 进度事件
        const progressEvent: SSEEvent = {
          event: 'progress',
          task_id: taskId,
          status: taskStatus.status,
          progress: taskStatus.progress?.percentage ?? 0,
          message: taskStatus.progress?.current_step ?? '处理中...',
          error: null,
          updated_at: new Date().toISOString(),
          current_step: taskStatus.progress?.current_step ?? '',
          percentage: taskStatus.progress?.percentage ?? 0,
          estimated_remaining: taskStatus.progress?.estimated_remaining ?? 0,
        };

        handleEvent(progressEvent);

        // 任务完成或失败时停止轮询
        if (taskStatus.status === 'completed' || taskStatus.status === 'failed') {
          if (pollingTimerRef.current !== null) {
            clearInterval(pollingTimerRef.current);
            pollingTimerRef.current = null;
          }

          // 发送完成事件
          const completedEvent: SSEEvent =
            taskStatus.status === 'completed'
              ? {
                  event: 'completed',
                  task_id: taskId,
                  status: TaskStatus.COMPLETED,
                  progress: 100,
                  message: '分析完成',
                  error: null,
                  updated_at: new Date().toISOString(),
                }
              : {
                  event: 'error',
                  task_id: taskId,
                  error_code: 'TASK_FAILED',
                  error_message: taskStatus.error_message ?? '任务失败',
                  retryable: false,
                };
          
          handleEvent(completedEvent);
        }
      } catch (error) {
        console.error('轮询任务状态失败:', error);
      }
    };
    
    // 立即执行一次
    void poll();
    
    // 设置定时轮询
    pollingTimerRef.current = window.setInterval(() => {
      void poll();
    }, pollingInterval);
  }, [isPolling, taskId, pollingInterval, handleEvent, onFallbackToPolling]);
  
  /**
   * 自动连接
   */
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    
    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);
  
  return {
    status,
    latestEvent,
    isPolling,
    connect,
    disconnect,
    switchToPolling,
  };
};
