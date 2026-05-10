import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { getClueDetail, recordClueCopy, toggleClueFavorite } from '@/services/hotpostClues.service';
import type { ClueDetail } from '@/types/hotpostClues';

const HotPostClueDetailPage: React.FC = () => {
  const navigate = useNavigate();
  const { clueId = '' } = useParams();
  const [params] = useSearchParams();
  const [detail, setDetail] = useState<ClueDetail | null>(null);
  const sheet = params.get('sheet') === 'write' ? 'write' : 'validate';

  useEffect(() => {
    getClueDetail(clueId).then(setDetail);
  }, [clueId]);

  const activeSheet = useMemo(() => (sheet === 'write' ? detail?.content_sheet : detail?.validation_sheet), [detail, sheet]);

  if (!detail) return <div className="min-h-screen bg-background p-8 text-sm text-muted-foreground">线索加载中...</div>;

  const onFavorite = async () => {
    const result = await toggleClueFavorite(detail.id, detail.favorited ? 'remove' : 'add');
    setDetail({ ...detail, favorited: result.favorited });
  };

  const onCopy = async () => {
    if (!activeSheet) return;
    await navigator.clipboard.writeText(activeSheet.copy_payload);
    await recordClueCopy(detail.id, sheet);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-4 py-8">
        <button type="button" onClick={() => navigate('/hotpost')} className="text-sm text-muted-foreground">返回今日线索</button>
        <h1 className="mt-4 text-3xl font-bold text-foreground">{detail.title}</h1>
        <p className="mt-3 text-base leading-7 text-muted-foreground">{detail.one_liner}</p>
        <div className="mt-4 grid gap-2 rounded-3xl border border-border bg-card p-5 text-sm text-muted-foreground md:grid-cols-2">
          <p>谁在说：{detail.audience}</p>
          <p>为什么值得看：{detail.why_now}</p>
          <p>线程数：{detail.source_meta.thread_count}</p>
          <p>社区数：{detail.source_meta.community_count}</p>
        </div>
        <div className="mt-6 space-y-3">
          {detail.full_quotes.map((quote) => (
            <a key={quote.permalink} href={quote.permalink} target="_blank" rel="noreferrer" className="block rounded-2xl bg-muted/50 px-4 py-3 text-sm leading-6 text-foreground">
              “{quote.text}”
              <div className="mt-1 text-xs text-muted-foreground">{quote.community}</div>
            </a>
          ))}
        </div>
        {activeSheet && (
          <div className="mt-6 rounded-3xl border border-border bg-card p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold text-foreground">{sheet === 'write' ? '内容小抄' : '验证小抄'}</h2>
              <div className="flex gap-2">
                <button type="button" onClick={onFavorite} className="rounded-full border border-border px-4 py-2 text-sm">{detail.favorited ? '取消收藏' : '收藏'}</button>
                <button type="button" onClick={onCopy} className="rounded-full bg-foreground px-4 py-2 text-sm text-background">一键复制</button>
              </div>
            </div>
            <pre className="mt-4 whitespace-pre-wrap text-sm leading-7 text-foreground">{activeSheet.copy_payload}</pre>
          </div>
        )}
        <a href={detail.hotpost_detail_url} className="mt-6 inline-block text-sm text-primary">查看原话详情</a>
      </div>
    </div>
  );
};

export default HotPostClueDetailPage;
