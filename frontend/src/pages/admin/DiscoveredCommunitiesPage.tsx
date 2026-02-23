import React, { useEffect, useState } from 'react';
import { 
  getDiscoveredCommunities, 
  approveCommunity, 
  rejectCommunity, 
  DiscoveredCommunityItem 
} from '@/api/admin.api';

// Simple Modal Component
const Modal = ({ isOpen, onClose, title, children }: { isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg w-full max-w-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">{title}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
};

const DiscoveredCommunitiesPage: React.FC = () => {
  const [communities, setCommunities] = useState<DiscoveredCommunityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  
  // Modal State
  const [selectedCommunity, setSelectedCommunity] = useState<DiscoveredCommunityItem | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'reject' | null>(null);
  const [adminNotes, setAdminNotes] = useState('');
  const [tier, setTier] = useState('medium');

  const fetchCommunities = async () => {
    setLoading(true);
    try {
      const data = await getDiscoveredCommunities(3); // evidenceLimit=3
      setCommunities(data.items);
    } catch (error: any) {
      console.error('Error fetching communities', error);
      alert('加载候选社区失败: ' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCommunities();
  }, []);

  const openModal = (community: DiscoveredCommunityItem, type: 'approve' | 'reject') => {
    setSelectedCommunity(community);
    setActionType(type);
    setAdminNotes('');
    setTier('medium'); // Default tier
  };

  const closeModal = () => {
    setSelectedCommunity(null);
    setActionType(null);
  };

  const handleConfirmAction = async () => {
    if (!selectedCommunity || !actionType) return;

    setProcessing(selectedCommunity.name);
    try {
      if (actionType === 'approve') {
        await approveCommunity({
          name: selectedCommunity.name,
          tier: tier,
          admin_notes: adminNotes || '管理员人工批准',
          categories: null // Optional
        });
      } else {
        await rejectCommunity({
          name: selectedCommunity.name,
          admin_notes: adminNotes || '人工拒绝'
        });
      }
      
      // Success
      setCommunities(prev => prev.filter(c => c.name !== selectedCommunity.name));
      closeModal();
    } catch (error: any) {
      console.error('Action failed', error);
      alert(`${actionType === 'approve' ? '批准' : '拒绝'}失败: ${error.message}`);
    } finally {
      setProcessing(null);
    }
  };

  const formatCommunityName = (name: string) => {
    return name.startsWith('r/') ? name : `r/${name}`;
  };

  if (loading) {
    return <div className="p-8 text-center">正在加载待审核社区...</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <header className="mb-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          候选社区审核
        </h1>
        <button 
          onClick={fetchCommunities} 
          className="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          刷新列表
        </button>
      </header>

      {communities.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-gray-50 dark:bg-gray-800 rounded-lg">
          暂无待审核的候选社区。干得漂亮！
        </div>
      ) : (
        <div className="grid gap-6">
          {communities.map((community) => (
            <div 
              key={community.name} 
              className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-blue-600 dark:text-blue-400">
                    {formatCommunityName(community.name)}
                  </h2>
                  <div className="text-sm text-gray-500 mt-1 space-x-4">
                    <span>被发现次数: {community.discovered_count}</span>
                    <span>最近活跃: {new Date(community.last_discovered_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => openModal(community, 'reject')}
                    disabled={processing === community.name}
                    className="px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50 transition-colors font-medium"
                  >
                    拒绝
                  </button>
                  <button
                    onClick={() => openModal(community, 'approve')}
                    disabled={processing === community.name}
                    className="px-4 py-2 bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50 transition-colors font-medium"
                  >
                    批准
                  </button>
                </div>
              </div>

              {/* Evidence Section */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded p-4">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wide">
                  核心证据帖 (Top {community.evidence_posts.length})
                </h3>
                <div className="space-y-3">
                  {community.evidence_posts.map((post) => (
                    <div key={post.source_post_id} className="text-sm">
                      <div className="font-medium text-gray-900 dark:text-gray-100 mb-1">
                        {post.title}
                      </div>
                      <p className="text-gray-600 dark:text-gray-400 line-clamp-2 text-xs">
                        {post.summary}
                      </p>
                      <div className="text-xs text-gray-400 mt-1 flex gap-2">
                        <span>分数: {post.score}</span>
                        <span>评论数: {post.num_comments}</span>
                        <span>来源: {post.probe_source}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Action Modal */}
      <Modal 
        isOpen={!!selectedCommunity} 
        onClose={closeModal} 
        title={actionType === 'approve' ? `批准 ${selectedCommunity ? formatCommunityName(selectedCommunity.name) : ''}` : `拒绝 ${selectedCommunity ? formatCommunityName(selectedCommunity.name) : ''}`}
      >
        <div className="space-y-4">
          {actionType === 'approve' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">分级 (Tier)</label>
              <select 
                value={tier} 
                onChange={(e) => setTier(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 dark:bg-gray-700 dark:border-gray-600"
              >
                <option value="Tier S">Tier S (战略级)</option>
                <option value="Tier A">Tier A (核心级)</option>
                <option value="Tier B">Tier B (细分级)</option>
                <option value="Tier C">Tier C (长尾级)</option>
                <option value="medium">Medium (默认)</option>
              </select>
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">管理员备注</label>
            <textarea 
              value={adminNotes} 
              onChange={(e) => setAdminNotes(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 dark:bg-gray-700 dark:border-gray-600"
              rows={3}
              placeholder="请输入备注（可选）..."
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <button 
              onClick={closeModal} 
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              取消
            </button>
            <button 
              onClick={handleConfirmAction}
              disabled={!!processing}
              className={`px-4 py-2 rounded text-white font-medium ${
                actionType === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
              }`}
            >
              确认{actionType === 'approve' ? '批准' : '拒绝'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DiscoveredCommunitiesPage;