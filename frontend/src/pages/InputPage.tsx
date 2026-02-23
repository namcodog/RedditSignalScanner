import { useEffect, useMemo, useState } from 'react';
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
import { getInputGuidance } from '@/api/guidance.api';
import { isAuthenticated, logout } from '@/api/auth.api';
import { ROUTES } from '@/router';
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
  exampleId?: string | null;
};

const FALLBACK_PROMPTS: SamplePrompt[] = [
  {
    title: 'SaaS 工具',
    description: '一个面向远程团队的项目管理工具，集成 Slack 并自动跟踪任务时间...',
  },
  {
    title: '移动应用',
    description: '一个健身应用，根据可用设备和时间限制创建个性化锻炼计划...',
  },
  {
    title: '电商平台',
    description: '一个专注于可持续时尚品牌的在线市场，重视透明度和道德制造...',
  },
  {
    title: '跨境电商',
    description: '跨境电商卖家多平台回款与手续费管理工具，覆盖 Amazon/Etsy/Shopify/TikTok Shop，解决结算周期长、费率不透明、资金分散的问题。',
  },
  {
    title: '家居收纳',
    description: '面向北美租房人群的家居收纳与清洁工具推荐/比价助手，解决空间小、产品选择多、踩雷的问题。',
  },
  {
    title: '户外/EDC',
    description: '户外露营与日常随身工具（EDC）选购与评测助手，帮助新手挑选高性价比装备，减少踩坑。',
  },
];

