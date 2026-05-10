import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import clsx from 'clsx';
import {
  Search,
  Flame,
  Frown,
  Lightbulb,
  ArrowRight,
  AlertCircle,
  Hash,
} from 'lucide-react';

import { searchHotPost } from '@/services/hotpost.service';
import { HotPostMode, HotPostQueryParse } from '@/types/hotpost';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';

// Form Schema
const searchSchema = z.object({
  query: z.string().min(2, '关键词太短了 (至少 2 字符)').max(100, '关键词太长了'),
  mode: z.enum(['trending', 'rant', 'opportunity']),
  subreddits: z.string().optional(), // Comma separated string for input
});

type SearchFormValues = z.infer<typeof searchSchema>;

type HotPostSearchPrefillState = {
  prefillQuery?: string;
  prefillMode?: HotPostMode;
  prefillSubreddits?: string;
  prefillQueryParse?: HotPostQueryParse;
  prefillHint?: string;
  prefillSource?: 'retry-search';
};

const EMPTY_QUERY_PARSE: HotPostQueryParse = {
  query_kind: 'object',
  subject: '',
  compare_target: '',
  focus: '',
  scenario: '',
};

const QUERY_PARSE_PREFIX_RE =
  /^(?:为什么现在很多人觉得|为什么很多人觉得|为什么大家说|为什么会说|为什么|为何|为啥|最近|现在|大家说)\s*/;
const ASCII_ENTITY_RE = /[A-Za-z][A-Za-z0-9+._-]*(?:\s+[A-Za-z0-9+._-]+){0,2}/;

const toEditableQueryParse = (value?: HotPostQueryParse | null): HotPostQueryParse => ({
  query_kind: value?.query_kind ?? 'object',
  subject: value?.subject ?? '',
  compare_target: value?.compare_target ?? '',
  focus: value?.focus ?? '',
  scenario: value?.scenario ?? '',
});

const hasMeaningfulQueryParse = (value: HotPostQueryParse): boolean =>
  Boolean(value.subject?.trim() || value.compare_target?.trim() || value.focus?.trim() || value.scenario?.trim());

const isSameQueryParse = (left: HotPostQueryParse, right: HotPostQueryParse): boolean =>
  left.query_kind === right.query_kind &&
  (left.subject ?? '') === (right.subject ?? '') &&
  (left.compare_target ?? '') === (right.compare_target ?? '') &&
  (left.focus ?? '') === (right.focus ?? '') &&
  (left.scenario ?? '') === (right.scenario ?? '');

const normalizeQueryParseText = (value?: string | null): string => {
  const cleaned = String(value ?? '')
    .replace(/[，,。！？?!]+$/g, '')
    .trim()
    .replace(/\s+/g, ' ');
  return cleaned;
};

