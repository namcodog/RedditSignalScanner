/**
 * SSE (Server-Sent Events) 客户端实现
 *
 * 基于 PRD-02 API 设计规范
 * 最后更新: 2025-10-11 Day 6
 *
 * 功能：
 * - SSE 连接管理（使用 fetch-event-source 支持自定义头）
 * - 自动重连机制
 * - 心跳检测
 * - 自动降级到轮询
 */

import { fetchEventSource, EventSourceMessage } from '@microsoft/fetch-event-source';
import type {
  SSEEvent,
  SSEConnectionStatus,
  SSEClientConfig,
  SSEEventHandler,
} from '@/types';

/**
 * SSE 客户端类
 */
export class SSEClient {
  private abortController: AbortController | null = null;
  private config: Required<SSEClientConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private status: SSEConnectionStatus = 'disconnected';
  private lastHeartbeat: number = Date.now();

  constructor(config: SSEClientConfig) {
    // 设置默认配置
    this.config = {
      url: config.url,
      reconnectInterval: config.reconnectInterval ?? 3000,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 5,
      heartbeatTimeout: config.heartbeatTimeout ?? 30000,
      onEvent: config.onEvent ?? ((_event: SSEEvent) => {
        // 默认空实现，确保回调类型一致
      }),
      onStatusChange: config.onStatusChange ?? ((_status: SSEConnectionStatus) => {
        // 默认空实现，确保回调类型一致
      }),
    };
  }
  
  /**
   * 连接 SSE
   */
  async connect(): Promise<void> {
    if (this.status === 'connected' || this.status === 'connecting') {
      console.warn('SSE 已连接或正在连接中');
      return;
    }

    this.updateStatus('connecting');
    this.abortController = new AbortController();

    const token = this.getAuthToken();

    try {
      await fetchEventSource(this.config.url, {
        signal: this.abortController.signal,
        headers: token !== null ? {
          'Authorization': `Bearer ${token}`,
        } : {},

        onopen: async (response) => {
          if (response.ok) {
            console.log('SSE 连接成功');
            this.updateStatus('connected');
            this.reconnectAttempts = 0;
            this.startHeartbeatMonitor();
          } else if (response.status === 401) {
            console.error('SSE 认证失败 (401)');
            this.updateStatus('failed');
            throw new Error('Unauthorized');
          } else {
            console.error(`SSE 连接失败: ${response.status}`);
            this.updateStatus('failed');
            throw new Error(`HTTP ${response.status}`);
          }
        },

        onmessage: (event: EventSourceMessage) => {
          this.handleMessage(event);
        },

        onerror: (error) => {
          console.error('SSE 连接错误:', error);
          this.updateStatus('failed');

          // 如果是认证错误，不重连
          if (error instanceof Error && error.message === 'Unauthorized') {
            throw error;
          }

          // 其他错误尝试重连
          this.attemptReconnect();
        },

        onclose: () => {
          console.log('SSE 连接关闭');
          this.updateStatus('closed');
        },
      });
    } catch (error) {
      console.error('SSE 连接失败:', error);
      this.updateStatus('failed');

      // 如果不是认证错误，尝试重连
      if (!(error instanceof Error && error.message === 'Unauthorized')) {
        this.attemptReconnect();
      }
    }
  }
  
  /**
   * 断开 SSE 连接
   */
  disconnect(): void {
    this.clearTimers();

    if (this.abortController !== null) {
      this.abortController.abort();
      this.abortController = null;
    }

    this.updateStatus('closed');
  }
  
  /**
   * 获取当前连接状态
   */
  getStatus(): SSEConnectionStatus {
    return this.status;
  }
  
  /**
   * 处理消息事件
   */
  private handleMessage(event: EventSourceMessage): void {
    try {
      // fetch-event-source 的 event 对象结构：
      // { id: string, event: string, data: string }
      const eventType = event.event || 'message';
      const data = JSON.parse(event.data) as Record<string, unknown>;

      // 更新心跳时间
      this.lastHeartbeat = Date.now();

      // 处理心跳事件
      if (eventType === 'heartbeat') {
        console.debug('收到心跳包');
        return;
      }

      // 构造 SSEEvent（合并 eventType 和 data）
      const sseEvent = {
        event: eventType,
        ...data,
      } as SSEEvent;

      // 调用事件处理器
      this.config.onEvent(sseEvent);

      // 处理完成或关闭事件
      if (eventType === 'completed' || eventType === 'close') {
        this.disconnect();
      }

    } catch (error) {
      console.error('解析 SSE 消息失败:', error, event);
    }
  }

  /**
   * 尝试重连
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('SSE 重连次数已达上限，停止重连');
      this.updateStatus('failed');
      return;
    }
    
    this.reconnectAttempts++;
    console.log(`SSE 重连尝试 ${this.reconnectAttempts}/${this.config.maxReconnectAttempts}`);
    
    this.reconnectTimer = window.setTimeout(() => {
      this.disconnect();
      this.connect();
    }, this.config.reconnectInterval);
  }
  
  /**
   * 启动心跳监控
   */
  private startHeartbeatMonitor(): void {
    this.heartbeatTimer = window.setInterval(() => {
      const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeat;
      
      if (timeSinceLastHeartbeat > this.config.heartbeatTimeout) {
        console.warn('心跳超时，尝试重连');
        this.disconnect();
        this.attemptReconnect();
      }
    }, this.config.heartbeatTimeout / 2);
  }
  
  /**
   * 清除定时器
   */
  private clearTimers(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
  
  /**
   * 更新连接状态
   */
  private updateStatus(status: SSEConnectionStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.config.onStatusChange(status);
    }
  }
  
  /**
   * 获取认证 token
   */
  private getAuthToken(): string | null {
    return localStorage.getItem('auth_token');
  }
}

/**
 * 创建 SSE 客户端
 */
export const createSSEClient = (config: SSEClientConfig): SSEClient => {
  return new SSEClient(config);
};

/**
 * SSE 客户端工厂函数（用于任务进度监听）
 */
export const createTaskProgressSSE = (
  taskId: string,
  onEvent: SSEEventHandler,
  onStatusChange?: (status: SSEConnectionStatus) => void
): SSEClient => {
  const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
  const config: SSEClientConfig = {
    url: `${baseURL}/api/analyze/stream/${taskId}`,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    heartbeatTimeout: 30000,
    onEvent,
  };

  if (onStatusChange !== undefined) {
    config.onStatusChange = onStatusChange;
  }

  return createSSEClient(config);
};