const InputPage: React.FC = () => {
  const navigate = useNavigate();
  const [apiError, setApiError] = useState<string | null>(null);
  const [isAuthDialogOpen, setIsAuthDialogOpen] = useState(false);
  const [authDialogTab, setAuthDialogTab] = useState<'login' | 'register'>('login');
  const [samplePrompts, setSamplePrompts] = useState<SamplePrompt[]>(FALLBACK_PROMPTS);
  const [selectedExampleId, setSelectedExampleId] = useState<string | null>(null);
  const [selectedExamplePrompt, setSelectedExamplePrompt] = useState<string | null>(null);

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
          .map((example) => ({
            title: example.title || '示例',
            description: example.prompt,
            tags: example.tags ?? [],
            exampleId: example.example_id ?? null,
          }))
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
    if (!selectedExampleId || !selectedExamplePrompt) {
      return;
    }
    if (productDescription.trim() !== selectedExamplePrompt.trim()) {
      setSelectedExampleId(null);
      setSelectedExamplePrompt(null);
    }
  }, [productDescription, selectedExampleId, selectedExamplePrompt]);

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
      const response = await createAnalyzeTask({
        product_description: description,
        ...(selectedExampleId && description === selectedExamplePrompt?.trim()
          ? { example_id: selectedExampleId }
          : {}),
      });
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
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Reddit 商业信号扫描器</h1>
            <button
               onClick={() => navigate(ROUTES.HOTPOST)}
               className="ml-6 flex items-center space-x-1 px-3 py-1.5 rounded-full bg-orange-100 text-orange-700 hover:bg-orange-200 text-sm font-medium transition-colors"
            >
               <span>🔥 爆帖速递</span>
            </button>
          </div>
          <div className="flex items-center space-x-4">
            {isAuthenticated() ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm text-muted-foreground">欢迎回来</span>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3"
                >
                  退出登录
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => { setAuthDialogTab('login'); setIsAuthDialogOpen(true); }}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3"
                >
                  登录
                </button>
                <button
                  onClick={() => { setAuthDialogTab('register'); setIsAuthDialogOpen(true); }}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-3"
                >
                  注册
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <NavigationBreadcrumb currentStep="input" />

        <div className="max-w-4xl mx-auto space-y-8">
          {/* Header Section */}
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center space-x-2 mb-4">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                <Lightbulb className="w-6 h-6 text-primary" />
              </div>
            </div>
            <h2 className="text-3xl font-bold text-foreground">描述您的产品想法</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              详细告诉我们您的产品或服务。您描述得越具体，我们能提供的洞察就越好。
            </p>
          </div>

          {/* Main Input Form */}
          <div className="rounded-xl border-2 border-dashed border-border hover:border-secondary/50 transition-colors bg-card text-card-foreground shadow-sm">
            <div className="flex flex-col space-y-1.5 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold leading-none tracking-tight flex items-center space-x-2">
                    <Target className="w-5 h-5 text-primary" />
                    <span>产品描述</span>
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">包括您的目标受众、核心功能以及您要解决的问题</p>
                </div>
                <div className={clsx(
                  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ml-4",
                  "border-transparent bg-primary text-primary-foreground hover:bg-primary/80"
                )}>
                  {characterBadge}
                </div>
              </div>
            </div>
            <div className="p-6 pt-0">
              <form onSubmit={onSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label htmlFor="productDescription" className="sr-only">
                    产品描述
                  </label>
                  <textarea
                    id="productDescription"
                    {...registerForm('productDescription')}
                    className="flex min-h-40 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none p-4"
                    placeholder="示例：一个帮助忙碌专业人士进行餐食准备的移动应用，根据饮食偏好、烹饪时间限制和当地杂货店供应情况生成个性化的每周餐食计划。该应用包括自动生成购物清单、分步烹饪指导以及与热门配送服务集成等功能..."
                  />
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>
                      {trimmedLength < MIN_CHARACTERS
                        ? `还需要至少 ${MIN_CHARACTERS - trimmedLength} 个字`
                        : trimmedLength > MAX_CHARACTERS
                          ? `超出 ${trimmedLength - MAX_CHARACTERS} 个字`
                          : "字数适合分析"}
                    </span>
                    <span>建议 10-500 字</span>
                  </div>
                  {errors.productDescription && (
                    <p className="text-sm text-destructive">{errors.productDescription.message}</p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || !isValid}
                  className={clsx(
                    "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 h-11 rounded-md px-8 w-full",
                    (isSubmitting || !isValid)
                      ? "bg-gray-500 text-white cursor-not-allowed" // Disabled: Grey
                      : "bg-black text-white hover:bg-black/90"     // Enabled: Black
                  )}
                >
                  <Zap className="w-4 h-4 mr-2" />
                  {isSubmitting ? '创建任务中...' : '开始 5 分钟分析'}
                </button>

                {apiError && (
                  <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {apiError}
                  </div>
                )}
              </form>
            </div>
          </div>

          {/* Example Ideas */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-foreground text-center">需要灵感？试试这些示例：</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {samplePrompts.map((example, index) => (
                <div
                  key={index}
                  className="rounded-lg border bg-card text-card-foreground shadow-sm cursor-pointer hover:shadow-md transition-shadow border-border hover:border-primary/50"
                  onClick={() => {
                    setValue('productDescription', example.description, { shouldValidate: true, shouldDirty: true });
                    setSelectedExampleId(example.exampleId ?? null);
                    setSelectedExamplePrompt(example.description.trim());
                  }}
                >
                  <div className="flex flex-col space-y-1.5 p-6 pb-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-medium text-primary leading-none tracking-tight">{example.title}</h3>
                      {example.tags?.length ? (
                        <span className="text-xs text-muted-foreground">{example.tags.join(' / ')}</span>
                      ) : null}
                    </div>
                  </div>
                  <div className="p-6 pt-0">
                    <p className="text-sm text-muted-foreground line-clamp-3">{example.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Process Timeline */}
          <div className="bg-card rounded-lg p-6 border border-border shadow-sm text-card-foreground">
            <h3 className="text-lg font-semibold text-foreground mb-4 text-center">接下来会发生什么？</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center space-y-2">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
                  <Clock className="w-6 h-6 text-primary" />
                </div>
                <h4 className="font-medium text-foreground">步骤 1：分析</h4>
                <p className="text-sm text-muted-foreground">我们扫描相关的 Reddit 社区，寻找关于您市场的讨论</p>
              </div>
              <div className="text-center space-y-2">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
                  <Target className="w-6 h-6 text-primary" />
                </div>
                <h4 className="font-medium text-foreground">步骤 2：处理</h4>
                <p className="text-sm text-muted-foreground">AI 分析用户痛点、竞品提及和市场机会</p>
              </div>
              <div className="text-center space-y-2">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
                  <Lightbulb className="w-6 h-6 text-primary" />
                </div>
                <h4 className="font-medium text-foreground">步骤 3：洞察</h4>
                <p className="text-sm text-muted-foreground">获得包含可操作商业洞察的综合报告</p>
              </div>
            </div>
          </div>
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
