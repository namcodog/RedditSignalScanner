import { createContext, useCallback, useContext, useMemo, useState } from 'react';

type Locale = 'zh' | 'en';
type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

interface TranslationContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: TranslateFn;
}

const STORAGE_KEY = 'rss_locale';

const translations: Record<Locale, Record<string, string>> = {
  zh: {
    'report.brandName': 'Reddit 商业信号扫描器',
    'report.brandTagline': '市场洞察报告',
    'report.error.generic': '获取报告失败，请稍后重试',
    'report.error.subtitle': '报告加载失败',
    'report.error.title': '获取报告失败',
    'report.error.detail': '无法加载分析报告，请检查任务ID是否正确或稍后重试',
    'report.error.backHome': '返回首页',
    'report.title': '市场洞察报告',
    'report.subtitle': '分析已完成 • 已分析 {{count}} 条提及',
    'report.viewInsights': '查看洞察卡片',
    'report.share.button': '分享',
    'report.share.success': '分享链接已复制',
    'report.share.error': '分享失败，请稍后重试',
    'report.share.description': '与团队分享这份 Reddit 市场洞察报告',
    'report.export.error': '导出失败，请稍后重试',
    'report.export.loading': '导出中...',
    'report.export.download': '导出报告',
    'report.export.options.json': '导出为 JSON',
        'report.export.options.csv': '导出为 CSV',
        'report.export.options.text': '导出为 TXT',
        'report.export.options.pdf': '导出为 PDF',
        'report.export.progress': '正在导出 {{format}} ...',
    'report.export.history': '导出历史',
    'report.export.history.empty': '暂无导出记录',
    'report.export.history.task': '任务 {{taskId}}',
    'report.export.format.json': 'JSON 文件',
    'report.export.format.csv': 'CSV 文件',
    'report.export.format.text': 'TXT 文件',
    'report.progress.cache': '正在校验缓存',
    'report.progress.fetch': '正在获取报告数据',
    'report.progress.hydrate': '正在解析分析结构',
    'report.progress.render': '正在生成视图',
    'report.export.stage.prepare': '准备数据',
    'report.export.stage.format': '格式化 {{format}}',
    'report.export.stage.history': '写入导出历史',
    'report.export.stage.complete': '导出完成',
    'report.locale.zh': '中文',
    'report.locale.en': 'English',
    'report.nav.login': '登录',
    'report.nav.register': '注册',
    'report.productAnalyzed': '已分析产品',
    'report.summary.title': '执行摘要',
    'report.summary.totalCommunities': '分析社区数',
    'report.summary.keyInsights': '关键洞察数',
    'report.summary.topOpportunity': '最重要机会',
    'report.summary.noOpportunity': '暂无机会',
    'report.metrics.totalMentions': '总提及数',
    'report.metrics.positive': '正面情感',
    'report.metrics.communities': '社区数量',
    'report.metrics.opportunities': '商业机会',
    'report.tabs.overview': '概览',
    'report.tabs.painPoints': '用户痛点',
    'report.tabs.competitors': '竞品分析',
    'report.tabs.opportunities': '商业机会',
    'report.tabs.actions': '行动建议',
    'report.tabs.entities': '关键实体',
    'report.overview.marketSentiment': '市场情感',
    'report.overview.sentiment.positive': '正面',
    'report.overview.sentiment.negative': '负面',
    'report.overview.sentiment.neutral': '中性',
    'report.overview.topCommunities': '热门社区',
    'report.overview.mentions': '{{count}} 次提及',
    'report.overview.relevance': '{{score}}% 相关',
    'report.overview.noCommunities': '暂无社区数据',
    'report.overview.topOfTotal': 'Top {{top}} / Total {{total}}（{{source}}）',
    'report.overview.source.pool': '社区池',
    'report.overview.source.pool_discovery': '社区池+发现',
    'report.overview.download.json': '下载社区（结构化）',
    'report.overview.download.csv': '下载社区（表格）',
    'report.painPoints.empty': '暂无用户痛点数据',
    'report.competitors.empty': '暂无竞品分析数据',
    'report.opportunities.empty': '暂无商业机会数据',
    'report.actions.empty': '暂无行动建议',
    'report.actions.startNew': '开始新分析',
    'report.entities.empty': '暂无实体匹配',
    'report.entities.categories.brands': '品牌',
    'report.entities.categories.features': '功能',
    'report.entities.categories.pain_points': '痛点关键词',
    'report.entities.mentions': '{{count}} 次提及',
    'report.metadata.title': '分析元数据',
    'report.metadata.analysisVersion': '分析版本',
    'report.metadata.confidence': '置信度',
    'report.metadata.processingTime': '耗时',
    'report.metadata.cacheHitRate': '缓存命中率',
  },
  en: {
    'report.brandName': 'Reddit Signal Scanner',
    'report.brandTagline': 'Market Insight Report',
    'report.error.generic': 'Failed to load the report, please try again later',
    'report.error.subtitle': 'Report load failed',
    'report.error.title': 'Unable to fetch report',
    'report.error.detail': 'We could not load this analysis report. Please verify the task ID or retry later.',
    'report.error.backHome': 'Back to Home',
    'report.title': 'Market Insight Report',
    'report.subtitle': 'Analysis complete • {{count}} mentions analyzed',
    'report.viewInsights': 'View Insight Cards',
    'report.share.button': 'Share',
    'report.share.success': 'Share link copied',
    'report.share.error': 'Share failed, please try again later',
    'report.share.description': 'Share this Reddit market insight report with your team',
    'report.export.error': 'Export failed, please try again later',
    'report.export.loading': 'Exporting...',
    'report.export.download': 'Export Report',
    'report.export.options.json': 'Export as JSON',
        'report.export.options.csv': 'Export as CSV',
        'report.export.options.text': 'Export as TXT',
        'report.export.options.pdf': 'Export as PDF',
    'report.export.progress': 'Exporting {{format}} ...',
    'report.export.history': 'Export History',
    'report.export.history.empty': 'No export history yet',
    'report.export.history.task': 'Task {{taskId}}',
    'report.export.format.json': 'JSON file',
    'report.export.format.csv': 'CSV file',
    'report.export.format.text': 'TXT file',
    'report.progress.cache': 'Validating cache',
    'report.progress.fetch': 'Fetching report data',
    'report.progress.hydrate': 'Hydrating insights',
    'report.progress.render': 'Rendering view',
    'report.export.stage.prepare': 'Preparing data',
    'report.export.stage.format': 'Formatting {{format}}',
    'report.export.stage.history': 'Recording export history',
    'report.export.stage.complete': 'Export complete',
    'report.locale.zh': 'Chinese',
    'report.locale.en': 'English',
    'report.nav.login': 'Log in',
    'report.nav.register': 'Sign up',
    'report.productAnalyzed': 'Product analysed',
    'report.summary.title': 'Executive Summary',
    'report.summary.totalCommunities': 'Communities analysed',
    'report.summary.keyInsights': 'Key insights',
    'report.summary.topOpportunity': 'Top opportunity',
    'report.summary.noOpportunity': 'No opportunity highlighted',
    'report.metrics.totalMentions': 'Total mentions',
    'report.metrics.positive': 'Positive sentiment',
    'report.metrics.communities': 'Communities',
    'report.metrics.opportunities': 'Opportunities',
    'report.tabs.overview': 'Overview',
    'report.tabs.painPoints': 'Pain Points',
    'report.tabs.competitors': 'Competitors',
    'report.tabs.opportunities': 'Opportunities',
    'report.tabs.actions': 'Action Items',
    'report.tabs.entities': 'Entities',
    'report.overview.marketSentiment': 'Market Sentiment',
    'report.overview.sentiment.positive': 'Positive',
    'report.overview.sentiment.negative': 'Negative',
    'report.overview.sentiment.neutral': 'Neutral',
    'report.overview.topCommunities': 'Top Communities',
    'report.overview.mentions': '{{count}} mentions',
    'report.overview.relevance': '{{score}}% relevance',
    'report.overview.noCommunities': 'No community data available',
    'report.overview.topOfTotal': 'Top {{top}} of Total {{total}} ({{source}})',
    'report.overview.source.pool': 'Pool',
    'report.overview.source.pool_discovery': 'Pool + Discovery',
    'report.overview.download.json': 'Download Communities (Structured)',
    'report.overview.download.csv': 'Download Communities (Table)',
    'report.painPoints.empty': 'No pain point data',
    'report.competitors.empty': 'No competitor data',
    'report.opportunities.empty': 'No opportunity data',
    'report.actions.empty': 'No action items',
    'report.actions.startNew': 'Start New Analysis',
    'report.entities.empty': 'No entities detected',
    'report.entities.categories.brands': 'Brands',
    'report.entities.categories.features': 'Features',
    'report.entities.categories.pain_points': 'Pain Indicators',
    'report.entities.mentions': '{{count}} mentions',
    'report.metadata.title': 'Analysis Metadata',
    'report.metadata.analysisVersion': 'Version',
    'report.metadata.confidence': 'Confidence',
    'report.metadata.processingTime': 'Processing Time',
    'report.metadata.cacheHitRate': 'Cache Hit Rate',
  },
};

