import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ThumbsUp, ThumbsDown } from 'lucide-react';
import { getDecisionUnits, submitDecisionUnitFeedback, type DecisionUnit } from '@/api/decision-units.api';
import { useToast } from '@/components/ui/toast';
import { ROUTES } from '@/router';

export default function DecisionUnitsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [units, setUnits] = useState<DecisionUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUnits();
  }, []);

  const fetchUnits = async () => {
    try {
      setLoading(true);
      const data = await getDecisionUnits({ limit: 50 });
      setUnits(data.items);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch decision units', err);
      setError('无法加载决策单元列表');
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (id: string, label: 'valuable' | 'worthless') => {
    try {
      await submitDecisionUnitFeedback(id, { label });
      toast.success('反馈提交成功');
      // Optimistically remove or update item? For now, just show toast.
    } catch (err) {
      toast.error('反馈提交失败');
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-card">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center space-x-3">
            <button onClick={() => navigate(ROUTES.HOME)} className="p-2 hover:bg-muted rounded-full">
              <ArrowLeft className="h-5 w-5" />
            </button>
            <h1 className="text-lg font-semibold">决策单元 (RLHF)</h1>
          </div>
        </div>
      </header>

      <main className="container py-8 px-4">
        {loading ? (
          <div className="text-center py-10">加载中...</div>
        ) : error ? (
          <div className="text-center py-10 text-destructive">{error}</div>
        ) : units.length === 0 ? (
          <div className="text-center py-10 text-muted-foreground">暂无决策单元</div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {units.map((unit) => (
              <div key={unit.id} className="border border-border rounded-lg p-4 bg-card shadow-sm">
                <div className="flex justify-between items-start mb-2">
                  <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs font-semibold uppercase">
                    {unit.signal_type}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(unit.created_at).toLocaleString()}
                  </span>
                </div>
                
                <h3 className="font-semibold text-lg mb-2">{unit.title}</h3>
                
                <div className="bg-muted/30 p-3 rounded-md mb-4 text-sm">
                  {unit.summary}
                </div>

                <div className="flex justify-between items-center">
                   <div className="flex gap-2">
                      <span className="text-xs text-muted-foreground">Confidence: {unit.confidence.toFixed(2)}</span>
                   </div>
                   <div className="flex gap-2">
                     <button 
                        onClick={() => handleFeedback(unit.id, 'valuable')}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-md hover:bg-green-100 hover:text-green-700 transition"
                     >
                       <ThumbsUp className="h-4 w-4" /> 有用
                     </button>
                     <button 
                        onClick={() => handleFeedback(unit.id, 'worthless')}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-md hover:bg-red-100 hover:text-red-700 transition"
                     >
                       <ThumbsDown className="h-4 w-4" /> 无用
                     </button>
                   </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
