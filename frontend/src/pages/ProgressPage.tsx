/**
 * 等待页面（Progress Page）
 *
 * 基于 v0 设计还原 (analysis-progress.tsx)
 * 集成 RedditScannerAnimation 和真实 SSE 逻辑
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Search,
  Download,
  Brain,
  Lightbulb,
  Clock,
  CheckCircle,
  Loader2,
  Users,
  MessageSquare,
  TrendingUp,
} from 'lucide-react';
import { createTaskProgressSSE } from '@/api/sse.client';
import type { SSEClient } from '@/api/sse.client';
import { getTaskStatus } from '@/api/analyze.api';
import { isAuthenticated, logout } from '@/api/auth.api';
import type { SSEEvent, SSEConnectionStatus } from '@/types';
import { ROUTES } from '@/router';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import RedditScannerAnimation from '@/components/RedditScannerAnimation';
import clsx from 'clsx';

interface ProgressState {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  estimatedTime: number;
  error: string | null;
  stage: string | null;
}

interface Step {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed';
  icon: React.ElementType;
}

type ProgressLocationState = {
  sseEndpoint?: string;
  productDescription?: string;
};

// 按照 v0 定义的 4 个步骤
const ANALYSIS_STEPS: Step[] = [
  {
    id: 'community-discovery',
    title: '社区发现',
    description: '寻找相关的 Reddit 社区和子版块',
    status: 'pending',
    icon: Search,
  },
  {
    id: 'content-extraction',
    title: '内容抓取',
    description: '收集帖子、评论和讨论内容',
    status: 'pending',
    icon: Download,
  },
  {
    id: 'nlp-analysis',
    title: 'NLP 分析',
    description: '使用 AI 处理文本以识别模式和情感',
    status: 'pending',
    icon: Brain,
  },
  {
    id: 'insight-generation',
    title: '洞察生成',
    description: '生成商业洞察和建议',
    status: 'pending',
    icon: Lightbulb,
  },
];

const ProgressPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = (location.state as ProgressLocationState | null) ?? null;

  const [state, setState] = useState<ProgressState>({
    status: 'pending',
    progress: 0,
    currentStep: '准备开始分析...',
    estimatedTime: 120, // default estimate
    error: null,
    stage: null,
  });

  const [steps, setSteps] = useState<Step[]>(ANALYSIS_STEPS);
  const [sseClient, setSSEClient] = useState<SSEClient | null>(null);
  const [usePolling, setUsePolling] = useState(false);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [sseEndpoint, setSseEndpoint] = useState<string | null>(locationState?.sseEndpoint ?? null);

  const productDescription = locationState?.productDescription ?? '正在加载产品描述...';

  // 映射进度到步骤
  const updateStepStatus = useCallback((percentage: number) => {
    setSteps((prev) =>
      prev.map((step, index) => {
        const stepThreshold = ((index + 1) / 4) * 100;
        const prevThreshold = (index / 4) * 100;

        if (percentage >= stepThreshold) {
          return { ...step, status: 'completed' as const };
        } else if (percentage > prevThreshold) {
          return { ...step, status: 'in-progress' as const };
        }
        return { ...step, status: 'pending' as const };
      })
    );
  }, []);

  // 初始状态拉取
  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;

    const fetchInitialStatus = async () => {
      try {
        const snapshot = await getTaskStatus(taskId);
        if (cancelled) return;

        const percentage = snapshot.percentage ?? snapshot.progress ?? 0;
        setSseEndpoint((prev) => (prev ?? snapshot.sse_endpoint));
        updateStepStatus(percentage);
        setState((prev) => ({
          ...prev,
          status: snapshot.status,
          progress: percentage,
          currentStep: snapshot.current_step || snapshot.message,
          stage: snapshot.stage ?? null,
          error: snapshot.error ?? null,
        }));

        if (snapshot.status === 'completed') {
          setIsComplete(true);
        }
      } catch (error) {
        console.error('Initial status fetch failed', error);
      }
    };

    fetchInitialStatus();
    return () => { cancelled = true; };
  }, [taskId, updateStepStatus]);

  // 计时器
  useEffect(() => {
    if (state.status !== 'processing' || isComplete) return;
    const timer = setInterval(() => setTimeElapsed(prev => prev + 1), 1000);
    return () => clearInterval(timer);
  }, [state.status, isComplete]);

  // SSE 处理
  const handleSSEEvent = useCallback((event: SSEEvent) => {
    switch (event.event) {
      case 'connected':
        setState(prev => ({ ...prev, status: 'processing', currentStep: '已连接，开始分析...' }));
        break;
      case 'progress': {
        const percentage = event.percentage ?? event.progress;
        setState(prev => ({
          ...prev,
          status: 'processing',
          progress: percentage,
          currentStep: event.current_step || event.message || prev.currentStep,
          estimatedTime: event.estimated_remaining || prev.estimatedTime,
          stage: event.stage ?? prev.stage,
        }));
        updateStepStatus(percentage);
        break;
      }
      case 'completed': {
        setIsComplete(true);
        setState(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
          currentStep: '分析完成！',
        }));
        updateStepStatus(100);
        
        // 自动跳转判断
        const stage = event.stage ?? null;
        if (stage !== 'warmup' && stage !== 'auto_rerun') {
          setTimeout(() => taskId && navigate(ROUTES.REPORT(taskId)), 2000);
        } else {
          setUsePolling(true);
        }
        break;
      }
      case 'error':
        setState(prev => ({ ...prev, status: 'failed', error: 'error_message' in event ? event.error_message : '分析失败' }));
        setUsePolling(true);
        break;
    }
  }, [taskId, navigate, updateStepStatus]);

  const handleStatusChange = useCallback((status: SSEConnectionStatus) => {
    if (status === 'failed') {
      setUsePolling(true);
    }
  }, []);

  // 连接逻辑
  useEffect(() => {
    if (!taskId) return;
    if (isComplete && !usePolling) return;

    if (usePolling) {
      const poll = setInterval(async () => {
        try {
          const task = await getTaskStatus(taskId);
          const pct = task.percentage ?? task.progress ?? 0;
          setState(prev => ({
            ...prev,
            status: task.status === 'completed' ? 'completed' : task.status === 'failed' ? 'failed' : 'processing',
            progress: pct,
            currentStep: task.current_step || task.message || '正在处理...',
            stage: task.stage ?? null,
            error: task.error ?? null,
          }));
          updateStepStatus(pct);

          if (task.status === 'completed' && task.stage !== 'warmup' && task.stage !== 'auto_rerun') {
            clearInterval(poll);
            setIsComplete(true);
            setTimeout(() => navigate(ROUTES.REPORT(taskId)), 2000);
          }
        } catch (e) {
          console.error('Polling error', e);
        }
      }, 2000);
      return () => clearInterval(poll);
    }

    if (sseEndpoint) {
      const client = createTaskProgressSSE(taskId, handleSSEEvent, handleStatusChange, sseEndpoint);
      client.connect();
      setSSEClient(client);
      return () => {
        client.disconnect();
        setSSEClient(null);
      };
    }
    
    // Explicit return for consistent return type
    return undefined;
  }, [taskId, usePolling, sseEndpoint, handleSSEEvent, handleStatusChange, isComplete, navigate, updateStepStatus]);

  const handleLogout = () => {
    logout();
    window.location.reload();
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleCancel = () => {
    if (confirm('确定要取消分析吗？')) {
      sseClient?.disconnect();
      navigate(ROUTES.HOME);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Reddit 商业信号扫描器</h1>
          </div>
          {isAuthenticated() && (
            <button
              onClick={handleLogout}
              className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3"
            >
              退出登录
            </button>
          )}
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 flex flex-col items-center">
        <div className="w-full max-w-4xl mb-8">
          <NavigationBreadcrumb currentStep="analysis" canNavigateBack={false} />
        </div>

        <div className="max-w-4xl w-full space-y-8">
          {/* Header */}
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center space-x-2 mb-4">
              <RedditScannerAnimation isComplete={isComplete} />
            </div>
            <h2 className="text-3xl font-bold text-foreground">
              {isComplete ? "分析完成！" : "正在分析您的产品"}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {isComplete ? "我们已经发现了关于您市场机会的宝贵洞察" : "我们正在扫描 Reddit 社区，为您的产品寻找商业机会"}
            </p>
          </div>

          {/* Product Summary */}
          <div className="rounded-xl border bg-card text-card-foreground shadow-sm border-secondary/20">
            <div className="flex flex-col space-y-1.5 p-6">
              <h3 className="font-semibold leading-none tracking-tight text-lg">正在分析的产品</h3>
            </div>
            <div className="p-6 pt-0">
              <p className="text-muted-foreground line-clamp-3">{productDescription}</p>
            </div>
          </div>

          {/* Progress Overview */}
          <div className="rounded-xl border bg-card text-card-foreground shadow-sm">
            <div className="flex flex-col space-y-1.5 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold leading-none tracking-tight flex items-center space-x-2">
                    <Clock className="w-5 h-5 text-secondary" />
                    <span>分析进度</span>
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isComplete
                      ? "分析已成功完成"
                      : `第 ${steps.findIndex(s => s.status === 'in-progress') + 1} 步，共 4 步 • 剩余 ${formatTime(state.estimatedTime)}`}
                  </p>
                </div>
                <div className={clsx(
                  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ml-4",
                  isComplete 
                    ? "border-transparent bg-primary text-primary-foreground hover:bg-primary/80"
                    : "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80"
                )}>
                  {Math.round(state.progress)}%
                </div>
              </div>
            </div>
            <div className="p-6 pt-0 space-y-6">
              {/* Progress Bar */}
              <div className="h-3 w-full overflow-hidden rounded-full bg-secondary/20">
                <div 
                  className="h-full bg-primary transition-all duration-500 ease-out" 
                  style={{ width: `${state.progress}%` }} 
                />
              </div>

              {/* Step Details */}
              <div className="space-y-4">
                {steps.map((step) => (
                  <div
                    key={step.id}
                    className={clsx(
                      "flex items-center space-x-4 p-4 rounded-lg border transition-all",
                      step.status === "in-progress"
                        ? "border-secondary/50 bg-secondary/5"
                        : step.status === "completed"
                          ? "border-green-200 bg-green-50"
                          : "border-border bg-card"
                    )}
                  >
                    <div className="flex-shrink-0">
                      {step.status === "completed" ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : step.status === "in-progress" ? (
                        <Loader2 className="w-5 h-5 text-secondary animate-spin" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-foreground">{step.title}</h4>
                      <p className="text-sm text-muted-foreground">{step.description}</p>
                    </div>
                    <div className="flex-shrink-0">
                      {step.status === "in-progress" && (
                        <div className="inline-flex items-center rounded-full border border-transparent bg-secondary px-2.5 py-0.5 text-xs font-semibold text-secondary-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 animate-pulse">
                          处理中...
                        </div>
                      )}
                      {step.status === "completed" && (
                        <div className="inline-flex items-center rounded-full border border-transparent px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 bg-green-500 text-white">
                          完成
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Live Stats */}
          {!isComplete && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl border bg-card text-card-foreground shadow-sm">
                <div className="p-4 text-center">
                  <div className="w-8 h-8 bg-secondary/10 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Users className="w-4 h-4 text-secondary" />
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {Math.min(Math.floor(timeElapsed / 10) * 3 + 12, 47)}
                  </div>
                  <p className="text-sm text-muted-foreground">发现的社区</p>
                </div>
              </div>

              <div className="rounded-xl border bg-card text-card-foreground shadow-sm">
                <div className="p-4 text-center">
                  <div className="w-8 h-8 bg-secondary/10 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <MessageSquare className="w-4 h-4 text-secondary" />
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {Math.min(Math.floor(timeElapsed / 5) * 127 + 234, 2847)}
                  </div>
                  <p className="text-sm text-muted-foreground">已分析帖子</p>
                </div>
              </div>

              <div className="rounded-xl border bg-card text-card-foreground shadow-sm">
                <div className="p-4 text-center">
                  <div className="w-8 h-8 bg-secondary/10 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <TrendingUp className="w-4 h-4 text-secondary" />
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {Math.min(Math.floor(timeElapsed / 15) * 8 + 3, 23)}
                  </div>
                  <p className="text-sm text-muted-foreground">生成的洞察</p>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-center space-x-4">
            {!isComplete ? (
              <button
                onClick={handleCancel}
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
              >
                取消分析
              </button>
            ) : (
              <button
                onClick={() => taskId && navigate(ROUTES.REPORT(taskId))}
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-11 rounded-md px-8"
              >
                查看报告
              </button>
            )}
          </div>

          <div className="text-center text-sm text-muted-foreground">
            已用时间：{formatTime(timeElapsed)}
            {!isComplete && ` • 预计完成时间：${formatTime(state.estimatedTime)}`}
          </div>
        </div>
      </main>
    </div>
  );
};

export default ProgressPage;
