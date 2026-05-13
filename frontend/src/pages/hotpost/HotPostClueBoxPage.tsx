import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ClueCard from '@/components/hotpost/ClueCard';
import { getClueBox, toggleClueFavorite } from '@/services/hotpostClues.service';
import type { ClueBoxTab, ClueCard as ClueCardType } from '@/types/hotpostClues';

const tabs: Array<{ key: ClueBoxTab; label: string }> = [
  { key: 'favorites', label: '我的收藏' },
  { key: 'copied', label: '最近复制' },
];

const HotPostClueBoxPage: React.FC = () => {
  const navigate = useNavigate();
  const [tab, setTab] = useState<ClueBoxTab>('favorites');
  const [items, setItems] = useState<ClueCardType[]>([]);

  useEffect(() => {
    getClueBox(tab).then((result) => setItems(result.items));
  }, [tab]);

  const onFavorite = async (clue: ClueCardType) => {
    const result = await toggleClueFavorite(clue.id, clue.favorited ? 'remove' : 'add');
    setItems((current) => current.map((item) => (item.id === clue.id ? { ...item, favorited: result.favorited } : item)));
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <button type="button" onClick={() => navigate('/hotpost')} className="text-sm text-muted-foreground">返回今日线索</button>
        <h1 className="mt-4 text-3xl font-bold text-foreground">我的线索箱</h1>
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

export default HotPostClueBoxPage;
