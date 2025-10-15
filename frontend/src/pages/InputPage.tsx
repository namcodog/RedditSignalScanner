import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import clsx from 'clsx';
import {
  Search,
  Lightbulb,
  Target,
  Zap,
  Clock,
} from 'lucide-react';

import { createAnalyzeTask } from '@/api/analyze.api';
import { register, isAuthenticated } from '@/api/auth.api';
import { ROUTES } from '@/router';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import AuthDialog from '@/components/AuthDialog';

const MIN_CHARACTERS = 10;
const MAX_CHARACTERS = 2000;

const formSchema = z
  .object({
    productDescription: z
      .string()
      .max(MAX_CHARACTERS, `最多支持 ${MAX_CHARACTERS} 个字符`),
  })
  .refine(
    (values) => values.productDescription.trim().length >= MIN_CHARACTERS,
    {
      message: `至少需要 ${MIN_CHARACTERS} 个字符`,
      path: ['productDescription'],
    }
  );

type InputFormValues = z.infer<typeof formSchema>;

const SAMPLE_PROMPTS: string[] = [
  '一款帮助忙碌专业人士进行餐食准备的移动应用，根据饮食偏好、烹饪时间限制和当地杂货店供应情况生成个性化的每周餐食计划。包括自动购物清单、分步烹饪指导以及与配送服务集成。',
  '一个面向远程团队的项目管理 SaaS，通过 Slack 集成自动同步项目动态，并提供 AI 生成的每周状态报告，帮助团队在不加班的情况下维持透明度与执行力。',
  '一个专注中小型电商的结账优化工具，实时分析购物车流失原因，提供一键化 AB 测试和支付方式推荐，目标是在 30 天内提升转化率 20%。',
];

const PROCESS_STEPS = [
  {
    title: '步骤 1：分析',
    description: '我们扫描相关 Reddit 社区，寻找关于您市场的第一手讨论。',
    icon: Clock,
  },
  {
    title: '步骤 2：处理',
    description: 'AI 识别痛点、竞品提及以及信号强度，甄别真实需求。',
    icon: Target,
  },
  {
    title: '步骤 3：洞察',
    description: '生成包含机会清单、用户声音与行动建议的完整报告。',
    icon: Lightbulb,
  },
];

