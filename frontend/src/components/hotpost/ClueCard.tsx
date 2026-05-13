import React from 'react';
import clsx from 'clsx';
import { Bookmark, BookmarkCheck, ArrowUpRight } from 'lucide-react';
import type { ClueCard as ClueCardType } from '@/types/hotpostClues';

type Props = {
  clue: ClueCardType;
  onFavorite: (clue: ClueCardType) => void;
  onOpen: (sheet: 'validate' | 'write') => void;
};

const tagClass: Record<ClueCardType['primary_tag'], string> = {
  validate: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  write: 'bg-amber-50 text-amber-700 border-amber-200',
  both: 'bg-sky-50 text-sky-700 border-sky-200',
};

const ClueCard: React.FC<Props> = ({ clue, onFavorite, onOpen }) => (
  <article className="rounded-3xl border border-border bg-card p-5 shadow-sm">
    <div className="flex items-start justify-between gap-3">
      <div>
        <div className={clsx('inline-flex rounded-full border px-3 py-1 text-xs font-semibold', tagClass[clue.primary_tag])}>
          {clue.primary_tag === 'validate' ? '适合验证' : clue.primary_tag === 'write' ? '适合写' : '双用'}
        </div>
        <h3 className="mt-3 text-lg font-semibold text-foreground">{clue.title}</h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{clue.one_liner}</p>
      </div>
      <button type="button" aria-label="收藏" onClick={() => onFavorite(clue)} className="rounded-full border border-border p-2">
        {clue.favorited ? <BookmarkCheck className="h-4 w-4 text-primary" /> : <Bookmark className="h-4 w-4 text-muted-foreground" />}
      </button>
    </div>
    <div className="mt-4 space-y-2 text-sm text-muted-foreground">
      <p>谁在说：{clue.audience}</p>
      <p>为什么值得看：{clue.why_now}</p>
    </div>
    <div className="mt-4 space-y-2">
      {clue.preview_quotes.map((quote) => (
        <div key={`${clue.id}-${quote.permalink}`} className="rounded-2xl bg-muted/50 px-4 py-3 text-sm leading-6 text-foreground">
          “{quote.text}”
          <div className="mt-1 text-xs text-muted-foreground">{quote.community}</div>
        </div>
      ))}
    </div>
    <div className="mt-4 flex flex-wrap gap-2">
      <button type="button" onClick={() => onOpen('validate')} className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background">
        拿去验证
      </button>
      <button type="button" onClick={() => onOpen('write')} className="rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground">
        拿去写
      </button>
      <a href={clue.hotpost_detail_url} className="inline-flex items-center gap-1 rounded-full px-3 py-2 text-sm text-muted-foreground">
        查看原话详情 <ArrowUpRight className="h-4 w-4" />
      </a>
    </div>
  </article>
);

export default ClueCard;
