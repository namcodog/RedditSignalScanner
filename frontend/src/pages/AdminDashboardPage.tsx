import React, { useEffect, useState } from 'react';
import { getAdminDashboardStats, getRecentTasks, DashboardStats, TaskLedgerItem } from '@/api/admin.api';
import { Link, useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, BarChart3, Database, ShieldCheck } from 'lucide-react';
import SurfaceHero from '@/components/product/SurfaceHero';
import ProductStatePanel from '@/components/product/ProductStatePanel';
import { buildAdminSurfaceHero } from '@/lib/product-surface';

const AdminDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTasks, setRecentTasks] = useState<TaskLedgerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsData, tasksData] = await Promise.all([
          getAdminDashboardStats(),
          getRecentTasks({ limit: 5 })
        ]);
        setStats(statsData);
        setRecentTasks(tasksData.items);
      } catch (err: any) {
        console.error('Failed to load dashboard data', err);
        setError(err.message || '加载仪表盘数据失败');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) return <div className="p-8 text-center">正在加载仪表盘…</div>;
  if (error) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <ProductStatePanel
          tone="error"
          title="系统驾驶舱暂时没拿到最新状态"
          description={error}
          nextStep="先重新打开这页；如果还是失败，就优先去任务账本和监控页确认今天的机器是不是还在正常跑。"
          actions={[
            { label: '刷新仪表盘', onClick: () => window.location.reload(), tone: 'primary' },
            { label: '看任务账本', onClick: () => navigate('/admin/tasks/ledger') },
          ]}
        />
      </div>
    );
  }
  if (!stats) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <ProductStatePanel
          tone="empty"
          title="系统驾驶舱现在还没有可展示的数据"
          description="当前没有拿到可用的系统统计，这不一定是系统坏了，也可能只是今天还没人跑任务。"
          nextStep="先去任务账本看今天有没有新任务，再决定要不要继续排查。"
          actions={[{ label: '看任务账本', onClick: () => navigate('/admin/tasks/ledger'), tone: 'primary' }]}
        />
      </div>
    );
  }

  const hero = buildAdminSurfaceHero(stats, recentTasks);
  const statCards = [
    { label: '总用户数', value: String(stats.total_users), detail: '历史累计使用人数', icon: <Database className="h-5 w-5" aria-hidden="true" /> },
    { label: '累计任务', value: String(stats.total_tasks), detail: `今日新增 ${stats.tasks_today}`, icon: <BarChart3 className="h-5 w-5" aria-hidden="true" /> },
    { label: '平均处理耗时', value: `${stats.avg_processing_time}秒`, detail: '看今天整体跑得快不快', icon: <Activity className="h-5 w-5" aria-hidden="true" /> },
    { label: '缓存命中率', value: `${(stats.cache_hit_rate * 100).toFixed(1)}%`, detail: '越高说明重复分析越省时', icon: <ShieldCheck className="h-5 w-5" aria-hidden="true" /> },
  ];

  const systemRisk = stats.active_workers <= 0
    ? 'high'
    : stats.cache_hit_rate < 0.3
      ? 'medium'
      : 'low';
  const riskLabel = systemRisk === 'high' ? '高风险' : systemRisk === 'medium' ? '中风险' : '低风险';
  const riskColorClass = systemRisk === 'high' ? 'text-red-600' : systemRisk === 'medium' ? 'text-amber-600' : 'text-emerald-600';
  const recommendedAction =
    systemRisk === 'high'
      ? '先去任务账本确认失败链路，再看 worker 是否在线，今天先别开新任务。'
      : systemRisk === 'medium'
        ? '先盯缓存命中和平均耗时，确认没有继续恶化后再开新任务。'
        : '机器状态稳定，可以按计划开新任务，异常时再回控制面复核。';
  const failedTaskCount = recentTasks.filter((task) => task.status === 'failed').length;
  const runningTaskCount = recentTasks.filter((task) => task.status === 'processing' || task.status === 'pending').length;
  const completedTaskCount = recentTasks.filter((task) => task.status === 'completed').length;
  const queuePressureLabel = runningTaskCount >= 3 ? '偏高' : runningTaskCount > 0 ? '可控' : '空闲';
  const queuePressureClass =
    runningTaskCount >= 3 ? 'text-red-600' : runningTaskCount > 0 ? 'text-amber-600' : 'text-emerald-600';
  const opsPriority = failedTaskCount > 0
    ? {
        title: `先处理失败任务（${failedTaskCount} 条）`,
        description: '先看失败任务的共同原因，避免今天继续放大同类错误。',
      }
    : runningTaskCount > 0
      ? {
          title: `先盯在跑任务（${runningTaskCount} 条）`,
          description: '确认在跑任务没有卡住，再决定是否继续加新任务。',
        }
      : completedTaskCount > 0
        ? {
            title: `先抽查已完成任务（${completedTaskCount} 条）`,
            description: '先抽查最新完成的结果质量，再决定是否扩大执行。',
          }
        : {
            title: '先确认有没有新任务',
            description: '先去任务账本确认今天有没有新任务，再决定是否需要盯盘。',
          };

  // 状态映射辅助函数
  const getStatusText = (status: string) => {
    const map: Record<string, string> = {
      'pending': '等待中',
      'processing': '处理中',
      'completed': '已完成',
      'failed': '失败',
    };
    return map[status] || status;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="space-y-2">
        <div className="surface-section-kicker">Control Desk</div>
        <h1 className="text-3xl font-semibold text-foreground">系统控制面</h1>
        <p className="max-w-3xl text-sm leading-6 text-muted-foreground">先看机器稳不稳，再决定今天要不要继续开新任务。</p>
      </div>

      <SurfaceHero {...hero} />
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="surface-panel-muted rounded-[24px] p-5">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{card.label}</div>
              <div className="text-primary">{card.icon}</div>
            </div>
            <div className="surface-number mt-3 text-2xl font-semibold text-foreground">{card.value}</div>
            <div className="mt-1 text-xs text-muted-foreground">{card.detail}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Recent Tasks */}
        <div className="lg:col-span-2 space-y-6">
          <div className="surface-panel rounded-[28px]">
            <div className="flex items-center justify-between border-b border-border px-4 py-4">
              <div>
                <h3 className="text-lg font-semibold text-foreground">今天先看什么</h3>
                <p className="mt-1 text-xs text-muted-foreground">先看最近这批任务有没有顺利跑完，再决定今天需不需要继续盯盘。</p>
              </div>
              <Link to="/admin/tasks/ledger" className="surface-action-secondary inline-flex items-center rounded-xl px-3 py-2 text-sm font-medium transition-colors">看全部任务</Link>
            </div>
            <div className="divide-y divide-border">
              {recentTasks.map(task => (
                <div key={task.task_id} className="flex items-center justify-between p-4 transition-colors hover:bg-background/60">
                  <div>
                    <div className="font-medium text-foreground">任务 {task.task_id.substring(0, 8)}...</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {new Date(task.created_at).toLocaleString()} • {task.user_email}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-medium ${
                      task.status === 'completed' ? 'text-green-600' : 
                      task.status === 'failed' ? 'text-red-600' : 'text-yellow-600'
                    }`}>
                      {getStatusText(task.status)}
                    </div>
                    {task.posts_analyzed > 0 && <div className="surface-number mt-1 text-xs text-muted-foreground">{task.posts_analyzed} 帖子</div>}
                  </div>
                </div>
              ))}
              {recentTasks.length === 0 && (
                <div className="p-4">
                  <ProductStatePanel
                    tone="empty"
                    compact
                    title="当前还没有最近任务"
                    description="这不代表系统坏了，只是最近没有新的分析任务进来，或者这批任务还没开始跑。"
                    nextStep="先去任务账本确认今天有没有新任务，再回头看社区池和导入页。"
                    actions={[
                      { label: '看任务账本', onClick: () => navigate('/admin/tasks/ledger'), tone: 'primary' },
                      { label: '看社区池', onClick: () => navigate('/admin/communities/pool') },
                    ]}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: System & Actions */}
        <div className="space-y-6">
          <div className="surface-panel-muted rounded-[24px] p-4">
            <h3 className="text-lg font-semibold text-foreground mb-1">今天机器稳不稳</h3>
            <p className="mb-4 text-xs text-muted-foreground">这块只回答一个问题：今天这套机器稳不稳。</p>
            <div className="mb-3 flex items-center justify-between rounded-xl bg-background/80 px-3 py-2">
              <span className="text-sm text-muted-foreground">当前风险级别</span>
              <span className={`text-sm font-semibold ${riskColorClass}`}>{riskLabel}</span>
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">活跃节点 (Workers)</span>
              <span className={`surface-number font-bold ${stats.active_workers > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {stats.active_workers}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">今日完成任务</span>
              <span className="surface-number font-bold text-foreground">
                {stats.tasks_completed_today}
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-sm text-muted-foreground">队列压力（最近任务）</span>
              <span className={`text-sm font-semibold ${queuePressureClass}`}>{queuePressureLabel}</span>
            </div>
            <div className="mt-3 rounded-xl bg-background/80 px-3 py-3">
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">今日建议动作</div>
              <p className="mt-2 text-sm leading-6 text-foreground">{recommendedAction}</p>
            </div>
          </div>
          
           <div className="surface-panel-muted rounded-[24px] p-4">
            <h3 className="text-lg font-semibold text-foreground mb-1">控制面捷径</h3>
            <p className="mb-4 text-xs text-muted-foreground">先管系统，再看社区。</p>
            <div className="space-y-2">
              <Link to="/admin/communities/discovered" className="surface-action-secondary flex w-full items-center justify-between rounded-xl px-4 py-3 text-left text-sm font-medium transition-colors">
                <span>审核候选社区</span>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link to="/admin/communities/pool" className="surface-action-secondary flex w-full items-center justify-between rounded-xl px-4 py-3 text-left text-sm font-medium transition-colors">
                <span>看社区池</span>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
           </div>

           <div className="surface-panel-muted rounded-[24px] p-4">
            <h3 className="text-lg font-semibold text-foreground mb-1">今天先做哪一步</h3>
            <p className="mb-3 text-sm font-medium text-foreground">{opsPriority.title}</p>
            <p className="mb-4 text-xs leading-6 text-muted-foreground">{opsPriority.description}</p>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => navigate('/admin/tasks/ledger')}
                className="surface-action-primary inline-flex h-10 w-full items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
              >
                先看任务账本
              </button>
              <button
                type="button"
                onClick={() => navigate('/admin/communities/pool')}
                className="surface-action-secondary inline-flex h-10 w-full items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors"
              >
                再看社区池
              </button>
            </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardPage;
