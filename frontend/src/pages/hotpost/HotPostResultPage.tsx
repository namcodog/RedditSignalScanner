import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  BarChart2,
  MessageSquare,
  ThumbsUp,
  FileText,
  Zap,
  Frown,
  Lightbulb,
  TrendingUp,
  Users,
  Target,
  ArrowRight,
  ShieldAlert,
  Clock
} from 'lucide-react';
import clsx from 'clsx';

import { getHotPostResult, generateDeepDiveToken, subscribeToHotPostStream } from '@/services/hotpost.service';
import { HotPostResponse, HotPost, ConfidenceLevel } from '@/types/hotpost';
import { isAuthenticated } from '@/api/auth.api';
import AuthDialog from '@/components/AuthDialog';
import { SSEEvent, SSEQueueUpdateEvent } from '@/types';
import SurfaceHero from '@/components/product/SurfaceHero';
import ProductStatePanel from '@/components/product/ProductStatePanel';
import DecisionSummaryPanel from '@/components/product/DecisionSummaryPanel';
import { buildHotpostActionPlan, buildHotpostDecisionSummary, buildHotpostSurfaceHero } from '@/lib/product-surface';

// --- Helper Components ---

const ConfidenceBadge: React.FC<{ level: ConfidenceLevel; count: number }> = ({ level, count }) => {
  const config = {
    high: { color: 'bg-amber-100 text-amber-900 border-amber-200', icon: CheckCircle2, label: '✔ 信号可靠' },
    medium: { color: 'bg-slate-100 text-slate-700 border-slate-200', icon: AlertTriangle, label: '⚠ 信号一般' },
    low: { color: 'bg-gray-50 text-gray-600 border-gray-200', icon: HelpCircle, label: '△ 信号有限' },
    none: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: HelpCircle, label: '正在补证据' },
  };

  const { color, icon: Icon, label } = config[level] || config.none;

  return (
    <div className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', color)}>
      <Icon className="w-3 h-3 mr-1" />
      {label} ({count} 证据)
    </div>
  );
};

const toUserFacingHotpostError = (): string =>
  '系统已接到这次搜索，正在重新整理热点信号。先重试一次，不行就换关键词重扫。';

const summarizeSentiment = (value: string | undefined): string => {
  if (!value) return '中性';
  if (value === 'positive') return '被夸较多';
  if (value === 'negative') return '吐槽较多';
  return '中性';
};

const normalizeTrendLabel = (value: string | undefined): string => {
  if (!value) return '持续关注';
  const normalized = value.trim().toLowerCase();
  if (['explosive', 'exploding', '新兴🆕', '新兴', '爆发中', '爆发中 new'].includes(normalized)) {
    return '爆发中 NEW';
  }
  if (['rising', '上升中', '上升中↑', '上升'].includes(normalized)) {
    return '上升中 ↑';
  }
  if (['stable', 'sustained', '持续热门', '持续热度', '持续热度↗'].includes(normalized)) {
    return '持续热度 ↗';
  }
  if (['declining', '下降中', '下降中↓', '下降'].includes(normalized)) {
    return '下降中 ↓';
  }
  return value.trim();
};

const hasCjk = (value: string): boolean => /[\u3400-\u9FFF]/.test(value);
const cjkRatio = (value: string): number => {
  const content = value.replace(/\s+/g, '');
  if (!content) return 0;
  const cjkCount = (content.match(/[\u3400-\u9FFF]/g) ?? []).length;
  return cjkCount / content.length;
};

const stripMarkdownNoise = (value: string): string =>
  value
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\s+/g, ' ')
    .trim();

const toHotpostReadableText = (value: string | undefined, fallback: string, maxLength = 88): string => {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return fallback;
  }

  const cleaned = stripMarkdownNoise(raw);
  if (!cleaned) {
    return fallback;
  }

  if (!hasCjk(cleaned)) {
    return fallback;
  }

  if (cjkRatio(cleaned) < 0.35) {
    return fallback;
  }

  return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength).trimEnd()}…` : cleaned;
};

const toHotpostTopicTitle = (value: string | undefined, rank?: number): string => {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return `重点话题 ${rank ?? ''}`.trim();
  }
  if (!hasCjk(raw)) {
    return `重点话题 ${rank ?? ''}`.trim();
  }
  return raw;
};

const toPostPreviewText = (value: string | undefined): string => {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return '';
  }
  const cleaned = stripMarkdownNoise(raw);
  if (!cleaned) {
    return '';
  }
  if (!hasCjk(cleaned)) {
    return '该证据原文为英文，建议点击原帖查看完整上下文。';
  }
  return cleaned;
};

const toHotpostQuoteText = (value: string | undefined, maxLength = 160): string => {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return '';
  }

  const cleaned = stripMarkdownNoise(raw).replace(/^["“”]+|["“”]+$/g, '').trim();
  if (!cleaned || /^\[(removed|deleted)\]$/i.test(cleaned)) {
    return '';
  }

  return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength).trimEnd()}…` : cleaned;
};

const pickHotpostQuote = (...values: Array<string | undefined | null>): string | null => {
  for (const value of values) {
    const quote = toHotpostQuoteText(String(value ?? ''));
    if (quote) {
      return quote;
    }
  }
  return null;
};

type HotpostEvidenceQuote = {
  quote: string;
  subreddit: string | undefined;
  url: string | undefined;
  createdUtc: number | undefined;
};