const deriveQueryParseFromQuery = (query: string): HotPostQueryParse => {
  const normalizedQuery = normalizeQueryParseText(query);
  if (!normalizedQuery) {
    return EMPTY_QUERY_PARSE;
  }

  const trimmed = normalizedQuery.replace(QUERY_PARSE_PREFIX_RE, '');
  const scenarioMatch = trimmed.match(/(?:在|做|用)([^，。！？?]{2,24}?)(?:时|的时候)/);
  const scenario = normalizeQueryParseText(scenarioMatch?.[1]);

  const compareMatch = trimmed.match(
    /([A-Za-z][A-Za-z0-9+._ -]{1,30})\s*(?:vs\.?|versus|比)\s*([A-Za-z][A-Za-z0-9+._ -]{1,30})/i,
  );
  if (compareMatch) {
    const subject = normalizeQueryParseText(compareMatch[1]);
    const compareTarget = normalizeQueryParseText(compareMatch[2]);
    let focusSource = trimmed;
    for (const marker of [subject, compareTarget]) {
      if (marker) {
        focusSource = focusSource.replace(new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig'), ' ');
      }
    }
    focusSource = focusSource.replace(/\b(?:vs\.?|versus)\b|比|比较|对比/gi, ' ');
    return {
      query_kind: 'compare',
      subject,
      compare_target: compareTarget,
      focus: normalizeQueryParseText(focusSource),
      scenario,
    };
  }

  const subjectMatch = trimmed.match(ASCII_ENTITY_RE);
  const subject = normalizeQueryParseText(subjectMatch?.[0]);
  const focus = normalizeQueryParseText(subject ? trimmed.slice(subject.length) : trimmed);
  return {
    query_kind: scenario && !subject ? 'scenario' : 'object',
    subject,
    compare_target: '',
    focus,
    scenario,
  };
};

const MODES: Array<{
  id: HotPostMode;
  title: string;
  icon: React.ElementType;
  description: string;
  color: string;
}> = [
  {
    id: 'trending',
    title: '热点追踪',
    icon: Flame,
    description: '发现最近最火的讨论趋势',
    color: 'text-orange-500',
  },
  {
    id: 'rant',
    title: '用户声音证据',
    icon: Frown,
    description: '先看真实原话，再判断大家在骂什么',
    color: 'text-red-500',
  },
  {
    id: 'opportunity',
    title: '机会发现',
    icon: Lightbulb,
    description: '挖掘未满足的需求和商机',
    color: 'text-yellow-500',
  },
];

const HotPostSearchPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [queryParse, setQueryParse] = useState<HotPostQueryParse>(EMPTY_QUERY_PARSE);
  const [queryParseTouched, setQueryParseTouched] = useState(false);
  const hasAppliedPrefill = useRef(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<SearchFormValues>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      query: '',
      mode: 'trending',
      subreddits: '',
    },
  });

  const selectedMode = watch('mode');
  const queryValue = watch('query');
  const locationState = (location.state as HotPostSearchPrefillState | null) ?? null;
  const prefillQuery = locationState?.prefillQuery?.trim() ?? '';
  const prefillMode = locationState?.prefillMode ?? 'trending';
  const prefillSubreddits = locationState?.prefillSubreddits ?? '';
  const prefillQueryParse = locationState?.prefillQueryParse ?? null;
  const prefillHint = locationState?.prefillHint?.trim() ?? '';
  const prefillTitle = locationState?.prefillSource === 'retry-search' ? '已带回这次搜索方向' : '已带回你刚才那次快扫';

  useEffect(() => {
    if (hasAppliedPrefill.current || !prefillQuery) {
      return;
    }

    setValue('query', prefillQuery, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('mode', prefillMode, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
    setValue('subreddits', prefillSubreddits, { shouldDirty: true, shouldTouch: true });
    setQueryParse(toEditableQueryParse(prefillQueryParse));
    setQueryParseTouched(Boolean(prefillQueryParse && hasMeaningfulQueryParse(toEditableQueryParse(prefillQueryParse))));
    hasAppliedPrefill.current = true;
  }, [prefillMode, prefillQuery, prefillQueryParse, prefillSubreddits, setValue]);

  useEffect(() => {
    if (selectedMode !== 'rant') {
      return;
    }
    if (queryParseTouched && hasMeaningfulQueryParse(queryParse)) {
      return;
    }
    const derived = deriveQueryParseFromQuery(queryValue || '');
    if (isSameQueryParse(queryParse, derived)) {
      return;
    }
    setQueryParse(derived);
  }, [queryParse, queryParseTouched, queryValue, selectedMode]);

  const onSubmit = async (values: SearchFormValues) => {
    setIsSubmitting(true);
    setApiError(null);

    try {
      // Parse subreddits
      const subredditsList = values.subreddits
        ? values.subreddits
            .split(/[,，\s]+/)
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
            .map((s) => (s.startsWith('r/') ? s : `r/${s}`))
            .slice(0, 5) // Max 5 limit
        : undefined;

      const queryParseOverride =
        values.mode === 'rant' && hasMeaningfulQueryParse(queryParse)
          ? {
              query_kind: queryParse.query_kind,
              ...(queryParse.subject?.trim() ? { subject: queryParse.subject.trim() } : {}),
              ...(queryParse.compare_target?.trim() ? { compare_target: queryParse.compare_target.trim() } : {}),
              ...(queryParse.focus?.trim() ? { focus: queryParse.focus.trim() } : {}),
              ...(queryParse.scenario?.trim() ? { scenario: queryParse.scenario.trim() } : {}),
            }
          : undefined;

      // Initiate Search
      const requestPayload = {
        query: values.query,
        mode: values.mode,
        ...(subredditsList ? { subreddits: subredditsList } : {}),
        ...(queryParseOverride ? { query_parse_override: queryParseOverride } : {}),
      };

      const response = await searchHotPost(requestPayload);

      // Navigate to Result Page
      // Note: We use the query_id from response to display the result
      navigate(`/hotpost/result/${response.query_id}`);
    } catch (error: any) {
      console.error('Search failed:', error);
      setApiError(error.message || '搜索请求失败，请稍后重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header (Simplified reuse) */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-2 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Reddit 爆帖速递</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl">
         <NavigationBreadcrumb currentStep="input" /> {/* Placeholder or adjust breadcrumb logic later */}

        {prefillQuery ? (
          <div className="mb-8 rounded-2xl border border-primary/20 bg-primary/5 px-5 py-4">
            <div className="text-sm font-semibold text-primary">{prefillTitle}</div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {prefillHint || '这次关键词和模式都已经带回来了。你可以直接改词、补社区，然后马上重扫一轮。'}
            </p>
          </div>
        ) : null}

        <div className="text-center space-y-4 mb-10">
          <h2 className="text-3xl font-bold text-foreground">你今天想探索什么？</h2>
          <p className="text-lg text-muted-foreground">
            无需等待，即刻获取 Reddit 上的最新市场信号
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {/* Mode Selection */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {MODES.map((mode) => {
              const Icon = mode.icon;
              const isSelected = selectedMode === mode.id;
              return (
                <div
                  key={mode.id}
                  onClick={() => setValue('mode', mode.id)}
                  className={clsx(
                    'cursor-pointer rounded-xl border-2 p-6 transition-all duration-200 hover:shadow-md',
                    isSelected
                      ? 'border-primary bg-primary/5 ring-1 ring-primary'
                      : 'border-border bg-card hover:border-primary/50'
                  )}
                >
                  <div className="flex items-center space-x-3 mb-3">
                    <div
                      className={clsx(
                        'p-2 rounded-lg',
                        isSelected ? 'bg-background' : 'bg-muted'
                      )}
                    >
                      <Icon className={clsx('w-6 h-6', mode.color)} />
                    </div>
                    <h3 className="font-semibold text-foreground">{mode.title}</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">{mode.description}</p>
                </div>
              );
            })}
          </div>

          {/* Search Input */}
          <div className="space-y-6 bg-card p-6 rounded-xl border border-border shadow-sm">
            <div className="space-y-2">
              <label htmlFor="query" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                关键词 / 话题
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
                <input
                  id="query"
                  {...register('query')}
                  className="flex h-12 w-full rounded-md border border-input bg-background px-10 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder={
                    selectedMode === 'trending' ? "例如: AI Tools, K-Pop, 跨境电商..." :
                    selectedMode === 'rant' ? "例如: Notion AI 总把笔记改成空话、Codex vs Claude..." :
                    "例如: Video Editing, Home Gym, EDC..."
                  }
                />
              </div>
              {errors.query && (
                <p className="text-sm text-destructive flex items-center mt-1">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  {errors.query.message}
                </p>
              )}
            </div>

            {/* Advanced / Optional: Subreddits */}
            <div className="space-y-2">
               <label htmlFor="subreddits" className="text-sm font-medium leading-none flex items-center text-muted-foreground">
                  <Hash className="w-3 h-3 mr-1" />
                  指定社区 (可选，最多5个，逗号分隔)
              </label>
              <input
                id="subreddits"
                {...register('subreddits')}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="例如: r/marketing, r/entrepreneur"
              />
              <p className="text-xs text-muted-foreground">如果不填，系统将自动匹配最相关的社区。</p>
            </div>

            {selectedMode === 'rant' ? (
              <div className="rounded-2xl border border-border bg-muted/30 p-4 space-y-4">
                <div>
                  <div className="text-sm font-medium text-foreground">搜索标签确认</div>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    这一步不是必填。你已经知道对象、对比方或关注点时，直接补上，能少走很多弯路。
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2 text-sm">
                    <span className="font-medium text-foreground">类型</span>
                    <select
                      value={queryParse.query_kind}
                      onChange={(event) => {
                        setQueryParseTouched(true);
                        setQueryParse((prev) => ({ ...prev, query_kind: event.target.value as HotPostQueryParse['query_kind'] }));
                      }}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="object">对象型</option>
                      <option value="compare">比较型</option>
                      <option value="scenario">场景型</option>
                    </select>
                  </label>
                  <label className="space-y-2 text-sm">
                    <span className="font-medium text-foreground">
                      {queryParse.query_kind === 'scenario' ? '对象（可选）' : '对象'}
                    </span>
                    <input
                      value={queryParse.subject ?? ''}
                      onChange={(event) => {
                        setQueryParseTouched(true);
                        setQueryParse((prev) => ({ ...prev, subject: event.target.value }));
                      }}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      placeholder={queryParse.query_kind === 'scenario' ? '例如：Premiere' : '例如：Notion AI'}
                    />
                  </label>
                  {queryParse.query_kind === 'compare' ? (
                    <label className="space-y-2 text-sm">
                      <span className="font-medium text-foreground">对比对象</span>
                      <input
                        value={queryParse.compare_target ?? ''}
                        onChange={(event) => {
                          setQueryParseTouched(true);
                          setQueryParse((prev) => ({ ...prev, compare_target: event.target.value }));
                        }}
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        placeholder="例如：Claude"
                      />
                    </label>
                  ) : null}
                  <label className="space-y-2 text-sm">
                    <span className="font-medium text-foreground">关注点</span>
                    <input
                      value={queryParse.focus ?? ''}
                      onChange={(event) => {
                        setQueryParseTouched(true);
                        setQueryParse((prev) => ({ ...prev, focus: event.target.value }));
                      }}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      placeholder="例如：改写成空话、听懂长指令、总是崩掉"
                    />
                  </label>
                  <label className="space-y-2 text-sm md:col-span-2">
                    <span className="font-medium text-foreground">场景</span>
                    <input
                      value={queryParse.scenario ?? ''}
                      onChange={(event) => {
                        setQueryParseTouched(true);
                        setQueryParse((prev) => ({ ...prev, scenario: event.target.value }));
                      }}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      placeholder="例如：AI coding、视频剪辑、团队协作"
                    />
                  </label>
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setQueryParseTouched(false);
                      setQueryParse(deriveQueryParseFromQuery(queryValue || ''));
                    }}
                    className="surface-action-secondary inline-flex h-9 items-center justify-center rounded-xl px-3 text-xs font-medium transition-colors"
                  >
                    按输入重新识别
                  </button>
                </div>
              </div>
            ) : null}

             {apiError && (
              <div className="rounded-md bg-destructive/15 p-3">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-destructive" aria-hidden="true" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-destructive">请求出错</h3>
                    <div className="mt-2 text-sm text-destructive/90">
                      <p>{apiError}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className={clsx(
                "w-full inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none h-11",
                "bg-primary text-primary-foreground hover:bg-primary/90"
              )}
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  扫描中...
                </>
              ) : (
                <>
                  开始扫描 <ArrowRight className="ml-2 w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3 text-center">
             <div className="p-4">
                <h4 className="font-semibold text-lg">🚀 极速响应</h4>
                <p className="text-sm text-muted-foreground mt-2">1-2分钟内锁定关键信息，无需漫长等待。</p>
             </div>
              <div className="p-4">
                <h4 className="font-semibold text-lg">🔍 证据溯源</h4>
                <p className="text-sm text-muted-foreground mt-2">先给你看真实原话和来源，不再先说空话。</p>
             </div>
              <div className="p-4">
                <h4 className="font-semibold text-lg">🤖 智能分析</h4>
                <p className="text-sm text-muted-foreground mt-2">热点、用户声音、机会切口三条链路分开看，不再混在一起。</p>
             </div>
        </div>
      </main>
    </div>
  );
};

export default HotPostSearchPage;