const TranslationContext = createContext<TranslationContextValue | undefined>(undefined);

const formatTemplate = (template: string, params?: Record<string, string | number>) => {
  if (!params) return template;
  return template.replace(/{{(.*?)}}/g, (_, key) => {
    const value = params[key.trim()];
    return value === undefined || value === null ? '' : String(value);
  });
};

const loadInitialLocale = (initial?: Locale): Locale => {
  if (initial) return initial;
  if (typeof window === 'undefined') return 'zh';
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === 'en' ? 'en' : 'zh';
  } catch {
    return 'zh';
  }
};

export const TranslationProvider: React.FC<{ initialLocale?: Locale; children: React.ReactNode }> = ({
  initialLocale,
  children,
}) => {
  const [locale, setLocaleState] = useState<Locale>(() => loadInitialLocale(initialLocale));

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore storage errors (private mode, etc.)
    }
  }, []);

  const value = useMemo<TranslationContextValue>(() => {
    const translate: TranslateFn = (key, params) => {
      const dict = translations[locale] ?? translations.zh;
      const fallback = translations.zh[key as keyof typeof translations.zh];
      const template = dict[key] ?? fallback ?? key;
      return formatTemplate(template, params);
    };

    return {
      locale,
      setLocale,
      t: translate,
    };
  }, [locale, setLocale]);

  return <TranslationContext.Provider value={value}>{children}</TranslationContext.Provider>;
};

export const useTranslation = () => {
  const ctx = useContext(TranslationContext);
  if (!ctx) {
    throw new Error('useTranslation must be used within TranslationProvider');
  }
  return ctx;
};

export const SUPPORTED_LOCALES: Locale[] = ['zh', 'en'];