const collectHotpostEvidenceQuotes = (
  payload: HotPostResponse | null
): HotpostEvidenceQuote[] => {
  if (!payload) {
    return [];
  }

  const timeLookup = new Map<string, number>();
  const registerPostTime = (post?: HotPost | null) => {
    if (!post?.reddit_url || !post.created_utc) {
      return;
    }
    timeLookup.set(post.reddit_url, post.created_utc);
  };

  for (const post of payload.top_posts ?? []) {
    registerPostTime(post);
  }
  for (const painPoint of payload.pain_points ?? []) {
    for (const post of painPoint.evidence_posts ?? []) {
      registerPostTime(post);
    }
  }

  const directQuotes =
    payload.top_quotes
      ?.map((item) => ({
        quote: toHotpostQuoteText(item.quote),
        subreddit: item.subreddit,
        url: item.url,
        createdUtc: item.created_utc ?? (item.url ? timeLookup.get(item.url) : undefined),
      }))
      .filter((item) => item.quote) ?? [];

  if (directQuotes.length > 0) {
    return directQuotes.slice(0, 3);
  }

  const unmetNeeds = payload.unmet_needs?.length ? payload.unmet_needs : payload.opportunities || [];
  const fallbackCandidates = [
    ...(payload.topics ?? []).flatMap((topic) =>
      (topic.evidence ?? []).map((evidence) => ({
        quote: toHotpostQuoteText(evidence.key_quote),
        subreddit: evidence.subreddit,
        url: evidence.url,
        createdUtc: evidence.url ? timeLookup.get(evidence.url) : undefined,
      })),
    ),
    ...(payload.pain_points ?? []).flatMap((painPoint) =>
      (painPoint.evidence ?? []).map((evidence) => ({
        quote: toHotpostQuoteText(evidence.key_quote),
        subreddit: undefined,
        url: evidence.url,
        createdUtc: evidence.url ? timeLookup.get(evidence.url) : undefined,
      })),
    ),
    ...unmetNeeds.flatMap((need) =>
      (need.evidence ?? []).map((evidence) => ({
        quote: toHotpostQuoteText(evidence.key_quote),
        subreddit: evidence.subreddit,
        url: evidence.url,
        createdUtc: evidence.url ? timeLookup.get(evidence.url) : undefined,
      })),
    ),
    ...(payload.competitor_mentions ?? []).map((competitor) => ({
      quote: pickHotpostQuote(competitor.sample_quote, competitor.evidence_quote) ?? '',
      subreddit: undefined,
      url: undefined,
      createdUtc: undefined,
    })),
    payload.migration_intent?.key_quote
      ? {
          quote: toHotpostQuoteText(payload.migration_intent.key_quote),
          subreddit: undefined,
          url: undefined,
          createdUtc: undefined,
        }
      : null,
  ];

  const normalizedCandidates = fallbackCandidates.filter((item): item is HotpostEvidenceQuote => Boolean(item?.quote));

  return normalizedCandidates
    .filter((item, index, source) => source.findIndex((candidate) => candidate.quote === item.quote) === index)
    .slice(0, 3);
};

const formatHotpostEvidenceTime = (value?: number): string | null => {
  if (!value) {
    return null;
  }
  return new Date(value * 1000).toLocaleDateString();
};

const collectRantRepresentativePosts = (payload: HotPostResponse | null): HotPost[] => {
  if (!payload) {
    return [];
  }

  const selected: HotPost[] = [];
  const seen = new Set<string>();

  for (const painPoint of payload.pain_points ?? []) {
    for (const post of painPoint.evidence_posts ?? []) {
      if (!post?.id || seen.has(post.id)) {
        continue;
      }
      seen.add(post.id);
      selected.push(post);
    }
  }

  for (const post of payload.top_posts ?? []) {
    if (!post?.id || seen.has(post.id)) {
      continue;
    }
    seen.add(post.id);
    selected.push(post);
  }

  return selected;
};

const pickHotpostRangeNote = (payload: HotPostResponse | null): string | null => {
  if (!payload) {
    return null;
  }

  const reliabilityNote = payload.reliability_note?.trim();
  if (reliabilityNote) {
    return reliabilityNote;
  }

  const nextNote = payload.notes?.find((item) => {
    const cleaned = String(item ?? '').trim();
    return cleaned && !cleaned.includes('关键词过长') && !cleaned.includes('已拆分为');
  });

  return nextNote?.trim() || null;
};

const pickHotpostSummary = (payload: HotPostResponse | null): string => {
  if (!payload) return '';

  if (payload.mode === 'trending') {
    const topicTakeaway = toHotpostReadableText(
      payload.topics?.[0]?.key_takeaway,
      '这波热度在上升，先扫证据再决定要不要继续追。'
    );
    if (topicTakeaway) {
      return topicTakeaway;
    }
  }

  return toHotpostReadableText(
    payload.summary?.trim() ||
      payload.topics?.[0]?.key_takeaway?.trim() ||
      payload.unmet_needs?.[0]?.summary?.trim() ||
      payload.pain_points?.[0]?.description?.trim(),
    '这轮快扫已经把方向捞出来了。'
  );
};

const PostCard: React.FC<{ post: HotPost }> = ({ post }) => {
  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors">
      <div className="flex justify-between items-start gap-4">
        <div className="space-y-1 flex-1">
          <a
            href={post.reddit_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-foreground hover:text-primary line-clamp-2"
          >
            {post.title}
          </a>
          <div className="flex items-center text-xs text-muted-foreground gap-3">
            <span className="font-semibold text-primary">{post.subreddit}</span>
            <span>•</span>
            <span>by u/{post.author}</span>
            <span>•</span>
            <span>{new Date(post.created_utc * 1000).toLocaleDateString()}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 min-w-[60px]">
           <div className="flex items-center text-orange-500 text-sm font-bold">
             <ThumbsUp className="w-3 h-3 mr-1" />
             {post.score > 1000 ? `${(post.score / 1000).toFixed(1)}k` : post.score}
           </div>
           <div className="flex items-center text-muted-foreground text-xs">
             <MessageSquare className="w-3 h-3 mr-1" />
             {post.num_comments}
           </div>
        </div>
      </div>
      {post.body_preview && (
        <p className="text-sm text-muted-foreground mt-3 line-clamp-3">
          {toPostPreviewText(post.body_preview)}
        </p>
      )}
       {/* Signals */}
      {post.signals && post.signals.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
            {post.signals.slice(0, 3).map((sig, idx) => (
                <span key={idx} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground">
                    #{sig}
                </span>
            ))}
        </div>
      )}
    </div>
  );
};

const QueueOverlay: React.FC<{ position?: number | undefined; estimatedWait?: number | undefined }> = ({ position, estimatedWait }) => (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center p-4">
        <div className="surface-panel max-w-md w-full rounded-[28px] p-8 text-center space-y-6">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto animate-pulse">
                <Clock className="w-8 h-8 text-primary" />
            </div>
            <div>
                <h3 className="text-2xl font-semibold text-foreground">正在排队中…</h3>
                <p className="text-muted-foreground mt-2">系统正忙，您的请求已加入优先队列</p>
            </div>

            <div className="grid grid-cols-2 gap-4 bg-muted/50 rounded-lg p-4">
                <div className="text-center">
                    <div className="text-sm text-muted-foreground">当前排位</div>
                    <div className="text-2xl font-bold text-primary">{position ?? '-'}</div>
                </div>
                <div className="text-center">
                    <div className="text-sm text-muted-foreground">预计等待</div>
                    <div className="text-2xl font-bold text-primary">{estimatedWait ? `${estimatedWait}s` : '-'}</div>
                </div>
            </div>

            <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                <div className="bg-primary h-full w-1/3 animate-[loading_2s_ease-in-out_infinite]" />
            </div>
        </div>
    </div>
);

