import React, { useEffect, useState } from 'react';
import { getAdminDashboardStats, getRecentTasks, DashboardStats, TaskLedgerItem } from '@/api/admin.api';
import { Link } from 'react-router-dom';

const AdminDashboardPage: React.FC = () => {
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

  if (loading) return <div className="p-8 text-center">正在加载仪表盘...</div>;
  if (error) return <div className="p-8 text-center text-red-600">错误: {error}</div>;
  if (!stats) return null;

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
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Admin 仪表盘</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">总用户数</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total_users}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">累计任务</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total_tasks}</div>
          <div className="text-xs text-gray-500 mt-1">今日新增: {stats.tasks_today}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">平均处理耗时</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.avg_processing_time}秒</div>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400">缓存命中率</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{(stats.cache_hit_rate * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Recent Tasks */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">最近任务</h3>
              <Link to="/admin/tasks/ledger" className="text-sm text-blue-600 hover:underline">查看全部</Link>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {recentTasks.map(task => (
                <div key={task.task_id} className="p-4 flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-750">
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">任务 {task.task_id.substring(0, 8)}...</div>
                    <div className="text-xs text-gray-500 mt-1">
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
                    {task.posts_analyzed > 0 && <div className="text-xs text-gray-400 mt-1">{task.posts_analyzed} 帖子</div>}
                  </div>
                </div>
              ))}
              {recentTasks.length === 0 && <div className="p-4 text-center text-gray-500">暂无最近任务</div>}
            </div>
          </div>
        </div>

        {/* Right Column: System & Actions */}
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-4">系统状态 (System Status)</h3>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-300">活跃节点 (Workers)</span>
              <span className={`font-bold ${stats.active_workers > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {stats.active_workers}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-300">今日完成任务</span>
              <span className="font-bold text-gray-900 dark:text-gray-100">
                {stats.tasks_completed_today}
              </span>
            </div>
          </div>
          
           <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-4">快捷操作</h3>
            <div className="space-y-2">
              <Link to="/admin/communities/discovered" className="block w-full text-left px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded text-sm text-blue-600">
                → 审核候选社区
              </Link>
              <Link to="/admin/communities/pool" className="block w-full text-left px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded text-sm text-blue-600">
                → 管理社区池
              </Link>
            </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardPage;
