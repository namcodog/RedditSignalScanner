/**
 * 等待页面（Progress Page）
 *
 * 基于真实 SSE 链路的成品化等待页。
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Search,
  Download,
  Brain,
  Lightbulb,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import { createTaskProgressSSE } from '@/api/sse.client';
import type { SSEClient } from '@/api/sse.client';
import { getTaskStatus } from '@/api/analyze.api';
import { isAuthenticated, logout } from '@/api/auth.api';
import type { SSEEvent, SSEConnectionStatus } from '@/types';
import { ROUTES } from '@/router/routes';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import RedditScannerAnimation from '@/components/RedditScannerAnimation';
import ProductStatePanel from '@/components/product/ProductStatePanel';
import clsx from 'clsx';

interface ProgressState {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  estimatedTime: number;
  error: string | null;
  stage: string | null;
  blockedReason: string | null;
  nextAction: string | null;
  details: Record<string, unknown> | null;
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

const ANALYSIS_STEPS: Step[] = [
  {
    id: 'community-discovery',
    title: '社区发现',
    description: '找到这次最相关的 Reddit 社区',
    status: 'pending',
    icon: Search,
  },
  {
    id: 'content-extraction',
    title: '内容抓取',
    description: '抓取帖子、评论和讨论原话',
    status: 'pending',
    icon: Download,
  },
  {
    id: 'nlp-analysis',
    title: 'NLP 分析',
    description: '用 AI 识别模式、情绪和重点主题',
    status: 'pending',
    icon: Brain,
  },
  {
    id: 'insight-generation',
    title: '洞察生成',
    description: '生成可判断的结论和建议动作',
    status: 'pending',
    icon: Lightbulb,
  },
];

const STAGE_LABELS: Record<string, string> = {
  pending: '准备阶段',
  warmup: '补量预热',
  auto_rerun: '自动重跑',
  processing: '正式分析',
  community_discovery: '社区发现',
  data_collection: '数据采集',
  content_extraction: '内容抓取',
  nlp_analysis: 'NLP 分析',
  insight_generation: '洞察生成',
  report_generation: '报告生成',
  done: '结果完成',
  success: '结果完成',
  completed: '结果完成',
  failed: '分析失败',
};

const BLOCKED_REASON_LABELS: Record<string, string> = {
  insufficient_samples: '样本还不够，系统正在补量。',
  system_dependency_down: '依赖服务暂时不可用，任务被保护性暂停。',
  budget_or_fuse_blocked: '触发系统保护阈值，任务已暂停。',
  quality_gate_blocked: '结果未过质量门禁，系统先拦住了输出。',
};

const NEXT_ACTION_LABELS: Record<string, string> = {
  auto_rerun_scheduled: '系统已安排自动重跑，无需重复提交。',
  wait_for_warmup: '等系统补够样本后再判断要不要继续追。',
  manual_retry: '建议稍后手动重试一次。',
  manual_intervention: '需要管理员介入，不建议继续盲等。',
  running: '系统已继续向下跑，先看进度变化。',
  none: '当前没有额外动作，先看这页结论。',
};

const normalizeMetaKey = (value: string): string =>
  value.trim().toLowerCase().replace(/[\s-]+/g, '_');

const humanizeMeta = (value: string | null | undefined, labels: Record<string, string>) => {
  if (!value) {
    return '暂时没有额外说明';
  }

  const direct = labels[value];
  if (direct) {
    return direct;
  }

  const normalized = normalizeMetaKey(value);
  const normalizedLabel = labels[normalized];
  if (normalizedLabel) {
    return normalizedLabel;
  }

  return value.replace(/_/g, ' ');
};

const formatRetryTime = (value: unknown) => {
  if (typeof value !== 'string') {
    return '系统尚未给出预计时间';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
};

const buildRemediationSummary = (value: unknown): string | null => {
  if (!Array.isArray(value)) {
    return null;
  }

  const labels = value
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }
      const rawType = String((item as Record<string, unknown>)['type'] ?? '').trim();
      const targets = Number((item as Record<string, unknown>)['targets'] ?? 0);
      if (!rawType) {
        return null;
      }
      const actionLabel =
        rawType === 'backfill_posts'
          ? '补帖子'
          : rawType === 'backfill_comments'
            ? '补评论'
            : rawType.replace(/_/g, ' ');
      return targets > 0 ? `${actionLabel} ${targets} 项` : actionLabel;
    })
    .filter((item): item is string => Boolean(item));

  if (labels.length === 0) {
    return null;
  }

  return labels.slice(0, 2).join(' / ');
};

const ProgressPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = (location.state as ProgressLocationState | null) ?? null;

  const [state, setState] = useState<ProgressState>({
    status: 'pending',
    progress: 0,
    currentStep: '准备开始分析...',
    estimatedTime: 120,
    error: null,
    stage: null,
    blockedReason: null,
    nextAction: null,
    details: null,
  });

  const [steps, setSteps] = useState<Step[]>(ANALYSIS_STEPS);
  const [sseClient, setSSEClient] = useState<SSEClient | null>(null);
  const [usePolling, setUsePolling] = useState(false);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [sseEndpoint, setSseEndpoint] = useState<string | null>(locationState?.sseEndpoint ?? null);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const productDescription = locationState?.productDescription ?? '正在加载产品描述...';
  const reusableProductDescription =
    typeof locationState?.productDescription === 'string' ? locationState.productDescription.trim() : '';

  const navigateBackToInput = useCallback(
    (hint: string) => {
      navigate(ROUTES.HOME, {
        state: {
          prefillProductDescription: reusableProductDescription,
          prefillSource: 'restart-analysis',
          prefillHint: hint,
        },
      });
    },
    [navigate, reusableProductDescription],
  );

  const updateStepStatus = useCallback((percentage: number) => {
    setSteps((prev) =>
      prev.map((step, index) => {
        const stepThreshold = ((index + 1) / 4) * 100;
        const prevThreshold = (index / 4) * 100;

        if (percentage >= stepThreshold) {
          return { ...step, status: 'completed' as const };
        }

        if (percentage > prevThreshold) {
          return { ...step, status: 'in-progress' as const };
        }

        return { ...step, status: 'pending' as const };
      })
    );
  }, []);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    let cancelled = false;

    const fetchInitialStatus = async () => {
      try {
        const snapshot = await getTaskStatus(taskId);
        if (cancelled) {
          return;
        }

        const percentage = snapshot.percentage ?? snapshot.progress ?? 0;
        setSseEndpoint((prev) => prev ?? snapshot.sse_endpoint);
        updateStepStatus(percentage);
        setState((prev) => ({
          ...prev,
          status: snapshot.status,
          progress: percentage,
          currentStep: snapshot.current_step || snapshot.message,
          stage: snapshot.stage ?? null,
          error: snapshot.error ?? null,
          blockedReason: snapshot.blocked_reason ?? null,
          nextAction: snapshot.next_action ?? null,
          details: snapshot.details ?? null,
        }));

        if (snapshot.status === 'completed') {
          setIsComplete(true);
        }
      } catch (error) {
        console.error('Initial status fetch failed', error);
      }
    };

    void fetchInitialStatus();
    return () => {
      cancelled = true;
    };
  }, [taskId, updateStepStatus]);

  useEffect(() => {
    if (state.status !== 'processing' || isComplete) {
      return;
    }

    const timer = setInterval(() => setTimeElapsed((prev) => prev + 1), 1000);
    return () => clearInterval(timer);
  }, [state.status, isComplete]);

  const handleSSEEvent = useCallback((event: SSEEvent) => {
    switch (event.event) {
      case 'connected':
        setState((prev) => ({
          ...prev,
          status: 'processing',
          currentStep: '已连接，开始分析...',
        }));
        break;
      case 'progress': {
        const percentage = event.percentage ?? event.progress;
        setState((prev) => ({
          ...prev,
          status: 'processing',
          progress: percentage,
          currentStep: event.current_step || event.message || prev.currentStep,
          estimatedTime: event.estimated_remaining || prev.estimatedTime,
          stage: event.stage ?? prev.stage,
          blockedReason: event.blocked_reason ?? prev.blockedReason,
          nextAction: event.next_action ?? prev.nextAction,
          details: event.details ?? prev.details,
        }));
        updateStepStatus(percentage);
        break;
      }
      case 'completed': {
        const stage = event.stage ?? null;
        setIsComplete(true);
        setState((prev) => ({
          ...prev,
          status: 'completed',
          progress: 100,
          currentStep: '分析完成！',
          stage,
          blockedReason: event.blocked_reason ?? prev.blockedReason,
          nextAction: event.next_action ?? prev.nextAction,
          details: event.details ?? prev.details,
        }));
        updateStepStatus(100);

        if (stage !== 'warmup' && stage !== 'auto_rerun') {
          setTimeout(() => {
            if (taskId) {
              navigate(ROUTES.REPORT(taskId));
            }
          }, 2000);
        } else {
          setUsePolling(true);
        }
        break;
      }
      case 'error':
        setState((prev) => ({
          ...prev,
          status: 'failed',
          error: event.error_message,
        }));
        setUsePolling(true);
        break;
      default:
        break;
    }
  }, [navigate, taskId, updateStepStatus]);

  const handleStatusChange = useCallback((status: SSEConnectionStatus) => {
    if (status === 'failed') {
      setUsePolling(true);
    }
  }, []);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    if (isComplete && !usePolling) {
      return;
    }

    if (usePolling) {
      const poll = setInterval(async () => {
        try {
          const task = await getTaskStatus(taskId);
          const percentage = task.percentage ?? task.progress ?? 0;
          setState((prev) => ({
            ...prev,
            status: task.status === 'completed' ? 'completed' : task.status === 'failed' ? 'failed' : 'processing',
            progress: percentage,
            currentStep: task.current_step || task.message || '正在处理...',
            stage: task.stage ?? null,
            error: task.error ?? null,
            blockedReason: task.blocked_reason ?? null,
            nextAction: task.next_action ?? null,
            details: task.details ?? null,
          }));
          updateStepStatus(percentage);

          if (task.status === 'completed' && task.stage !== 'warmup' && task.stage !== 'auto_rerun') {
            clearInterval(poll);
            setIsComplete(true);
            setTimeout(() => navigate(ROUTES.REPORT(taskId)), 2000);
          }
        } catch (error) {
          console.error('Polling error', error);
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

    return undefined;
  }, [taskId, usePolling, isComplete, sseEndpoint, handleSSEEvent, handleStatusChange, navigate, updateStepStatus]);

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
    setShowCancelConfirm(true);
  };

  const confirmCancel = () => {
    sseClient?.disconnect();
    navigateBackToInput('已带回这次分析方向。你可以继续补描述，或者先缩小范围再重跑。');
  };

  const activeStepIndex = steps.findIndex((step) => step.status === 'in-progress');
  const currentStepNumber = activeStepIndex >= 0 ? activeStepIndex + 1 : isComplete ? 4 : 1;
  const isHoldState = state.stage === 'warmup' || state.stage === 'auto_rerun';
  const progressHeading = isHoldState
    ? '这次结果还在整理中'
    : isComplete
      ? '分析完成！'
      : '正在分析您的产品';
  const progressDescription = isHoldState
    ? '系统已找到方向，正在补量把结论做稳。'
    : isComplete
      ? '这轮已经产出可继续判断的结果。'
      : '系统正在抓取并分析真实讨论。';
  const currentStepCopy = state.currentStep || '正在处理...';
  const stageLabel = humanizeMeta(state.stage, STAGE_LABELS);
  const blockedReasonLabel = humanizeMeta(state.blockedReason, BLOCKED_REASON_LABELS);
  const nextActionLabel = humanizeMeta(state.nextAction, NEXT_ACTION_LABELS);
  const nextRetryLabel = formatRetryTime(state.details?.['next_retry_at']);
  const remediationSummary = buildRemediationSummary(state.details?.['remediation_actions']);
  const progressFacts = useMemo(() => {
    const facts = [
      {
        label: '当前阶段',
        value: stageLabel,
        help: '真实阶段，不是演示进度。',
      },
      {
        label: '系统正在做什么',
        value: currentStepCopy,
        help: '这里在变化，就说明还在跑。',
      },
      {
        label: '下一步',
        value: nextActionLabel,
        help: remediationSummary ?? (nextRetryLabel !== '系统尚未给出预计时间' ? `预计重试：${nextRetryLabel}` : '看当前提示即可。'),
      },
    ];

    if (state.blockedReason) {
      facts.splice(1, 0, {
        label: '卡点原因',
        value: blockedReasonLabel,
        help: remediationSummary ?? '系统会先说明原因，再决定是否继续补量。',
      });
    }

    return facts.slice(0, 4);
  }, [blockedReasonLabel, currentStepCopy, nextActionLabel, nextRetryLabel, remediationSummary, stageLabel, state.blockedReason]);

  return (
    <div className="min-h-screen bg-background">
      <header className="surface-header border-b border-border/70">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="surface-brand-mark flex h-11 w-11 items-center justify-center rounded-2xl text-primary-foreground">
              <Search className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="surface-section-kicker">Signal Run</div>
              <h1 className="truncate text-lg font-semibold text-foreground">Reddit 商业信号扫描器</h1>
            </div>
          </div>
          {isAuthenticated() ? (
            <button
              onClick={handleLogout}
              className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
            >
              退出登录
            </button>
          ) : null}
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col items-center px-4 py-8 md:py-10">
        <div className="mb-8 w-full max-w-5xl">
          <NavigationBreadcrumb currentStep="analysis" canNavigateBack={false} />
        </div>

        <div className="w-full max-w-5xl space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          <section className="surface-panel relative overflow-hidden rounded-[32px] p-6 md:p-7">
            <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
            <div className="pointer-events-none absolute bottom-0 left-0 h-32 w-32 rounded-full bg-secondary/10 blur-3xl" />
            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-4">
                <div className="surface-section-kicker">Analysis In Motion</div>
                <div className="surface-rule max-w-40" />
                <div className="flex flex-wrap items-center gap-3">
                  <span className="surface-chip inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold">
                    真实任务状态
                  </span>
                  <span className="surface-chip inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold">
                    当前步骤：{currentStepCopy}
                  </span>
                </div>
                <div className="space-y-3">
                  <h2 className="text-3xl font-semibold leading-tight text-foreground md:text-[2.3rem]">
                    {progressHeading}
                  </h2>
                  <p className="max-w-3xl text-sm leading-7 text-muted-foreground md:text-base">
                    {progressDescription}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-center">
                <div className="surface-panel-muted rounded-[28px] px-6 py-5 text-center">
                  <div className="flex items-center justify-center space-x-2">
                    <RedditScannerAnimation isComplete={isComplete} />
                  </div>
                  <div className="surface-number mt-4 text-3xl font-semibold text-foreground">
                    {Math.round(state.progress)} / 100
                  </div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {isComplete ? '这轮分析已经可以进入结果页' : `第 ${currentStepNumber} 步，共 4 步`}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {state.error ? (
            <ProductStatePanel
              tone="error"
              title="这次分析暂时没顺利跑完"
              description={state.error}
              nextStep="先回首页重试；如果连续失败，再去控制面确认今天机器和队列是不是稳定。"
              actions={[
                {
                  label: '回输入页重跑',
                  onClick: () =>
                    navigateBackToInput('已带回这次分析方向。你可以直接改描述后重跑，不用从零开始。'),
                  tone: 'primary',
                },
              ]}
            />
          ) : null}

          {isHoldState ? (
            <section className="surface-panel-muted rounded-[28px] p-5 md:p-6">
              <div className="surface-section-kicker">为什么还没直接跳报告</div>
              <div className="mt-3 text-base font-semibold text-foreground">
                这次结果还在补量确认，系统先把原因和下一步告诉你。
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-background/70 px-4 py-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">阶段</div>
                  <div className="mt-2 text-sm leading-6 text-foreground">{stageLabel}</div>
                </div>
                <div className="rounded-2xl bg-background/70 px-4 py-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">卡点原因</div>
                  <div className="mt-2 text-sm leading-6 text-foreground">{blockedReasonLabel}</div>
                </div>
                <div className="rounded-2xl bg-background/70 px-4 py-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">下一步</div>
                  <div className="mt-2 text-sm leading-6 text-foreground">{nextActionLabel}</div>
                </div>
                <div className="rounded-2xl bg-background/70 px-4 py-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">预计重试</div>
                  <div className="mt-2 text-sm leading-6 text-foreground">{nextRetryLabel}</div>
                </div>
              </div>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => taskId && navigate(ROUTES.REPORT(taskId))}
                  className="surface-action-primary inline-flex h-11 items-center justify-center rounded-xl px-5 text-sm font-medium transition-colors"
                >
                  先看当前结果
                </button>
                <button
                  type="button"
                  onClick={() =>
                    navigateBackToInput('已带回这次分析方向。你可以马上改描述重跑，或等系统自动补量后再看。')
                  }
                  className="surface-action-secondary inline-flex h-11 items-center justify-center rounded-xl px-5 text-sm font-medium transition-colors"
                >
                  回输入页重跑
                </button>
              </div>
            </section>
          ) : null}

          <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
            <div className="surface-panel-muted rounded-[28px] p-6">
              <h3 className="text-lg font-semibold text-foreground">正在分析的产品</h3>
              <p className="mt-3 line-clamp-4 text-sm leading-7 text-muted-foreground">{productDescription}</p>
            </div>
            <div className="surface-panel-muted rounded-[28px] p-6">
              <div className="surface-section-kicker">运行提示</div>
              <div className="mt-3 space-y-3">
                <p className="text-sm leading-6 text-muted-foreground">
                  这页只展示真实任务状态。阶段在变，就说明还在正常往下跑。
                </p>
                <p className="text-sm leading-6 text-muted-foreground">
                  中途返回不丢描述，系统会自动带回输入页。
                </p>
                <div className="rounded-2xl bg-background/70 px-4 py-3">
                  <div className="text-sm font-semibold text-foreground">当前步骤</div>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{currentStepCopy}</p>
                </div>
              </div>
            </div>
          </section>

          <section className="surface-panel rounded-[32px] p-6 md:p-7">
            <div className="flex flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-end md:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-foreground">分析进度</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {isComplete
                    ? '分析已成功完成'
                    : `第 ${currentStepNumber} 步，共 4 步 • 剩余 ${formatTime(state.estimatedTime)}`}
                </p>
              </div>
              <div className={clsx(
                'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold',
                isComplete ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
              )}>
                {Math.round(state.progress)}%
              </div>
            </div>

            <div className="mt-6 space-y-6">
              <div className="h-3 w-full overflow-hidden rounded-full bg-secondary/12">
                <div
                  className="h-full bg-primary transition-all duration-500 ease-out"
                  style={{ width: `${state.progress}%` }}
                />
              </div>

              <div className="space-y-4">
                {steps.map((step) => {
                  const StepIcon = step.icon;
                  return (
                    <div
                      key={step.id}
                      className={clsx(
                        'rounded-[24px] border p-4 transition-all',
                        step.status === 'in-progress'
                          ? 'border-secondary/25 bg-secondary/5 shadow-editorial'
                          : step.status === 'completed'
                            ? 'border-emerald-200 bg-emerald-50/90'
                            : 'border-border bg-background/70'
                      )}
                    >
                      <div className="flex items-start gap-4">
                        <div className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-background/80 text-primary">
                          {step.status === 'completed' ? (
                            <CheckCircle className="h-5 w-5 text-emerald-600" />
                          ) : step.status === 'in-progress' ? (
                            <Loader2 className="h-5 w-5 animate-spin text-secondary" />
                          ) : (
                            <StepIcon className="h-5 w-5 text-muted-foreground" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h4 className="font-medium text-foreground">{step.title}</h4>
                            {step.status === 'in-progress' ? (
                              <div className="inline-flex items-center rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-secondary-foreground">
                                处理中...
                              </div>
                            ) : null}
                            {step.status === 'completed' ? (
                              <div className="inline-flex items-center rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white">
                                完成
                              </div>
                            ) : null}
                          </div>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">{step.description}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {progressFacts.map((fact) => (
              <div key={`${fact.label}-${fact.value}`} className="surface-panel-muted rounded-[24px] p-5">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{fact.label}</div>
                <div className="mt-3 text-lg font-semibold leading-snug text-foreground">{fact.value}</div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{fact.help}</p>
              </div>
            ))}
          </section>

          <section className="space-y-4">
            <div className="flex items-center justify-center gap-4">
              {!isComplete ? (
                <button
                  onClick={handleCancel}
                  className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
                >
                  取消分析
                </button>
              ) : (
                <button
                  onClick={() => taskId && navigate(ROUTES.REPORT(taskId))}
                  className="surface-action-primary inline-flex h-11 items-center justify-center rounded-xl px-8 text-sm font-medium transition-colors"
                >
                  查看报告
                </button>
              )}
            </div>

            {showCancelConfirm && !isComplete ? (
              <ProductStatePanel
                tone="degraded"
                compact
                title="确定要取消这次分析吗？"
                description="现在退出会中断这次分析，你可以回输入页继续改后再重跑。"
                actions={[
                  { label: '继续等待', onClick: () => setShowCancelConfirm(false) },
                  { label: '回输入页', onClick: confirmCancel, tone: 'primary' },
                ]}
              />
            ) : null}

            <div className="text-center text-sm text-muted-foreground">
              已用时间：{formatTime(timeElapsed)}
              {!isComplete && ` • 预计完成时间：${formatTime(state.estimatedTime)}`}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default ProgressPage;
