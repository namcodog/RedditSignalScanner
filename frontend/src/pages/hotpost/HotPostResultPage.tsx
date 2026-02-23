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

// --- Helper Components ---

const ConfidenceBadge: React.FC<{ level: ConfidenceLevel; count: number }> = ({ level, count }) => {
  const config = {
    high: { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircle2, label: '样本充足' },
    medium: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: AlertTriangle, label: '样本有限' },
    low: { color: 'bg-red-100 text-red-800 border-red-200', icon: AlertTriangle, label: '样本不足' },
    none: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: HelpCircle, label: '无数据' },
  };

  const { color, icon: Icon, label } = config[level] || config.none;

  return (
    <div className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', color)}>
      <Icon className="w-3 h-3 mr-1" />
      {label} ({count} 证据)
    </div>
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
          {post.body_preview}
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
        <div className="bg-card border border-border shadow-lg rounded-xl p-8 max-w-md w-full text-center space-y-6">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto animate-pulse">
                <Clock className="w-8 h-8 text-primary" />
            </div>
            <div>
                <h3 className="text-2xl font-bold text-foreground">正在排队中...</h3>
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

const DisclaimerBanner = () => (
  <div className="bg-amber-50 border-b border-amber-200 px-4 py-3 text-sm text-amber-800 flex items-center justify-center">
    <AlertTriangle className="w-4 h-4 mr-2" />
    <span>⚠️ 预览结果仅供参考，不代表最终市场结论。如需完整决策依据，请生成深度报告。</span>
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
               setErrorMsg("获取结果失败");
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
       setErrorMsg(err.message || '获取结果失败');
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
            setErrorMsg(e.message || "请求失败");
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
        const resp = await generateDeepDiveToken({
            query_id: data.query_id,
            product_desc: data.query, 
            seed_subreddits
        });
        
        navigate('/', { state: { deepDiveToken: resp.deepdive_token, productDescription: data.query } });
    } catch (e: any) {
        alert('生成深度报告失败: ' + e.message);
    } finally {
        setIsGeneratingDeepDive(false);
    }
  };

  // --- Render ---

  if (status === 'queued') {
      return <QueueOverlay 
        position={queuePosition !== undefined ? queuePosition : undefined} 
        estimatedWait={estimatedWait !== undefined ? estimatedWait : undefined} 
      />;
  }

  if (status === 'loading' && !data) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        <p className="text-muted-foreground">正在扫描 Reddit 社区...</p>
      </div>
    );
  }

  if (status === 'error' || !data) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 text-center">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-bold">抱歉，未找到相关结果</h2>
        <p className="text-muted-foreground mt-2">{errorMsg || '请稍后重试或更换关键词'}</p>
        <div className="flex gap-4 mt-6">
            <button
               onClick={() => { setStatus('loading'); setPollingAttempt(0); fetchResult(); }}
               className="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              重试
            </button>
            <button
               onClick={() => navigate('/hotpost')}
               className="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4"
            >
              返回搜索
            </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      <DisclaimerBanner />

      {/* Header */}
      <header className="border-b border-border bg-card sticky top-0 z-10 shadow-sm">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button onClick={() => navigate('/hotpost')} className="p-2 hover:bg-accent rounded-full transition-colors">
              <ArrowLeft className="w-5 h-5 text-muted-foreground" />
            </button>
            <div>
               <div className="flex items-center space-x-2">
                 <h1 className="text-lg font-bold text-foreground">{data.query}</h1>
                 <span className="px-2 py-0.5 rounded text-xs font-medium uppercase bg-secondary text-secondary-foreground">
                    {data.mode}
                 </span>
               </div>
               <div className="text-xs text-muted-foreground">
                 {new Date(data.search_time).toLocaleString()} • {data.from_cache ? 'From Cache' : 'Live Search'}
               </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
             <button
               onClick={() => { window.location.reload(); }}
               className="p-2 text-muted-foreground hover:text-primary transition-colors"
               title="刷新"
             >
                <RefreshCw className="w-5 h-5" />
             </button>
             <button
                onClick={handleDeepDive}
                disabled={isGeneratingDeepDive}
                className="hidden sm:inline-flex items-center justify-center rounded-md text-sm font-medium bg-black text-white hover:bg-black/90 h-9 px-4 shadow-sm"
             >
                {isGeneratingDeepDive ? '准备中...' : '生成深度报告'}
                <Zap className="w-3 h-3 ml-2 text-yellow-400" />
             </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-5xl space-y-6">

        {/* Summary Card */}
        <section className="bg-card border border-border rounded-xl p-6 shadow-sm">
           <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-4">
              <h2 className="text-xl font-bold flex items-center">
                 <BarChart2 className="w-5 h-5 mr-2 text-primary" />
                 核心洞察
              </h2>
              <ConfidenceBadge level={data.confidence} count={data.evidence_count} />
           </div>
           
           {/* Market Opportunity Highlight (For Opportunity Mode) */}
           {data.mode === 'opportunity' && marketOpportunityText && (
               <div className="mb-4 p-4 bg-yellow-50 border border-yellow-100 rounded-lg">
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

           <p className="text-foreground leading-relaxed text-lg">
              {data.summary || "暂无摘要"}
           </p>

            {/* Stats / Sentiment */}
            {data.sentiment_overview && (
                <div className="mt-6">
                    <div className="flex items-center space-x-1 h-2 rounded-full overflow-hidden bg-muted">
                        <div className="h-full bg-green-500" style={{ width: `${(data.sentiment_overview.positive * 100).toFixed(0)}%` }} title="Positive" />
                        <div className="h-full bg-gray-300" style={{ width: `${(data.sentiment_overview.neutral * 100).toFixed(0)}%` }} title="Neutral" />
                        <div className="h-full bg-red-500" style={{ width: `${(data.sentiment_overview.negative * 100).toFixed(0)}%` }} title="Negative" />
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground mt-2">
                        <span>Positive: {((data.sentiment_overview?.positive ?? 0) * 100).toFixed(0)}%</span>
                        <span>Negative: {((data.sentiment_overview?.negative ?? 0) * 100).toFixed(0)}%</span>
                    </div>
                </div>
            )}
        </section>

        {/* --- Trending Mode: Topics --- */}
        {data.mode === 'trending' && data.topics && data.topics.length > 0 && (
            <section className="space-y-4">
                <h3 className="font-bold text-lg flex items-center text-orange-600">
                    <TrendingUp className="w-5 h-5 mr-2" />
                    热门话题 (Trending Topics)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {data.topics.map((topic, idx) => (
                        <div key={idx} className="bg-card border border-orange-100 rounded-lg p-4 hover:shadow-md transition-shadow">
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex items-center gap-2">
                                    <span className="bg-orange-100 text-orange-700 text-xs font-bold px-2 py-1 rounded-full">#{topic.rank}</span>
                                    <h4 className="font-semibold">{topic.topic}</h4>
                                </div>
                                <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">{topic.time_trend}</span>
                            </div>
                            <p className="text-sm text-foreground mb-3">{topic.key_takeaway}</p>
                            
                            {/* Evidence Links */}
                            <div className="space-y-2 border-t pt-2 border-dashed border-border">
                                {topic.evidence.slice(0, 2).map((ev, i) => (
                                    <a key={i} href={ev.url} target="_blank" rel="noopener noreferrer" className="block text-xs text-muted-foreground hover:text-primary truncate">
                                        📄 {ev.title} ({ev.score})
                                    </a>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        )}

        {/* --- Rant Mode: Pain Points & Competitors & Migration --- */}
        {data.mode === 'rant' && (
            <>
                {data.pain_points && data.pain_points.length > 0 && (
                     <section className="space-y-4">
                        <h3 className="font-bold text-lg flex items-center text-red-600">
                            <Frown className="w-5 h-5 mr-2" />
                            核心痛点 (Pain Points)
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {data.pain_points.map((pp, idx) => (
                                <div key={idx} className="bg-card border border-red-100 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                                    <div className="flex justify-between items-start">
                                        <h4 className="font-semibold text-red-900">{pp.category}</h4>
                                        <span className={clsx("px-2 py-0.5 rounded text-xs font-bold uppercase",
                                            pp.severity === 'high' ? 'bg-red-100 text-red-700' :
                                            pp.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                            'bg-blue-100 text-blue-800'
                                        )}>{pp.severity || 'low'}</span>
                                    </div>
                                    <p className="text-sm text-foreground mt-2">{pp.description || pp.user_voice || '暂无描述'}</p>
                                    <div className="mt-3 text-xs text-muted-foreground bg-muted/50 p-2 rounded italic">
                                        "{(pp.sample_quotes && pp.sample_quotes[0]) || pp.user_voice || '暂无引用'}"
                                    </div>
                                </div>
                            ))}
                        </div>
                     </section>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {data.competitor_mentions && data.competitor_mentions.length > 0 && (
                        <section className="space-y-3">
                             <h3 className="font-bold text-lg flex items-center text-foreground">
                                <ShieldAlert className="w-5 h-5 mr-2" />
                                竞品提及
                            </h3>
                            <div className="bg-card border border-border rounded-lg p-4 space-y-3">
                                {data.competitor_mentions.map((comp, idx) => (
                                    <div key={idx} className="flex justify-between items-center border-b border-dashed border-border last:border-0 pb-2 last:pb-0">
                                        <span className="font-medium">{comp.name}</span>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-muted-foreground">{comp.mentions ?? '-'} mentions</span>
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
                                用户流失意向
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
            </>
        )}

        {/* --- Opportunity Mode: Needs, Segments, Tools --- */}
        {data.mode === 'opportunity' && (
             <>
                {unmetNeeds && unmetNeeds.length > 0 && (
                     <section className="space-y-4">
                        <h3 className="font-bold text-lg flex items-center text-yellow-600">
                            <Lightbulb className="w-5 h-5 mr-2" />
                            未满足需求 (Unmet Needs)
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
                                                  // @ts-ignore: Handle mixed type
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
                                目标人群
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
                                现有工具评价
                            </h3>
                            <div className="space-y-3">
                                {data.existing_tools.map((tool, idx) => (
                                    <div key={idx} className="bg-card border border-border rounded-lg p-3">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="font-bold">{tool.name}</span>
                                            <span className={clsx("text-xs px-2 py-0.5 rounded", 
                                                tool.sentiment === 'positive' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                            )}>{tool.sentiment}</span>
                                        </div>
                                        {(tool.praised_for || tool.pros) && (tool.praised_for || tool.pros)!.length > 0 && (
                                          <div className="text-xs text-green-700">👍 {(tool.praised_for || tool.pros)?.join(', ')}</div>
                                        )}
                                        {(tool.criticized_for || tool.cons) && (tool.criticized_for || tool.cons)!.length > 0 && (
                                          <div className="text-xs text-red-700 mt-1">👎 {(tool.criticized_for || tool.cons)?.join(', ')}</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}
                </div>
             </>
        )}

        {/* Top Posts Section */}
        <section className="space-y-4 pt-6 border-t border-dashed">
             <h3 className="font-bold text-lg flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                热门讨论 (Top Evidence)
             </h3>
             <div className="grid grid-cols-1 gap-4">
                 {data.top_posts && data.top_posts.length > 0 ? (
                    data.top_posts.map((post) => (
                        <PostCard key={post.id} post={post} />
                    ))
                 ) : (
                    <div className="text-center py-8 text-muted-foreground">暂无帖子显示</div>
                 )}
             </div>
        </section>

        {/* Communities */}
        {data.communities && data.communities.length > 0 && (
            <section className="border-t pt-6">
                <h4 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">涉及社区</h4>
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
        )}

      </main>

      {/* Floating CTA for Mobile */}
      <div className="fixed bottom-6 right-6 sm:hidden">
         <button
            onClick={handleDeepDive}
            className="flex items-center justify-center rounded-full bg-black text-white h-14 w-14 shadow-lg hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black"
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