const InputPage: React.FC = () => {
  const navigate = useNavigate();
  const [apiError, setApiError] = useState<string | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isAuthDialogOpen, setIsAuthDialogOpen] = useState(false);
  const [authDialogTab, setAuthDialogTab] = useState<'login' | 'register'>('login');

  const {
    register: registerForm,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting, isValid },
  } = useForm<InputFormValues>({
    resolver: zodResolver(formSchema),
    mode: 'onChange',
    defaultValues: {
      productDescription: '',
    },
  });

  // 自动认证：如果没有 Token，自动注册临时用户
  useEffect(() => {
    const ensureAuthenticated = async () => {
      if (isAuthenticated()) {
        console.log('[Auth] User already authenticated');
        return;
      }

      setIsAuthenticating(true);
      try {
        // 生成临时用户邮箱（使用 example.com 域名，符合 RFC 标准）
        const tempEmail = `temp-user-${Date.now()}@example.com`;
        const tempPassword = `TempPass${Date.now()}!`;

        console.log('[Auth] Auto-registering temporary user:', tempEmail);

        await register({
          email: tempEmail,
          password: tempPassword,
        });

        console.log('[Auth] Temporary user registered successfully');
      } catch (error) {
        console.error('[Auth] Auto-registration failed:', error);
        setApiError('自动认证失败，请刷新页面重试。');
      } finally {
        setIsAuthenticating(false);
      }
    };

    ensureAuthenticated();
  }, []);

  const productDescription = watch('productDescription');
  const trimmedLength = productDescription.trim().length;

  const remainingForMin = Math.max(MIN_CHARACTERS - trimmedLength, 0);
  const minHint = remainingForMin === 0
    ? '已满足最低字数要求'
    : `还需要至少 ${remainingForMin} 个字`;

  const characterBadge = useMemo(() => {
    if (trimmedLength === 0) {
      return '0 字';
    }
    if (trimmedLength >= MAX_CHARACTERS) {
      return `${trimmedLength}/${MAX_CHARACTERS}`;
    }
    return `${trimmedLength} 字`;
  }, [trimmedLength]);

  const onSubmit = handleSubmit(async (values) => {
    const description = values.productDescription.trim();
    setApiError(null);

    try {
      const response = await createAnalyzeTask({
        product_description: description,
      });
      navigate(ROUTES.PROGRESS(response.task_id), {
        state: {
          estimatedCompletion: response.estimated_completion,
          createdAt: response.created_at,
        },
      });
    } catch (error) {
      setApiError('任务创建失败，请稍后重试或联系支持团队。');
    }
  });

  return (
    <div className="app-shell">
      <header className="border-b border-border bg-card">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
              <Search className="h-5 w-5" aria-hidden />
            </div>
            <h1 className="text-lg font-semibold text-foreground">
              Reddit 商业信号扫描器
            </h1>
          </div>
          <div className="hidden gap-3 sm:flex">
            <button
              type="button"
              aria-haspopup="dialog"
              onClick={() => {
                setAuthDialogTab('login');
                setIsAuthDialogOpen(true);
              }}
              className="inline-flex h-9 items-center justify-center rounded-md border border-border px-4 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              登录
            </button>
            <button
              type="button"
              aria-haspopup="dialog"
              onClick={() => {
                setAuthDialogTab('register');
                setIsAuthDialogOpen(true);
              }}
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              注册
            </button>
          </div>
        </div>
      </header>

      <main className="container flex-1 px-4 py-10">
        {/* Navigation Breadcrumb */}
        <NavigationBreadcrumb currentStep="input" />

        <section className="mx-auto max-w-4xl space-y-10">
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-secondary/20 text-secondary">
              <Lightbulb className="h-6 w-6" aria-hidden />
            </div>
            <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
              描述您的产品想法
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-base text-muted-foreground sm:text-lg">
              详细告诉我们您的产品或服务。描述越具体，我们提供的机会、痛点和竞品洞察就越精准。
            </p>
          </div>

          <section
            aria-labelledby="product-input-title"
            className="rounded-xl border-2 border-dashed border-border bg-card text-card-foreground shadow-sm transition-colors hover:border-secondary/50"
          >
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-6 py-5">
              <div>
                <div className="flex items-center gap-2 text-lg font-semibold" id="product-input-title">
                  <Target className="h-5 w-5 text-secondary" aria-hidden />
                  产品描述
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  包括目标受众、核心功能以及您要解决的关键问题。
                </p>
              </div>
              <span
                className={clsx(
                  'inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors',
                  trimmedLength > MAX_CHARACTERS
                    ? 'border-destructive/50 bg-destructive/10 text-destructive'
                    : 'border-transparent bg-secondary text-secondary-foreground'
                )}
                aria-live="polite"
              >
                {characterBadge}
              </span>
            </div>

            <div className="px-6 py-6">
              <form className="space-y-6" noValidate onSubmit={onSubmit}>
                <div className="space-y-2">
                  <label className="sr-only" htmlFor="productDescription">
                    产品描述
                  </label>
                  <textarea
                    id="productDescription"
                    {...registerForm('productDescription')}
                    className={clsx(
                      'w-full min-h-[10rem] resize-none rounded-lg border bg-input p-4 text-base leading-relaxed text-foreground transition focus:outline-none focus:ring-2 focus:ring-ring',
                      errors.productDescription
                        ? 'border-destructive focus:ring-destructive/60'
                        : 'border-border'
                    )}
                    placeholder="示例：一个帮助忙碌专业人士进行餐食准备的移动应用，根据饮食偏好、烹饪时间限制和当地杂货店供应情况生成个性化的每周餐食计划……"
                    maxLength={MAX_CHARACTERS + 100}
                  />
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                    <span>{minHint}</span>
                    <span>建议 10-500 字</span>
                  </div>
                  {errors.productDescription !== undefined ? (
                    <p className="text-sm text-destructive">
                      {errors.productDescription.message}
                    </p>
                  ) : null}
                </div>

                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    onSubmit(e);
                  }}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:bg-primary/60"
                  data-testid="submit-button"
                  disabled={isAuthenticating || isSubmitting || !isValid || trimmedLength === 0}
                >
                  <Zap className="h-4 w-4" aria-hidden />
                  {isAuthenticating ? '正在初始化...' : isSubmitting ? '创建任务中...' : '开始 5 分钟分析'}
                </button>

                {apiError !== null ? (
                  <div
                    role="alert"
                    className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
                  >
                    {apiError}
                  </div>
                ) : null}
              </form>
            </div>
          </section>

          <section aria-labelledby="sample-prompts" className="space-y-4">
            <div className="text-center">
              <h3 id="sample-prompts" className="text-lg font-semibold text-foreground">
                需要灵感？试试这些示例：
              </h3>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {SAMPLE_PROMPTS.map((prompt, index) => (
                <button
                  key={prompt}
                  type="button"
                  className={clsx(
                    'flex h-full flex-col justify-between rounded-xl border border-border bg-card p-6 text-left text-sm text-muted-foreground shadow-sm transition hover:-translate-y-0.5 hover:border-secondary/60 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    productDescription === prompt ? 'border-secondary shadow-md' : null
                  )}
                  onClick={() => {
                    setValue('productDescription', prompt, {
                      shouldDirty: true,
                      shouldTouch: true,
                      shouldValidate: true,
                    });
                  }}
                >
                  <span className="mb-4 inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-secondary">
                    示例 {index + 1}
                  </span>
                  <p className="leading-relaxed">{prompt}</p>
                </button>
              ))}
            </div>
          </section>

          <section aria-labelledby="next-steps" className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <h3 id="next-steps" className="mb-6 text-center text-lg font-semibold text-foreground">
              接下来会发生什么？
            </h3>
            <div className="grid gap-6 md:grid-cols-3">
              {PROCESS_STEPS.map(({ title, description, icon: Icon }) => (
                <div
                  key={title}
                  className="text-center"
                >
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-secondary/15 text-secondary">
                    <Icon className="h-6 w-6" aria-hidden />
                  </div>
                  <h4 className="text-base font-semibold text-foreground">{title}</h4>
                  <p className="mt-2 text-sm text-muted-foreground">{description}</p>
                </div>
              ))}
            </div>
          </section>
        </section>
      </main>

      {/* 认证对话框 */}
      <AuthDialog
        isOpen={isAuthDialogOpen}
        onClose={() => setIsAuthDialogOpen(false)}
        defaultTab={authDialogTab}
      />
    </div>
  );
};

export default InputPage;
