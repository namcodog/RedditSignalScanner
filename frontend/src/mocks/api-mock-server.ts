/**
 * API Mock Server
 * 
 * 用于前端开发和测试的 Mock API 服务器
 * 基于 PRD-02 API 设计规范
 */

import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { beforeAll, afterEach, afterAll } from 'vitest';
import { TaskStatus, Sentiment } from '@/types';

const API_BASE_URL = 'http://localhost:8000/api';

// Mock 数据
const mockTaskId = 'test-task-123';
const mockUserId = 'test-user-456';

// Mock 处理器
export const handlers = [
  // POST /api/analyze - 创建分析任务
  http.post(`${API_BASE_URL}/analyze`, async ({ request }: { request: Request }) => {
    const body = await request.json() as { product_description: string };
    
    if (body.product_description.length < 10) {
      return HttpResponse.json(
        {
          detail: [
            {
              type: 'string_too_short',
              loc: ['body', 'product_description'],
              msg: 'String should have at least 10 characters',
              input: body.product_description,
            },
          ],
        },
        { status: 422 }
      );
    }

    return HttpResponse.json({
      task_id: mockTaskId,
      status: TaskStatus.PENDING,
      created_at: new Date().toISOString(),
      estimated_duration_seconds: 300,
    });
  }),

  // GET /api/status/{task_id} - 查询任务状态
  http.get(`${API_BASE_URL}/status/:taskId`, ({ params }: { params: Record<string, string> }) => {
    const { taskId } = params;

    if (taskId === 'non-existent') {
      return HttpResponse.json(
        { detail: 'Task not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      task_id: taskId,
      status: TaskStatus.COMPLETED,
      progress: 100,
      current_step: 'Analysis completed',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }),

  // GET /api/analyze/stream/{task_id} - SSE 连接
  http.get(`${API_BASE_URL}/analyze/stream/:taskId`, () => {
    // SSE 在 MSW 中需要特殊处理，这里返回基本响应
    return new HttpResponse(null, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }),

  // GET /api/report/{task_id} - 获取分析报告
  http.get(`${API_BASE_URL}/report/:taskId`, ({ params }: { params: Record<string, string> }) => {
    const { taskId } = params;

    if (taskId === 'non-existent') {
      return HttpResponse.json(
        { detail: 'Report not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      task_id: taskId,
      status: 'completed',
      generated_at: new Date().toISOString(),
      product_description: '一款专为自由职业者设计的时间追踪和发票管理工具，帮助用户高效管理项目时间并自动生成专业发票',
      report: {
        executive_summary: {
          total_communities: 5,
          key_insights: 12,
          top_opportunity: '开发移动端应用以满足用户随时随地访问的需求',
        },
        pain_points: [
          {
            description: '产品价格过高，超出预算',
            frequency: 42,
            sentiment_score: -0.6,
            severity: 'high' as const,
            user_examples: [
              '价格太贵了，希望有更便宜的替代品',
              '功能不错但价格不合理',
              '对于小团队来说成本太高'
            ],
            example_posts: [
              {
                community: 'r/productivity',
                content: '价格太贵了，希望有更便宜的替代品',
                upvotes: 156,
                url: 'https://reddit.com/r/productivity/example1',
              },
              {
                community: 'r/software',
                content: '功能不错但价格不合理',
                upvotes: 89,
              },
            ],
          },
          {
            description: '缺少移动端支持',
            frequency: 38,
            sentiment_score: -0.5,
            severity: 'medium' as const,
            user_examples: [
              '希望有手机版应用',
              '需要在移动设备上使用',
              '出差时无法使用很不方便'
            ],
            example_posts: [
              {
                community: 'r/apps',
                content: '希望有手机版应用',
                upvotes: 124,
              },
            ],
          },
        ],
        competitors: [
          {
            name: 'Notion',
            mentions: 156,
            sentiment: Sentiment.POSITIVE,
            strengths: ['协作功能强大', '模板丰富', '数据库功能'],
            weaknesses: ['价格较高', '学习曲线陡峭'],
            market_share: 35,
          },
          {
            name: 'Trello',
            mentions: 89,
            sentiment: Sentiment.MIXED,
            strengths: ['简单易用', '看板视图', '免费版功能足够'],
            weaknesses: ['功能相对简单', '缺少高级功能'],
            market_share: 25,
          },
        ],
        opportunities: [
          {
            description: '开发移动端应用',
            relevance_score: 0.85,
            potential_users: '5000+ 活跃用户表达需求',
            key_insights: [
              '用户强烈需求移动端访问',
              '竞品移动端体验普遍较差',
              '可以作为差异化竞争优势',
              '预计可提升用户留存率30%'
            ],
          },
          {
            description: '提供更灵活的定价方案',
            relevance_score: 0.72,
            potential_users: '3200+ 用户关注价格问题',
            key_insights: [
              '价格是用户流失的主要原因',
              '小团队和个人用户对价格敏感',
              '按需付费模式可能更受欢迎',
              '竞品定价策略存在优化空间'
            ],
          },
        ],
      },
      metadata: {
        analysis_version: '1.0',
        confidence_score: 0.87,
        processing_time_seconds: 245.3,
        cache_hit_rate: 0.65,
        total_mentions: 15847,
      },
      overview: {
        sentiment: {
          positive: 58,
          negative: 23,
          neutral: 19,
        },
        top_communities: [
          {
            name: 'r/productivity',
            mentions: 5234,
            relevance: 89,
            category: '生产力工具',
            daily_posts: 450,
            avg_comment_length: 180,
            from_cache: false,
          },
          {
            name: 'r/freelance',
            mentions: 3421,
            relevance: 85,
            category: '自由职业',
            daily_posts: 320,
            avg_comment_length: 220,
            from_cache: false,
          },
          {
            name: 'r/startups',
            mentions: 2876,
            relevance: 78,
            category: '创业',
            daily_posts: 280,
            avg_comment_length: 250,
            from_cache: true,
          },
          {
            name: 'r/software',
            mentions: 2145,
            relevance: 72,
            category: '软件工具',
            daily_posts: 380,
            avg_comment_length: 160,
            from_cache: false,
          },
          {
            name: 'r/apps',
            mentions: 2171,
            relevance: 70,
            category: '应用推荐',
            daily_posts: 420,
            avg_comment_length: 140,
            from_cache: false,
          },
        ],
      },
      stats: {
        total_mentions: 15847,
        positive_mentions: 9191,
        negative_mentions: 3645,
        neutral_mentions: 3011,
      },
    });
  }),

  // POST /api/auth/register - 用户注册
  http.post(`${API_BASE_URL}/auth/register`, () => {
    return HttpResponse.json({
      user_id: mockUserId,
      token: 'mock-jwt-token-' + Date.now(),
      subscription_tier: 'free',
      created_at: new Date().toISOString(),
    });
  }),
];

// 创建 Mock 服务器
export const server = setupServer(...handlers);

// 测试生命周期钩子
export function setupMockServer() {
  beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
}