// --- Main Page Component ---

const HotPostResultPage: React.FC = () => {
  const { queryId } = useParams<{ queryId: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<HotPostResponse | null>(null);
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'queued'>('loading');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Queue State
  const [queuePosition, setQueuePosition] = useState<number | undefined>(undefined);
  const [estimatedWait, setEstimatedWait] = useState<number | undefined>(undefined);
  const sseClientRef = useRef<any>(null);

  // Auth Dialog State
  const [isAuthDialogOpen, setIsAuthDialogOpen] = useState(false);
  const [isGeneratingDeepDive, setIsGeneratingDeepDive] = useState(false);
  const [, setPollingAttempt] = useState(0);
  const [showAllTopics, setShowAllTopics] = useState(false);
  const [showAllEvidence, setShowAllEvidence] = useState(false);
  const [showAdvancedInsights, setShowAdvancedInsights] = useState(false);
  const evidenceSectionRef = useRef<HTMLElement | null>(null);

  const unmetNeeds = data?.unmet_needs?.length
    ? data.unmet_needs
    : data?.opportunities || [];
  const marketOpportunityText =
    typeof data?.market_opportunity === 'string'
      ? data.market_opportunity
      : data?.market_opportunity?.gap;
  const marketOpportunityDetail =
    data?.market_opportunity && typeof data.market_opportunity === 'object'
      ? data.market_opportunity
      : null;
  const hero = data ? buildHotpostSurfaceHero(data) : null;
  const decisionSummary = data ? buildHotpostDecisionSummary(data) : null;
  const actionPlan = data ? buildHotpostActionPlan(data) : null;
  const modeLabel = hero?.eyebrow ?? data?.mode ?? '快反结果';
  const midReviewSteps =
    data?.mode === 'rant' ? ['先看原话', '再看骂点', '最后再决定要不要下结论'] : ['先看摘要', '再扫证据', '最后看社区'];
  const loadingSteps = ['先抓摘要', '再抓证据', '最后看社区'];
  const summaryText = pickHotpostSummary(data);
  const evidenceQuotes = collectHotpostEvidenceQuotes(data);
  const complaintFacets = data?.complaint_facets ?? [];
  const rantRepresentativePosts = data?.mode === 'rant' ? collectRantRepresentativePosts(data) : [];
  const evidencePosts = data?.mode === 'rant' ? rantRepresentativePosts : data?.top_posts ?? [];
  const rangeNote = pickHotpostRangeNote(data);
  const recommendedActions = data?.next_steps?.recommended_actions?.filter(Boolean).slice(0, 3) ?? [];
  const suggestedKeywords = data?.next_steps?.suggested_keywords?.filter(Boolean).slice(0, 4) ?? [];
  const visibleTopics = data?.topics ? (showAllTopics ? data.topics : data.topics.slice(0, 3)) : [];
  const visibleEvidencePosts = showAllEvidence ? evidencePosts : evidencePosts.slice(0, 3);
  const queryParseEntries = data?.query_parse
    ? [
        data.query_parse.subject ? { label: '对象', value: data.query_parse.subject } : null,
        data.query_parse.compare_target ? { label: '对比方', value: data.query_parse.compare_target } : null,
        data.query_parse.focus ? { label: '关注点', value: data.query_parse.focus } : null,
        data.query_parse.scenario ? { label: '场景', value: data.query_parse.scenario } : null,
      ].filter((item): item is { label: string; value: string } => Boolean(item?.value))
    : [];
  const hasRantInsights =
    data?.mode === 'rant' &&
    (complaintFacets.length > 0 ||
      (data.pain_points?.length ?? 0) > 0 ||
      (data.competitor_mentions?.length ?? 0) > 0 ||
      Boolean(data.migration_intent));
  const compareFacetTargets = Array.from(
    new Set(complaintFacets.map((facet) => facet.target).filter((target): target is string => Boolean(target))),
  );
  const compareGroups =
    data?.mode === 'rant' && data.render_mode === 'compare' && compareFacetTargets.length >= 2
      ? [
          { title: `为什么更偏向 ${compareFacetTargets[0]}`, facets: complaintFacets.filter((facet) => facet.target === compareFacetTargets[0]) },
          { title: `为什么会嫌弃 ${compareFacetTargets[1]}`, facets: complaintFacets.filter((facet) => facet.target === compareFacetTargets[1]) },
        ]
      : [];
  const hasExpandableInsights =
    data?.mode === 'opportunity' &&
    ((unmetNeeds?.length ?? 0) > 0 ||
      (data.user_segments?.length ?? 0) > 0 ||
      (data.existing_tools?.length ?? 0) > 0);

  const handleSSEEvent = useCallback((event: SSEEvent) => {
    if (event.event === 'queue_update') {
      const payload = event as SSEQueueUpdateEvent;
      setStatus('queued');
      setQueuePosition(payload.position);
      setEstimatedWait(payload.estimated_wait_seconds);
    } else if (event.event === 'progress') {
       setStatus('loading'); // or 'processing'
       setQueuePosition(undefined);
    } else if (event.event === 'completed') {
       // Fetch final data
       if (queryId) {
           getHotPostResult(queryId).then(res => {
               setData(res);
               setStatus('success');
               sseClientRef.current?.disconnect();
           }).catch(e => {
               console.error("Failed to fetch completed result", e);
               setStatus('error');
               setErrorMsg(toUserFacingHotpostError());
           });
       }
    }
  }, [queryId]);

  const startStream = useCallback(() => {
    if (!queryId) return;
    if (sseClientRef.current) return; // Already connected

    console.log("Starting SSE stream for", queryId);
    sseClientRef.current = subscribeToHotPostStream(
        queryId,
        handleSSEEvent,
        (status) => {
            console.log("SSE Status:", status);
            if (status === 'failed' || status === 'closed') {
                 // Maybe fallback to polling if SSE fails hard?
                 // For now, let's rely on the internal reconnect of SSEClient
            }
        }
    );
  }, [queryId, handleSSEEvent]);

  // Polling Logic
  const fetchResult = useCallback(async () => {
    if (!queryId) return;
    try {
      const result = await getHotPostResult(queryId);

      // Backend status handling
      if (result.status === 'queued' || result.status === 'processing') {
         // Keep loading, useEffect will trigger next poll
      } else {
        setData(result);
        setStatus('success');
      }
    } catch (err: any) {
       console.error("Poll error:", err);
       setStatus('error');
       setErrorMsg(toUserFacingHotpostError());
    }
  }, [queryId]);

  // Initial Fetch & Logic
  useEffect(() => {
    if (!queryId) return;

    let isActive = true;

    const init = async () => {
        try {
            const res = await getHotPostResult(queryId);
            if (!isActive) return;

            if (res.status === 'queued' || res.status === 'processing') {
                setStatus('queued');
                setQueuePosition(res.position);
                setEstimatedWait(res.estimated_wait_seconds);
                startStream();
            } else {
                setData(res);
                setStatus('success');
            }
        } catch (e: any) {
            console.error("Initial fetch failed", e);
            setStatus('error');
            setErrorMsg(toUserFacingHotpostError());
        }
    };

    init();

    return () => {
        isActive = false;
        if (sseClientRef.current) {
            sseClientRef.current.disconnect();
            sseClientRef.current = null;
        }
    };
  }, [queryId, startStream]);


  const handleDeepDive = async () => {
    if (!isAuthenticated()) {
        setIsAuthDialogOpen(true);
        return;
    }
    if (!data) return;

    setIsGeneratingDeepDive(true);
    try {
        const seed_subreddits = data.communities?.map(c => typeof c === 'string' ? c : c.name) || [];
        await generateDeepDiveToken({
            query_id: data.query_id,
            product_desc: data.query,
            seed_subreddits
        });

        navigate('/', {
          state: {
            prefillProductDescription: data.query,
            prefillSource: 'hotpost-deepdive',
            prefillHint: '已带回这次热点方向。补成完整产品描述后，直接继续深挖。',
          },
        });
    } catch (e: any) {
        alert('系统刚才没把深度报告接上，先稍后再试一次。');
    } finally {
        setIsGeneratingDeepDive(false);
    }
  };

  const handleRetrySearch = useCallback(() => {
    if (!data) {
      navigate('/hotpost');
      return;
    }

    navigate('/hotpost', {
      state: {
        prefillQuery: data.query,
        prefillMode: data.mode,
        prefillQueryParse: data.query_parse,
        prefillSource: 'retry-search',
        prefillHint: '已带回这次搜索方向。改关键词或补社区后，直接重扫。',
      },
    });
  }, [data, navigate]);

  const handleReviewEvidence = useCallback(() => {
    evidenceSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  // --- Render ---

  if (status === 'queued') {
      return <QueueOverlay
        position={queuePosition !== undefined ? queuePosition : undefined}
        estimatedWait={estimatedWait !== undefined ? estimatedWait : undefined}
      />;
  }

  if (status === 'loading' && !data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="w-full max-w-2xl rounded-2xl border border-border bg-card p-8 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
            </div>
            <div>
              <div className="text-sm font-semibold text-primary">快扫进行中</div>
              <h2 className="text-2xl font-bold text-foreground">这波热点正在成型</h2>
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-muted-foreground">系统正在整理摘要、证据和社区。</p>

          <div className="mt-4 flex flex-wrap gap-2">
            {loadingSteps.map((step) => (
              <span
                key={step}
                className="inline-flex items-center rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground"
              >
                {step}
              </span>
            ))}
          </div>

          <div className="mt-5 h-2 overflow-hidden rounded-full bg-muted">
            <div className="h-full w-1/3 animate-[loading_2s_ease-in-out_infinite] rounded-full bg-primary" />
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error' || !data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-2xl">
          <ProductStatePanel
            tone="error"
            title="这次快扫还在整理中"
            description={errorMsg || toUserFacingHotpostError()}
            nextStep="先重试一次；还不行就换关键词，回搜索页重扫。"
            actions={[
              {
                label: '重新扫描',
                onClick: () => {
                  setStatus('loading');
                  setPollingAttempt(0);
                  fetchResult();
                },
                tone: 'primary',
              },
              { label: '回搜索页重扫', onClick: handleRetrySearch },
            ]}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <header className="surface-header sticky top-0 z-10 border-b border-border shadow-sm">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              type="button"
              aria-label="返回热点搜索页"
              onClick={() => navigate('/hotpost')}
              className="surface-action-secondary rounded-full p-2 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-muted-foreground" />
            </button>
            <div>
               <div className="surface-section-kicker mb-1">Hotpost Desk</div>
               <div className="flex items-center space-x-2">
                 <h1 className="text-lg font-semibold text-foreground">{data.query}</h1>
                 <span className="rounded-full border border-secondary/12 bg-secondary px-2.5 py-1 text-[11px] font-medium uppercase text-secondary-foreground">
                    {modeLabel}
                 </span>
               </div>
               <div className="text-xs text-muted-foreground">
                 {new Date(data.search_time).toLocaleString()} • {data.from_cache ? '最近一次扫描' : '刚刚扫描'}
               </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
             <button
               type="button"
               aria-label="重新加载当前热点结果"
               onClick={() => { window.location.reload(); }}
               className="surface-action-secondary rounded-full p-2 text-muted-foreground transition-colors hover:text-primary"
               title="刷新"
             >
                <RefreshCw className="w-5 h-5" />
             </button>
             <button
                type="button"
                onClick={handleDeepDive}
                disabled={isGeneratingDeepDive}
                className="surface-action-primary hidden h-9 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors sm:inline-flex"
             >
                {isGeneratingDeepDive ? '准备中…' : '继续深挖'}
                <Zap className="w-3 h-3 ml-2 text-yellow-400" />
             </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-5xl space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
        {data.mode === 'rant' && evidenceQuotes.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center text-foreground">
              <MessageSquare className="w-5 h-5 mr-2 text-primary" />
              真实原话
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {evidenceQuotes.map((item, index) => {
                const quoteTime = formatHotpostEvidenceTime(item.createdUtc);
                const content = (
                  <div className="surface-panel-muted rounded-2xl p-4 transition-shadow hover:shadow-editorial">
                    <p className="text-sm leading-7 text-foreground italic">“{item.quote}”</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.subreddit ? `来源：${item.subreddit}` : '来源：证据帖原话'}</span>
                      {quoteTime ? <span>时间：{quoteTime}</span> : null}
                      {item.url ? (
                        <span className="inline-flex items-center gap-1 text-primary">
                          <ExternalLink className="h-3.5 w-3.5" />
                          查看原帖
                        </span>
                      ) : null}
                    </div>
                  </div>
                );

                if (item.url) {
                  return (
                    <a
                      key={`${item.quote}-${index}`}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block"
                    >
                      {content}
                    </a>
                  );
                }

                return <div key={`${item.quote}-${index}`}>{content}</div>;
              })}
            </div>
          </section>
        )}

        {hero ? <SurfaceHero {...hero} /> : null}

        {decisionSummary && data.mode !== 'rant' ? (
          <DecisionSummaryPanel
            title="先定追不追"
            verdictTitle={decisionSummary.verdictTitle}
            verdictDescription={decisionSummary.verdictDescription}
            reasons={decisionSummary.reasons}
            signals={decisionSummary.signals}
            nextStepDescription={decisionSummary.nextStepDescription}
            actions={
              actionPlan
                ? [
                    {
                      label: actionPlan.primaryLabel,
                      onClick: actionPlan.primaryIntent === 'generate-deep-dive' ? handleDeepDive : handleReviewEvidence,
                      tone: 'primary',
                    },
                    {
                      label: actionPlan.secondaryLabel,
                      onClick: actionPlan.secondaryIntent === 'review-evidence' ? handleReviewEvidence : handleRetrySearch,
                    },
                    ...(actionPlan.tertiaryLabel
                      ? [{ label: actionPlan.tertiaryLabel, onClick: handleRetrySearch }]
                      : []),
                  ]
                : []
            }
          />
        ) : null}

        {/* Summary Card */}
        {data.mode !== 'rant' ? (
        <section className="surface-panel rounded-[28px] p-6">
           <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-4">
              <div>
                <div className="surface-section-kicker mb-2">快扫主判断</div>
                <h2 className="text-xl font-semibold flex items-center">
                 <BarChart2 className="w-5 h-5 mr-2 text-primary" aria-hidden="true" />
                 这页先看三件事
                </h2>
              </div>
              <ConfidenceBadge level={data.confidence} count={data.evidence_count} />
           </div>
           <div className="mb-4 flex flex-wrap gap-2">
             {midReviewSteps.map((step) => (
               <span
                 key={step}
                 className="surface-chip inline-flex items-center rounded-full px-3 py-1 text-xs font-medium text-muted-foreground"
               >
                 {step}
               </span>
             ))}
           </div>

           {/* Market Opportunity Highlight (For Opportunity Mode) */}
           {data.mode === 'opportunity' && marketOpportunityText && (
               <div className="mb-4 rounded-2xl border border-primary/15 bg-primary/10 p-4">
                   <h3 className="text-sm font-bold text-yellow-800 uppercase mb-1 flex items-center">
                       <Target className="w-4 h-4 mr-1" /> 市场机会
                   </h3>
                   <p className="text-yellow-900 font-medium">{marketOpportunityText}</p>
                   {marketOpportunityDetail && (
                     <div className="mt-2 text-xs text-yellow-900/80 space-y-1">
                       {marketOpportunityDetail.target_user && <div>目标用户：{marketOpportunityDetail.target_user}</div>}
                       {marketOpportunityDetail.pricing_hint && <div>定价提示：{marketOpportunityDetail.pricing_hint}</div>}
                       {marketOpportunityDetail.gtm_channel && <div>渠道建议：{marketOpportunityDetail.gtm_channel}</div>}
                     </div>
                   )}
               </div>
           )}

           <p className="text-base leading-7 text-foreground md:text-lg">
              {summaryText}
           </p>
        </section>
        ) : null}

        {data.mode !== 'rant' && evidenceQuotes.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center text-foreground">
              <MessageSquare className="w-5 h-5 mr-2 text-primary" />
              代表原话
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {evidenceQuotes.map((item, index) => {
                const quoteTime = formatHotpostEvidenceTime(item.createdUtc);
                const content = (
                  <div className="surface-panel-muted rounded-2xl p-4 transition-shadow hover:shadow-editorial">
                    <p className="text-sm leading-7 text-foreground italic">“{item.quote}”</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.subreddit ? `来源：${item.subreddit}` : '来源：证据帖原话'}</span>
                      {quoteTime ? <span>时间：{quoteTime}</span> : null}
                    </div>
                  </div>
                );

                if (item.url) {
                  return (
                    <a
                      key={`${item.quote}-${index}`}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block"
                    >
                      {content}
                    </a>
                  );
                }

                return <div key={`${item.quote}-${index}`}>{content}</div>;
              })}
            </div>
          </section>
        )}

        {/* --- Trending Mode: Topics --- */}
        {data.mode === 'trending' && data.topics && data.topics.length > 0 && (
            <section className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center text-orange-700">
                    <TrendingUp className="w-5 h-5 mr-2" />
                    {showAllTopics || data.topics.length <= 3 ? '这波最热的话题' : '先看最热的 3 个话题'}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {visibleTopics.map((topic, idx) => (
                        <div key={idx} className="surface-panel-muted rounded-2xl p-4 transition-shadow hover:shadow-editorial">
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex items-center gap-2">
                                    <span className="bg-orange-100 text-orange-700 text-xs font-bold px-2 py-1 rounded-full">#{topic.rank}</span>
                                    <h4 className="font-semibold">{toHotpostTopicTitle(topic.topic, topic.rank)}</h4>
                                </div>
                                <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">{normalizeTrendLabel(topic.time_trend)}</span>
                            </div>
                            <p className="text-sm text-foreground mb-3">
                              {toHotpostReadableText(
                                topic.key_takeaway,
                                '这个话题正在升温，建议先看证据再判断要不要继续追。'
                              )}
                            </p>

                            {/* Evidence Links */}
                            <div className="space-y-2 border-t pt-2 border-dashed border-border">
                                {topic.evidence.slice(0, 2).map((ev, i) => (
                                    <a key={i} href={ev.url} target="_blank" rel="noopener noreferrer" className="block text-xs text-muted-foreground hover:text-primary truncate">
                                        <FileText className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" />{ev.title} ({ev.score})
                                    </a>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
                {data.topics.length > 3 ? (
                  <button
                    type="button"
                    onClick={() => setShowAllTopics((prev) => !prev)}
                    className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
                  >
                    {showAllTopics ? '收起话题' : `查看更多话题（${data.topics.length - 3}）`}
                  </button>
                ) : null}
            </section>
        )}

        {hasExpandableInsights ? (
          <section className="surface-panel-muted rounded-2xl p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">补充细节（可选）</h3>
                <p className="mt-1 text-sm text-muted-foreground">默认看主结论；需要时再展开。</p>
              </div>
              <button
                type="button"
                onClick={() => setShowAdvancedInsights((prev) => !prev)}
                className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
              >
                {showAdvancedInsights ? '收起补充细节' : '展开补充细节'}
              </button>
            </div>
          </section>
        ) : null}

        {/* --- Rant Mode: Voice Facets --- */}
        {hasRantInsights && data.mode === 'rant' && complaintFacets.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center text-red-700">
              <Frown className="w-5 h-5 mr-2" />
              {data.render_mode === 'compare' ? '大家为什么偏向一边、嫌弃另一边' : '原话里反复出现的具体骂点'}
            </h3>
            {compareGroups.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {compareGroups.map((group) => (
                  <div key={group.title} className="surface-panel-muted rounded-2xl p-4 space-y-3">
                    <h4 className="font-semibold text-foreground">{group.title}</h4>
                    <div className="space-y-3">
                      {group.facets.map((facet, idx) => (
                        <div key={`${group.title}-${facet.label}-${idx}`} className="rounded-xl border border-border bg-background/80 p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="font-medium text-red-900">{facet.label}</div>
                            <span className="text-xs text-muted-foreground">{facet.evidence_count ?? 0} 条证据</span>
                          </div>
                          {facet.representative_quote ? (
                            <p className="mt-2 text-sm leading-6 text-foreground italic">“{facet.representative_quote}”</p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {complaintFacets.map((facet, idx) => (
                  <div key={`${facet.label}-${idx}`} className="surface-panel-muted rounded-2xl p-4 transition-shadow hover:shadow-editorial">
                    <div className="flex justify-between items-start gap-3">
                      <h4 className="font-semibold text-red-900">{facet.label}</h4>
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                        {facet.evidence_count ?? 0} 条证据
                      </span>
                    </div>
                    {facet.target ? (
                      <div className="mt-2 text-xs text-muted-foreground">对象：{facet.target}</div>
                    ) : null}
                    <div className="mt-3 text-sm text-foreground bg-muted/50 p-3 rounded-xl italic">
                      “{facet.representative_quote || '这轮原话还不够密，先继续看下面的代表帖子。'}”
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {hasRantInsights && data.mode === 'rant' && complaintFacets.length === 0 && data.pain_points && data.pain_points.length > 0 && (
          <section className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center text-red-700">
              <Frown className="w-5 h-5 mr-2" />
              用户到底在骂什么
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.pain_points.map((pp, idx) => (
                <div key={idx} className="surface-panel-muted rounded-2xl p-4 transition-shadow hover:shadow-editorial">
                  <div className="flex justify-between items-start">
                    <h4 className="font-semibold text-red-900">{pp.category}</h4>
                    <span
                      className={clsx(
                        'px-2 py-0.5 rounded text-xs font-bold uppercase',
                        pp.severity === 'high'
                          ? 'bg-red-100 text-red-700'
                          : pp.severity === 'medium'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-blue-100 text-blue-800',
                      )}
                    >
                      {pp.severity || 'low'}
                    </span>
                  </div>
                  <p className="text-sm text-foreground mt-2">
                    {pp.description || pp.user_voice || '先把这类用户声音当成一个方向判断，系统会继续补一句更完整的概括。'}
                  </p>
                  <div className="mt-3 text-xs text-muted-foreground bg-muted/50 p-2 rounded italic">
                    "{pickHotpostQuote(pp.sample_quotes?.[0], pp.user_voice, ...(pp.evidence ?? []).map((evidence) => evidence.key_quote)) || '这类原话会在继续深挖时自动补齐。'}"
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {data.mode === 'rant' && queryParseEntries.length > 0 ? (
          <section className="surface-panel-muted rounded-2xl p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">这次系统理解成了什么</h3>
                <p className="mt-1 text-sm text-muted-foreground">这些标签会直接影响检索方向；不对就回搜索页改。</p>
              </div>
              <button
                type="button"
                onClick={handleRetrySearch}
                className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
              >
                调整搜索标签
              </button>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {queryParseEntries.map((entry) => (
                <span
                  key={`${entry.label}-${entry.value}`}
                  className="surface-chip inline-flex items-center rounded-full px-3 py-1 text-xs font-medium text-muted-foreground"
                >
                  {entry.label}：{entry.value}
                </span>
              ))}
            </div>
          </section>
        ) : null}

        {decisionSummary && data.mode === 'rant' ? (
          <DecisionSummaryPanel
            title="再决定要不要继续追"
            verdictTitle={decisionSummary.verdictTitle}
            verdictDescription={decisionSummary.verdictDescription}
            reasons={decisionSummary.reasons}
            signals={decisionSummary.signals}
            nextStepDescription={decisionSummary.nextStepDescription}
            actions={
              actionPlan
                ? [
                    {
                      label: actionPlan.primaryLabel,
                      onClick: actionPlan.primaryIntent === 'generate-deep-dive' ? handleDeepDive : handleReviewEvidence,
                      tone: 'primary',
                    },
                    {
                      label: actionPlan.secondaryLabel,
                      onClick: actionPlan.secondaryIntent === 'review-evidence' ? handleReviewEvidence : handleRetrySearch,
                    },
                    ...(actionPlan.tertiaryLabel
                      ? [{ label: actionPlan.tertiaryLabel, onClick: handleRetrySearch }]
                      : []),
                  ]
                : []
            }
          />
        ) : null}

        {data.mode === 'rant' ? (
          <section className="surface-panel rounded-[28px] p-6">
            <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-4">
              <div>
                <div className="surface-section-kicker mb-2">轻梳理</div>
                <h2 className="text-xl font-semibold flex items-center">
                  <BarChart2 className="w-5 h-5 mr-2 text-primary" aria-hidden="true" />
                  {data.render_mode === 'quote_only' ? '这轮先不给重结论' : '这轮可以先记住这句'}
                </h2>
              </div>
              <ConfidenceBadge level={data.confidence} count={data.evidence_count} />
            </div>
            <div className="mb-4 flex flex-wrap gap-2">
              {midReviewSteps.map((step) => (
                <span
                  key={step}
                  className="surface-chip inline-flex items-center rounded-full px-3 py-1 text-xs font-medium text-muted-foreground"
                >
                  {step}
                </span>
              ))}
            </div>
            <p className="text-base leading-7 text-foreground md:text-lg">{summaryText}</p>
          </section>
        ) : null}

        {/* Top Posts Section */}
        <section ref={evidenceSectionRef} className="space-y-4 pt-6 border-t border-dashed">
             <h3 className="font-bold text-lg flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                {data.mode === 'rant'
                  ? showAllEvidence || evidencePosts.length <= 3
                    ? '代表帖子'
                    : '先看前 3 条代表帖子'
                  : showAllEvidence || evidencePosts.length <= 3
                    ? '关键证据帖'
                    : '先看前 3 条关键证据'}
             </h3>
             {data.mode === 'rant' ? (
               <p className="text-sm text-muted-foreground">这些帖子直接支撑上面的骂点，不再混进泛讨论。</p>
             ) : null}
             <div className="grid grid-cols-1 gap-4">
                 {visibleEvidencePosts.length > 0 ? (
                    visibleEvidencePosts.map((post) => (
                        <PostCard key={post.id} post={post} />
                    ))
                 ) : (
                    <ProductStatePanel
                      tone="empty"
                      compact
                      title="先顺着上面的判断继续走"
                      description="这轮快扫已经够你先判断值不值得追。"
                      nextStep={
                        data.next_steps?.deepdive_available
                          ? '觉得有价值就继续深挖。'
                          : '先换个更具体的关键词，或补几个贴近的社区。'
                      }
                      actions={
                        data.next_steps?.deepdive_available
                          ? [
                              { label: '继续深挖', onClick: handleDeepDive, tone: 'primary' },
                              { label: '回搜索页重扫', onClick: handleRetrySearch },
                            ]
                          : [{ label: '回搜索页重扫', onClick: handleRetrySearch, tone: 'primary' }]
                      }
                    />
                 )}
             </div>
             {evidencePosts.length > 3 ? (
               <button
                 type="button"
                 onClick={() => setShowAllEvidence((prev) => !prev)}
                 className="surface-action-secondary inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
               >
                 {showAllEvidence ? '收起证据' : `查看更多证据（${evidencePosts.length - 3}）`}
               </button>
             ) : null}
        </section>

        {/* --- Rant Mode: Competitors & Migration & Range --- */}
        {data.mode === 'rant' && hasRantInsights && (
            <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {data.competitor_mentions && data.competitor_mentions.length > 0 && (
                        <section className="space-y-3">
                             <h3 className="text-lg font-semibold flex items-center text-foreground">
                                <ShieldAlert className="w-5 h-5 mr-2" />
                                大家顺手会提到哪些竞品
                            </h3>
                            <div className="surface-panel-muted rounded-2xl p-4 space-y-3">
                                {data.competitor_mentions.map((comp, idx) => (
                                    <div key={idx} className="flex justify-between items-center border-b border-dashed border-border last:border-0 pb-2 last:pb-0">
                                        <span className="font-medium">{comp.name}</span>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-muted-foreground">{comp.mentions ?? '-'} 次提及</span>
                                            <span className={clsx("w-2 h-2 rounded-full",
                                                comp.sentiment === 'positive' ? 'bg-green-500' :
                                                comp.sentiment === 'negative' ? 'bg-red-500' : 'bg-gray-400'
                                            )} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {data.migration_intent && (
                         <section className="space-y-3">
                             <h3 className="font-bold text-lg flex items-center text-foreground">
                                <ArrowRight className="w-5 h-5 mr-2" />
                                有没有人已经想走
                            </h3>
                            <div className="bg-card border border-border rounded-lg p-4 space-y-4">
                                <div>
                                    <div className="flex justify-between text-sm mb-1"><span>已离开</span><span className="font-bold">{data.migration_intent.already_left || '0%'}</span></div>
                                    <div className="w-full bg-muted h-2 rounded-full"><div className="bg-red-500 h-2 rounded-full" style={{width: data.migration_intent.already_left || '0%'}} /></div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm mb-1"><span>考虑离开</span><span className="font-bold">{data.migration_intent.considering || '0%'}</span></div>
                                    <div className="w-full bg-muted h-2 rounded-full"><div className="bg-yellow-500 h-2 rounded-full" style={{width: data.migration_intent.considering || '0%'}} /></div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm mb-1"><span>无奈留守</span><span className="font-bold">{data.migration_intent.staying_reluctantly || '0%'}</span></div>
                                    <div className="w-full bg-muted h-2 rounded-full"><div className="bg-gray-500 h-2 rounded-full" style={{width: data.migration_intent.staying_reluctantly || '0%'}} /></div>
                                </div>
                            </div>
                        </section>
                    )}
                </div>

                {(rangeNote || recommendedActions.length > 0 || suggestedKeywords.length > 0) && (
                  <section className="space-y-4">
                    <h3 className="text-lg font-semibold flex items-center text-foreground">
                      <AlertTriangle className="w-5 h-5 mr-2 text-primary" />
                      范围说明与下一步
                    </h3>
                    <div className="surface-panel-muted rounded-2xl p-4 space-y-4">
                      {rangeNote ? (
                        <p className="text-sm leading-7 text-foreground">{rangeNote}</p>
                      ) : null}
                      {recommendedActions.length > 0 ? (
                        <div className="space-y-2">
                          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">建议先做这几步</div>
                          <div className="space-y-2">
                            {recommendedActions.map((item, index) => (
                              <div key={item} className="rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground">
                                {index + 1}. {item}
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {suggestedKeywords.length > 0 ? (
                        <div className="space-y-2">
                          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">继续追问可以先看这些词</div>
                          <div className="flex flex-wrap gap-2">
                            {suggestedKeywords.map((keyword) => (
                              <span
                                key={keyword}
                                className="inline-flex items-center rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground"
                              >
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </section>
                )}
            </>
        )}

        {/* --- Opportunity Mode: Needs, Segments, Tools --- */}
        {data.mode === 'opportunity' && showAdvancedInsights && (
             <>
                {unmetNeeds && unmetNeeds.length > 0 && (
                     <section className="space-y-4">
                        <h3 className="font-bold text-lg flex items-center text-yellow-600">
                            <Lightbulb className="w-5 h-5 mr-2" />
                            用户现在缺什么
                        </h3>
                        <div className="space-y-3">
                             {unmetNeeds.map((opp, idx) => (
                                <div key={idx} className="bg-card border border-yellow-100 rounded-lg p-4 flex flex-col sm:flex-row gap-4">
                                     <div className="flex-1">
                                         <h4 className="font-semibold text-foreground flex items-center">
                                             {opp.need || opp.summary || "未命名需求"}
                                             {opp.opportunity_signal === 'high' && <Zap className="w-4 h-4 text-yellow-500 ml-2 fill-current" />}
                                         </h4>
                                         <div className="flex gap-2 mt-2">
                                             {opp.me_too_count !== undefined && (
                                                 <span className="text-xs bg-yellow-50 text-yellow-700 px-2 py-1 rounded">共鸣: {opp.me_too_count} 人</span>
                                             )}
                                             {opp.mentions !== undefined && (
                                                <span className="text-xs bg-muted text-muted-foreground px-2 py-1 rounded">提及: {opp.mentions} 次</span>
                                             )}
                                         </div>
                                     </div>
                                     {opp.current_workarounds && opp.current_workarounds.length > 0 && (
                                        <div className="sm:w-1/3 text-sm text-muted-foreground border-l pl-4 border-dashed">
                                            <p className="font-medium text-xs uppercase text-gray-400 mb-1">当前凑合方案</p>
                                            <ul className="list-disc list-inside">
                                                {opp.current_workarounds.slice(0, 2).map((w, i) => {
                                                  const text = typeof w === 'string'
                                                    ? w
                                                    : [w.solution, w.pain].filter(Boolean).join(' - ');
                                                  return <li key={i}>{text}</li>;
                                                })}
                                            </ul>
                                        </div>
                                     )}
                                </div>
                             ))}
                        </div>
                     </section>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {data.user_segments && data.user_segments.length > 0 && (
                        <section className="space-y-3">
                             <h3 className="font-bold text-lg flex items-center text-foreground">
                                <Users className="w-5 h-5 mr-2" />
                                谁最着急
                            </h3>
                             <div className="bg-card border border-border rounded-lg p-4 space-y-4">
                                {data.user_segments.map((seg, idx) => (
                                    <div key={idx}>
                                        <h4 className="font-semibold text-primary mb-1">
                                          {seg.segment || seg.segment_name || '未命名用户'}
                                          {seg.percentage && <span className="text-xs text-muted-foreground ml-2">({seg.percentage})</span>}
                                        </h4>
                                        <p className="text-xs text-muted-foreground mb-2">
                                          {seg.core_need || seg.typical_profile || seg.price_sensitivity || ''}
                                        </p>
                                        {seg.needs && seg.needs.length > 0 && (
                                          <div className="flex flex-wrap gap-1">
                                            {seg.needs.map((n, i) => (
                                              <span key={i} className="px-2 py-0.5 bg-muted rounded text-[10px]">{n}</span>
                                            ))}
                                          </div>
                                        )}
                                    </div>
                                ))}
                             </div>
                        </section>
                    )}

                    {data.existing_tools && data.existing_tools.length > 0 && (
                        <section className="space-y-3">
                             <h3 className="font-bold text-lg flex items-center text-foreground">
                                <CheckCircle2 className="w-5 h-5 mr-2" />
                                用户现在拿什么凑合
                            </h3>
                            <div className="space-y-3">
                                {data.existing_tools.map((tool, idx) => (
                                    <div key={idx} className="bg-card border border-border rounded-lg p-3">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="font-bold">{tool.name}</span>
                                            <span className={clsx("text-xs px-2 py-0.5 rounded",
                                                tool.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                                                tool.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                                                'bg-slate-100 text-slate-700'
                                            )}>{summarizeSentiment(tool.sentiment)}</span>
                                        </div>
                                        {(tool.praised_for || tool.pros) && (tool.praised_for || tool.pros)!.length > 0 && (
                                          <div className="text-xs text-green-700">优势：{(tool.praised_for || tool.pros)?.join(', ')}</div>
                                        )}
                                        {(tool.criticized_for || tool.cons) && (tool.criticized_for || tool.cons)!.length > 0 && (
                                          <div className="text-xs text-red-700 mt-1">短板：{(tool.criticized_for || tool.cons)?.join(', ')}</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}
                </div>
             </>
        )}

        {/* Communities */}
        {data.communities && data.communities.length > 0 ? (
            <section className="border-t pt-6">
                <h3 className="text-lg font-bold text-foreground mb-2">这波主要出在哪些社区</h3>
                <p className="text-sm text-muted-foreground mb-3">先盯冒头社区，判断这波会不会继续放大。</p>
                <div className="flex flex-wrap gap-2">
                    {data.communities.map((c, idx) => {
                        const name = typeof c === 'string' ? c : c.name;
                        return (
                            <a
                                key={idx}
                                href={`https://reddit.com/${name}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center space-x-1 px-3 py-1.5 rounded-full border border-input bg-background hover:bg-accent text-sm transition-colors"
                            >
                                <span>{name}</span>
                                <ExternalLink className="w-3 h-3 text-muted-foreground" />
                            </a>
                        );
                    })}
                </div>
            </section>
        ) : (
          <section className="border-t pt-6">
            <ProductStatePanel
              tone="empty"
              compact
              title="先顺着这波判断继续追"
              description="这轮快扫已经够你先判断值不值得继续追。"
              nextStep="先看摘要和证据量；方向对就继续深挖。"
              actions={
                data.next_steps?.deepdive_available
                  ? [
                      { label: '继续深挖', onClick: handleDeepDive, tone: 'primary' },
                      { label: '回搜索页重扫', onClick: handleRetrySearch },
                    ]
                  : [{ label: '回搜索页重扫', onClick: handleRetrySearch, tone: 'primary' }]
              }
            />
          </section>
        )}

      </main>

      {/* Floating CTA for Mobile */}
      <div className="fixed bottom-6 right-6 sm:hidden">
         <button
            type="button"
            aria-label="继续深挖这次热点结果"
            onClick={handleDeepDive}
            className="surface-action-primary flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-colors"
            title="继续深挖"
         >
             <Zap className="w-6 h-6 text-yellow-400" />
         </button>
      </div>

      <AuthDialog
        isOpen={isAuthDialogOpen}
        onClose={() => setIsAuthDialogOpen(false)}
        defaultTab="login"
      />
    </div>
  );
};

export default HotPostResultPage;
