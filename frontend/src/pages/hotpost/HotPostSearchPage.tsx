import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { HotPostMode } from '@/types/hotpost';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';

// Form Schema
const searchSchema = z.object({
  query: z.string().min(2, '关键词太短了 (至少 2 字符)').max(100, '关键词太长了'),
  mode: z.enum(['trending', 'rant', 'opportunity']),
  subreddits: z.string().optional(), // Comma separated string for input
});

type SearchFormValues = z.infer<typeof searchSchema>;

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
    title: '痛点挖掘',
    icon: Frown,
    description: '寻找用户吐槽和负面反馈',
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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

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

      // Initiate Search
      const requestPayload = {
        query: values.query,
        mode: values.mode,
        ...(subredditsList ? { subreddits: subredditsList } : {}),
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
                    selectedMode === 'rant' ? "例如: Adobe, Salesforce, Robot Vacuum..." :
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
                <p className="text-sm text-muted-foreground mt-2">每个结论都附带 Reddit 原帖链接，真实可信。</p>
             </div>
              <div className="p-4">
                <h4 className="font-semibold text-lg">🤖 智能分析</h4>
                <p className="text-sm text-muted-foreground mt-2">自动识别吐槽、机会和热点，节省人工筛选时间。</p>
             </div>
        </div>
      </main>
    </div>
  );
};

export default HotPostSearchPage;
