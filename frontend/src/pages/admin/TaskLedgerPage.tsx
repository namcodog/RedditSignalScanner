import React, { useEffect, useState } from 'react';
import { 
  getRecentTasks, 
  getTaskLedger, 
  TaskLedgerItem, 
  AdminTaskLedgerResponse 
} from '@/api/admin.api';

const TaskLedgerPage: React.FC = () => {
  const [tasks, setTasks] = useState<TaskLedgerItem[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminTaskLedgerResponse | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  // Pagination / Filter
  const [page, setPage] = useState(0);
  const LIMIT = 50;

  const fetchTasks = async () => {
    setLoadingList(true);
    try {
      const data = await getRecentTasks({ 
        limit: LIMIT,
        offset: page * LIMIT
      });
      setTasks(data.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [page]);

  const handleSelectTask = async (taskId: string) => {
    setSelectedTaskId(taskId);
    setLoadingDetail(true);
    setDetail(null);
    try {
      const data = await getTaskLedger(taskId, true); // Include full package if needed
      setDetail(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Status mapping helper
  const getStatusText = (status: string) => {
    const map: Record<string, string> = {
      'pending': '⏳ 等待中',
      'processing': '🔄 处理中',
      'completed': '✅ 已完成',
      'failed': '❌ 失败',
    };
    return map[status] || status;
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Left Sidebar: Task List */}
      <div className="w-1/3 border-r border-gray-200 dark:border-gray-700 flex flex-col bg-white dark:bg-gray-800">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">任务账本 (Task Ledger)</h2>
          <div className="text-xs text-gray-500">第 {page + 1} 页</div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {loadingList ? (
            <div className="p-4 text-center text-gray-500">正在加载任务列表...</div>
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {tasks.map(task => (
                <div 
                  key={task.task_id}
                  onClick={() => handleSelectTask(task.task_id)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                    selectedTaskId === task.task_id ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' : ''
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-medium text-gray-900 dark:text-gray-100 truncate w-2/3" title={task.user_email}>
                      {task.user_email}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      task.status === 'completed' ? 'bg-green-100 text-green-800' :
                      task.status === 'failed' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {getStatusText(task.status)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 flex justify-between mt-1">
                    <span>{new Date(task.created_at).toLocaleTimeString()}</span>
                    <span>置信度: {task.confidence_score ? task.confidence_score.toFixed(2) : '-'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Pagination Controls */}
        <div className="p-2 border-t border-gray-200 dark:border-gray-700 flex justify-between">
          <button 
            disabled={page === 0}
            onClick={() => setPage(p => Math.max(0, p - 1))}
            className="px-3 py-1 bg-gray-100 rounded disabled:opacity-50 text-sm hover:bg-gray-200 transition-colors"
          >
            上一页
          </button>
          <button 
            onClick={() => setPage(p => p + 1)}
            className="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200 transition-colors"
          >
            下一页
          </button>
        </div>
      </div>

      {/* Right Content: Detail View */}
      <div className="flex-1 overflow-y-auto p-8">
        {!selectedTaskId ? (
          <div className="h-full flex items-center justify-center text-gray-400">
            请从左侧选择一个任务查看详情
          </div>
        ) : loadingDetail ? (
          <div className="h-full flex items-center justify-center text-gray-500">
            正在加载账本详情...
          </div>
        ) : detail ? (
          <div className="space-y-8 max-w-4xl mx-auto">
            {/* Header Info */}
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                任务报告
              </h1>
              <div className="bg-white dark:bg-gray-800 p-4 rounded border shadow-sm">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 block">任务 ID</span>
                    <span className="font-mono">{detail.task.id}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block">用户 ID</span>
                    <span className="font-mono">{detail.task.user_id}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-500 block">产品描述</span>
                    <p className="mt-1">{detail.task.product_description}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white dark:bg-gray-800 p-4 rounded border dark:border-gray-700">
                <div className="text-xs text-gray-500 uppercase">Snapshot Tier (快照分级)</div>
                <div className="text-xl font-bold mt-1 text-blue-600">
                  {detail.facts_snapshot?.tier || 'N/A'}
                </div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded border dark:border-gray-700">
                <div className="text-xs text-gray-500 uppercase">Snapshot Status (执行结果)</div>
                <div className="text-xl font-bold mt-1">
                  {detail.facts_snapshot?.status === 'blocked' ? (
                    <span className="text-red-600">🛑 已阻断 (Blocked)</span>
                  ) : detail.facts_snapshot?.status ? (
                    <span className="text-green-600">✅ {detail.facts_snapshot.status}</span>
                  ) : 'N/A'}
                </div>
                {detail.facts_snapshot?.blocked_reason && (
                  <div className="text-xs text-red-500 mt-1">
                    阻断原因: {detail.facts_snapshot.blocked_reason}
                  </div>
                )}
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded border dark:border-gray-700">
                <div className="text-xs text-gray-500 uppercase">Quality Score (质量评分)</div>
                <div className="text-xl font-bold mt-1">
                  {detail.facts_snapshot?.quality || 'N/A'}
                </div>
              </div>
            </div>

            {/* Sources Ledger */}
            {detail.analysis?.sources ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold mb-4 border-b dark:border-gray-700 pb-2">数据源账本 (Sources Ledger)</h3>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
                  <div>
                    <div className="text-2xl font-light text-gray-900 dark:text-gray-100">
                      {detail.analysis.sources.communities?.length || 0}
                    </div>
                    <div className="text-sm text-gray-500">覆盖社区数</div>
                  </div>
                  <div>
                    <div className="text-2xl font-light text-gray-900 dark:text-gray-100">
                      {detail.analysis.sources.posts_analyzed || 0}
                    </div>
                    <div className="text-sm text-gray-500">分析帖子数</div>
                  </div>
                  <div>
                    <div className="text-2xl font-light text-gray-900 dark:text-gray-100">
                      {((detail.analysis.sources.cache_hit_rate || 0) * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">缓存命中率</div>
                  </div>
                  <div>
                    <div className="text-2xl font-light text-gray-900 dark:text-gray-100">
                      {detail.analysis.sources.reddit_api_calls || 0}
                    </div>
                    <div className="text-sm text-gray-500">API 调用量</div>
                  </div>
                </div>

                {/* Raw Sources JSON (Collapsible) */}
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm text-blue-600 hover:underline mb-2">查看原始 Sources JSON</summary>
                  <pre className="bg-gray-50 dark:bg-gray-900 p-4 rounded text-xs overflow-x-auto">
                    {JSON.stringify(detail.analysis.sources, null, 2)}
                  </pre>
                </details>
              </div>
            ) : (
              <div className="p-8 text-center bg-gray-50 dark:bg-gray-800 rounded border border-dashed border-gray-300 dark:border-gray-700 text-gray-500">
                暂无分析源数据 (No analysis sources data available)
              </div>
            )}

            {/* Facts Package (If included) */}
            {detail.facts_snapshot?.v2_package && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold mb-4 border-b dark:border-gray-700 pb-2">Facts 数据包 (Facts Package)</h3>
                <details>
                  <summary className="cursor-pointer text-sm text-blue-600 hover:underline mb-2">查看完整数据包</summary>
                  <pre className="bg-gray-50 dark:bg-gray-900 p-4 rounded text-xs overflow-x-auto max-h-96">
                    {JSON.stringify(detail.facts_snapshot.v2_package, null, 2)}
                  </pre>
                </details>
              </div>
            )}
            
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-red-500">
            加载任务详情失败
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskLedgerPage;