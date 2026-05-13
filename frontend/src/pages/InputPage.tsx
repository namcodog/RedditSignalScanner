import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
import { getInputGuidance } from '@/api/guidance.api';
import { isAuthenticated, logout } from '@/api/auth.api';
import { ROUTES } from '@/router/routes';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import AuthDialog from '@/components/AuthDialog';

const MIN_CHARACTERS = 10;
const MAX_CHARACTERS = 500; // Updated to match v0

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

type SamplePrompt = {
  title: string;
  description: string;
  tags?: string[];
  topicProfileId?: string;
  standardReportSlug?: string;
};

type InputPrefillState = {
  prefillProductDescription?: string;
  prefillHint?: string;
  prefillSource?: 'report' | 'restart-analysis' | 'hotpost-deepdive' | 'standard-report';
  prefillStandardTitle?: string;
  prefillPromptSuggestion?: string;
};

const FALLBACK_PROMPTS: SamplePrompt[] = [
  {
    title: '跨境电商/PayPal',
    description: '帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。',
    tags: ['跨境电商', '支付'],
    topicProfileId: 'cross_border_payment_v1',
    standardReportSlug: 'cross-border-paypal',
  },
  {
    title: '跨境电商/现金流',
    description: '跨境电商卖家多平台回款管理工具，自动预测现金流与结算风险，覆盖 Amazon/Etsy/Shopify。',
    tags: ['跨境电商'],
    topicProfileId: 'cross_border_payment_v1',
    standardReportSlug: 'cross-border-cashflow',
  },
  {
    title: '跨境电商/回款费率',
    description: '跨境电商卖家多平台回款与手续费管理工具，覆盖 Amazon/Etsy/Shopify/TikTok Shop，解决结算周期长、费率不透明、资金分散的问题。',
    tags: ['跨境电商', '支付'],
    topicProfileId: 'cross_border_payment_v1',
    standardReportSlug: 'cross-border-fee-rate',
  },
  {
    title: 'SaaS协作',
    description: '远程团队项目管理与协作工具，解决跨时区沟通、任务拆解与进度跟踪问题，关注 Notion/Asana/Trello 的使用痛点与替代机会。',
    tags: ['SaaS'],
    topicProfileId: 'saas_collaboration_v1',
    standardReportSlug: 'saas-collaboration',
  },
  {
    title: '家居',
    description: '面向北美租房人群的家居收纳与清洁工具推荐/比价助手，解决空间小、产品选择多、踩雷的问题。',
    tags: ['家居'],
    topicProfileId: 'vacuum_cleaner_v1',
    standardReportSlug: 'home-cleaning',
  },
  {
    title: '户外',
    description: '我想挖 EDC（everyday carry）里 keychain / pocket organizer 方向的真实需求，重点看用户如何整理钥匙、门禁卡、小刀、手电、耳机，哪些场景会乱、会硌、会丢、不好拿，判断是否适合做小配件或收纳产品。',
    tags: ['户外'],
    topicProfileId: 'edc_everyday_carry_v1',
    standardReportSlug: 'edc-pocket-organizer',
  },
];

const STANDARD_REPORT_SLUGS: Record<string, string> = {
  '跨境电商/PayPal': 'cross-border-paypal',
  '跨境电商/现金流': 'cross-border-cashflow',
  '跨境电商/回款费率': 'cross-border-fee-rate',
  SaaS协作: 'saas-collaboration',
  家居: 'home-cleaning',
  户外: 'edc-pocket-organizer',
};

const InputPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [apiError, setApiError] = useState<string | null>(null);
  const [isAuthDialogOpen, setIsAuthDialogOpen] = useState(false);
  const [authDialogTab, setAuthDialogTab] = useState<'login' | 'register'>('login');
  const [samplePrompts, setSamplePrompts] = useState<SamplePrompt[]>(FALLBACK_PROMPTS);
  const [selectedTopicProfileId, setSelectedTopicProfileId] = useState<string | undefined>(undefined);
  const [selectedPromptSnapshot, setSelectedPromptSnapshot] = useState<string>('');
  const hasAppliedPrefill = useRef(false);

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

  const productDescription = watch('productDescription');
  const trimmedLength = productDescription.trim().length;
  const locationState = (location.state as InputPrefillState | null) ?? null;
  const prefillDescription = locationState?.prefillProductDescription?.trim() ?? '';
  const prefillHint = locationState?.prefillHint?.trim() ?? '';
  const prefillSource = locationState?.prefillSource ?? null;
  const prefillStandardTitle = locationState?.prefillStandardTitle?.trim() ?? '';
  const prefillPromptSuggestion = locationState?.prefillPromptSuggestion?.trim() ?? '';
  const shouldShowPrefillBanner = Boolean(prefillDescription) || prefillSource === 'standard-report';
  const prefillTitle =
    prefillSource === 'standard-report'
      ? '刚看过这份标准样板'
      : prefillSource === 'hotpost-deepdive'
      ? '已带回这次热点方向'
      : prefillSource === 'restart-analysis'
        ? '已带回这次待优化方向'
        : '已带回这次分析方向';
  const prefillFallbackHint =
    prefillSource === 'standard-report'
      ? '输入框不会自动沿用标准题。你直接按自己的真实问题描述写就行。'
      : prefillSource === 'hotpost-deepdive'
      ? '这波信号已带回。补成完整产品描述后，直接继续深挖。'
      : '不用从零重写，直接在这份描述上改后重跑。';

  const characterBadge = useMemo(() => {
    return `${trimmedLength} 字`;
  }, [trimmedLength]);

  useEffect(() => {
    let active = true;

    const loadGuidance = async () => {
      try {
        const guidance = await getInputGuidance();
        if (!active) return;
        const examples = (guidance.examples ?? [])
          .map((example) => {
            const normalizedProfileId = example.topic_profile_id?.trim() || '';
            return {
              title: example.title || '示例',
              description: example.prompt,
              tags: example.tags ?? [],
              ...(normalizedProfileId ? { topicProfileId: normalizedProfileId } : {}),
              ...(STANDARD_REPORT_SLUGS[example.title || '']
                ? { standardReportSlug: STANDARD_REPORT_SLUGS[example.title || ''] }
                : {}),
            };
          })
          .filter((example) => example.description && example.description.trim().length > 0);
        if (examples.length > 0) {
          setSamplePrompts(examples.slice(0, 6));
        }
      } catch {
        // 保留 fallback 示例，避免接口失败影响输入页
      }
    };

    void loadGuidance();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (hasAppliedPrefill.current || !prefillDescription) {
      return;
    }

    setValue('productDescription', prefillDescription, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: true,
    });
    setSelectedTopicProfileId(undefined);
    setSelectedPromptSnapshot('');
    hasAppliedPrefill.current = true;
  }, [prefillDescription, setValue]);

  useEffect(() => {
    if (!selectedTopicProfileId || !selectedPromptSnapshot) {
      return;
    }
    if (productDescription.trim() !== selectedPromptSnapshot.trim()) {
      setSelectedTopicProfileId(undefined);
      setSelectedPromptSnapshot('');
    }
  }, [productDescription, selectedTopicProfileId, selectedPromptSnapshot]);

  const onSubmit = handleSubmit(async (values) => {
    const description = values.productDescription.trim();
    setApiError(null);

    if (!isAuthenticated()) {
      setApiError('请先登录或注册后再提交分析任务');
      setAuthDialogTab('register');
      setIsAuthDialogOpen(true);
      return;
    }

    try {
      const payload = {
        product_description: description,
        ...(selectedTopicProfileId ? { topic_profile_id: selectedTopicProfileId } : {}),
      };
      const response = await createAnalyzeTask(payload);
      navigate(ROUTES.PROGRESS(response.task_id), {
        state: {
          estimatedCompletion: response.estimated_completion,
          createdAt: response.created_at,
          sseEndpoint: response.sse_endpoint,
          productDescription: description,
        },
      });
    } catch (error) {
      setApiError('任务创建失败，请稍后重试或联系支持团队。');
    }
  });

  const handleLogout = () => {
    logout();
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="surface-header border-b border-border/70">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="surface-brand-mark flex h-11 w-11 items-center justify-center rounded-2xl text-primary-foreground">
              <Search className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="surface-section-kicker">Signal Intake</div>
              <h1 className="truncate text-lg font-semibold text-foreground">Reddit 商业信号扫描器</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(ROUTES.HOTPOST)}
              className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
            >
              去爆帖速递
            </button>
            {isAuthenticated() ? (
              <>
                <span className="hidden text-sm text-muted-foreground md:inline">欢迎回来</span>
                <button
                  onClick={handleLogout}
                  className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
                >
                  退出登录
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => {
                    setAuthDialogTab('login');
                    setIsAuthDialogOpen(true);
                  }}
                  className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
                >
                  登录
                </button>
                <button
                  onClick={() => {
                    setAuthDialogTab('register');
                    setIsAuthDialogOpen(true);
                  }}
                  className="surface-action-primary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
                >
                  注册
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-8 md:py-10">
        <NavigationBreadcrumb currentStep="input" />

        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
          {shouldShowPrefillBanner ? (
            <div className="surface-panel-muted rounded-[24px] px-5 py-4">
              <div className="surface-section-kicker">方向带回</div>
              <div className="mt-2 text-base font-semibold text-foreground">{prefillTitle}</div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {prefillHint || prefillFallbackHint}
              </p>
              {prefillSource === 'standard-report' && prefillStandardTitle ? (
                <div className="mt-3 space-y-3">
                  <div className="inline-flex items-center rounded-full border border-primary/15 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary">
                    刚看的是：{prefillStandardTitle}
                  </div>
                  {prefillPromptSuggestion ? (
                    <div className="rounded-2xl border border-border/70 bg-background/72 px-4 py-3 text-sm leading-6 text-muted-foreground">
                      问题描述参考：{prefillPromptSuggestion}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          <section className="surface-panel relative overflow-hidden rounded-[32px] p-6 md:p-8">
            <div className="pointer-events-none absolute right-0 top-0 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
            <div className="pointer-events-none absolute bottom-0 left-0 h-32 w-32 rounded-full bg-secondary/10 blur-3xl" />
            <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="space-y-5">
                <div className="space-y-3">
                  <div className="surface-section-kicker">第一步</div>
                  <div className="surface-rule max-w-40" />
                  <div className="space-y-3">
                    <h2 className="max-w-3xl text-3xl font-semibold leading-tight text-foreground md:text-[2.4rem]">
                      描述您的产品想法
                    </h2>
                    <p className="max-w-2xl text-sm leading-7 text-muted-foreground md:text-base">
                      不用写 PRD。说清谁在用、卡在哪、你怎么帮，就能拿到第一板判断。
                    </p>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="surface-panel-muted rounded-2xl p-4">
                    <Lightbulb className="h-5 w-5 text-primary" />
                    <div className="mt-3 text-sm font-semibold text-foreground">1 谁在用</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">用户是谁，在哪个场景会想到它。</p>
                  </div>
                  <div className="surface-panel-muted rounded-2xl p-4">
                    <Target className="h-5 w-5 text-primary" />
                    <div className="mt-3 text-sm font-semibold text-foreground">2 卡在哪</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">最烦的痛点是什么，现有替代哪里不顺。</p>
                  </div>
                  <div className="surface-panel-muted rounded-2xl p-4">
                    <Clock className="h-5 w-5 text-primary" />
                    <div className="mt-3 text-sm font-semibold text-foreground">3 你怎么帮</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">你准备帮他省什么时间、成本，或少什么坑。</p>
                  </div>
                </div>
              </div>
              <aside className="surface-panel-muted rounded-[28px] p-5 md:p-6">
                <div className="surface-section-kicker">这次会发生什么</div>
                <div className="mt-3 space-y-4">
                  <div>
                    <div className="text-sm font-semibold text-foreground">直接跑真实讨论</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">提交后直接抓真实讨论，不会拿示例冒充。</p>
                  </div>
                  <div className="surface-rule" />
                  <div>
                    <div className="text-sm font-semibold text-foreground">先给是否继续追的第一板</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">这轮先回答值不值得追；要快扫可先去爆帖速递。</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate(ROUTES.HOTPOST)}
                    className="surface-action-secondary inline-flex h-10 w-full items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
                  >
                    先看爆帖速递
                  </button>
                </div>
              </aside>
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-3">
            <div className="surface-panel-muted rounded-2xl p-4">
              <div className="text-sm font-semibold text-foreground">可能直接出完整结论</div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">样本够就直接给可拍板的 A 级结果。</p>
            </div>
            <div className="surface-panel-muted rounded-2xl p-4">
              <div className="text-sm font-semibold text-foreground">也可能先给方向判断</div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">样本偏轻就先给方向判断，不会硬凑结论。</p>
            </div>
            <div className="surface-panel-muted rounded-2xl p-4">
              <div className="text-sm font-semibold text-foreground">中途返回不丢方向</div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">从报告或等待页返回时，描述会自动带回。</p>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
            <div className="surface-panel rounded-[32px] p-6 md:p-7">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="surface-section-kicker">产品描述</div>
                  <h3 className="mt-3 text-2xl font-semibold text-foreground">产品描述</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">写用户、场景、问题和解法，像真实对话即可。</p>
                </div>
                <div className="surface-chip inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold">
                  {characterBadge}
                </div>
              </div>

              <form onSubmit={onSubmit} className="mt-6 space-y-5">
                <div className="space-y-2">
                  <label htmlFor="productDescription" className="sr-only">
                    产品描述
                  </label>
                  <textarea
                    id="productDescription"
                    {...registerForm('productDescription')}
                    className="surface-field min-h-52 w-full resize-none rounded-[24px] px-4 py-4 text-sm leading-7 ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="示例：帮跨境卖家统一看 Amazon/Etsy/Shopify/TikTok 回款和手续费，减少手工对账与漏算。"
                  />
                  <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
                    <span>
                      {trimmedLength < MIN_CHARACTERS
                        ? `还需要至少 ${MIN_CHARACTERS - trimmedLength} 个字`
                        : trimmedLength > MAX_CHARACTERS
                          ? `超出 ${trimmedLength - MAX_CHARACTERS} 个字`
                          : '字数适合分析'}
                    </span>
                    <span>建议 10-500 字</span>
                  </div>
                  {errors.productDescription && (
                    <p className="text-sm text-destructive">{errors.productDescription.message}</p>
                  )}
                </div>

                <div className="rounded-[20px] border border-primary/15 bg-primary/5 px-4 py-3 text-sm leading-6 text-foreground">
                  这次会直接抓真实 Reddit 讨论。下面 6 张是固定标准样板，先带你看结果长什么样，再决定要不要改成你的方向。
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || !isValid}
                  className={clsx(
                    'inline-flex h-12 w-full items-center justify-center rounded-xl px-5 text-sm font-medium transition-colors',
                    isSubmitting || !isValid
                      ? 'cursor-not-allowed bg-muted text-muted-foreground'
                      : 'surface-action-primary'
                  )}
                >
                  <Zap className="mr-2 h-4 w-4" />
                  {isSubmitting ? '创建任务中...' : '开始 5 分钟分析'}
                </button>

                {apiError && (
                  <div className="rounded-[20px] border border-destructive/25 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {apiError}
                  </div>
                )}
              </form>
            </div>

            <aside className="space-y-4">
              <div className="surface-panel-muted rounded-[28px] p-5">
                <div className="surface-section-kicker">写得更准一点</div>
                <div className="mt-3 grid gap-3">
                  <div className="rounded-2xl bg-background/70 px-4 py-3">
                    <div className="text-sm font-semibold text-foreground">先写用户和场景</div>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">谁会用，在哪个场景会想到它。</p>
                  </div>
                  <div className="rounded-2xl bg-background/70 px-4 py-3">
                    <div className="text-sm font-semibold text-foreground">再写痛点和结果</div>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">最烦的问题是什么，你准备怎么帮他省时间或省钱。</p>
                  </div>
                </div>
              </div>
              <div className="surface-panel-muted rounded-[28px] p-5">
                <div className="surface-section-kicker">真流程</div>
                <div className="mt-3 rounded-2xl bg-background/70 px-4 py-3">
                  <div className="text-sm font-semibold text-foreground">先看任务状态，再看真实结果</div>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">你会先看到任务卡点和下一步，再进入机会/抱怨/覆盖范围的结果页。</p>
                </div>
              </div>
            </aside>
          </section>

          <section className="space-y-4">
            <div className="space-y-2 text-center">
              <div className="surface-section-kicker justify-center">快速起草</div>
              <h3 className="text-2xl font-semibold text-foreground">拿一个最像的，改成你自己的方向</h3>
              <p className="text-sm leading-6 text-muted-foreground">先看固定标准报告；如果方向接近，再把这题改成你自己的真实问题。</p>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {samplePrompts.map((example, index) => (
                <button
                  key={index}
                  type="button"
                  className="surface-panel-muted rounded-[24px] p-5 text-left transition-[transform,box-shadow,border-color] duration-300 hover:-translate-y-0.5 hover:border-primary/45 hover:shadow-editorial"
                  onClick={() => {
                    if (example.standardReportSlug) {
                      navigate(ROUTES.STANDARD_REPORT(example.standardReportSlug));
                      return;
                    }
                    setValue('productDescription', example.description, {
                      shouldValidate: true,
                      shouldDirty: true,
                    });
                    setSelectedTopicProfileId(example.topicProfileId);
                    setSelectedPromptSnapshot(example.description);
                  }}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-medium leading-none tracking-tight text-primary">{example.title}</h3>
                    {example.tags?.length ? (
                      <span className="text-xs text-muted-foreground">{example.tags.join(' / ')}</span>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground line-clamp-4">{example.description}</p>
                  <div className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-foreground">
                    先看标准报告
                    <Zap aria-hidden="true" className="h-4 w-4 text-primary" />
                  </div>
                </button>
              ))}
            </div>
          </section>
        </div>
      </main>

      <AuthDialog
        isOpen={isAuthDialogOpen}
        onClose={() => setIsAuthDialogOpen(false)}
        defaultTab={authDialogTab}
      />
    </div>
  );
};

export default InputPage;
