import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ClueCard from '@/components/hotpost/ClueCard';
import NavigationBreadcrumb from '@/components/NavigationBreadcrumb';
import { listClues, toggleClueFavorite } from '@/services/hotpostClues.service';
import type { ClueCard as ClueCardType, ClueListTab } from '@/types/hotpostClues';

const tabs: Array<{ key: ClueListTab; label: string }> = [
  { key: 'all', label: '全部' },
  { key: 'validate', label: '验证' },
  { key: 'write', label: '写作' },
];

const HotPostCluesPage: React.FC = () => {
  const navigate = useNavigate();
  const [tab, setTab] = useState<ClueListTab>('all');
  const [items, setItems] = useState<ClueCardType[]>([]);

  useEffect(() => {
    listClues(tab).then((result) => setItems(result.items));
  }, [tab]);

  const onFavorite = async (clue: ClueCardType) => {
    const action = clue.favorited ? 'remove' : 'add';
    const result = await toggleClueFavorite(clue.id, action);
    setItems((current) => current.map((item) => (item.id === clue.id ? { ...item, favorited: result.favorited } : item)));
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <NavigationBreadcrumb items={[{ label: '首页', path: '/' }, { label: '线索' }]} />
        <div className="mt-6 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Hotpost Clues</p>
            <h1 className="mt-2 text-4xl font-bold text-foreground">今日线索</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">不是再看一条热点，而是直接拿走一张工作卡：值不值得试，先怎么试；值不值得写，先怎么写。</p>
          </div>
          <button type="button" onClick={() => navigate('/hotpost/box')} className="rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground">
            我的线索箱
          </button>
        </div>
        <div className="mt-6 flex gap-2">
          {tabs.map((item) => (
            <button key={item.key} type="button" onClick={() => setTab(item.key)} className={`rounded-full px-4 py-2 text-sm font-medium ${tab === item.key ? 'bg-foreground text-background' : 'border border-border text-foreground'}`}>
              {item.label}
            </button>
          ))}
        </div>
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {items.map((clue) => (
            <ClueCard key={clue.id} clue={clue} onFavorite={onFavorite} onOpen={(sheet) => navigate(`/hotpost/clues/${clue.id}?sheet=${sheet}`)} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default HotPostCluesPage;
