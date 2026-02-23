/**
 * 社区池管理页面
 * 
 * 功能：
 * 1. 展示社区池列表（支持筛选、排序、分页）
 * 2. 批量操作（调整Tier、优先级、启用/禁用、自动调级）
 * 3. 生成并应用调级建议
 * 4. 历史审计与回滚
 */

import React, { useState, useEffect } from 'react';
import { 
  getCommunityPool, 
  batchUpdateCommunities, 
  getCommunityAuditLogs, 
  rollbackCommunity,
  generateTierSuggestions,
  getTierSuggestions,
  applyTierSuggestions,
  CommunityPoolItem,
  BatchUpdatePayload,
  TierSuggestionItem,
  TierAuditLogItem
} from '@/api/admin.api';

// --- 样式定义 (复用 AdminDashboardPage 风格) ---
const buttonStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: '4px',
  border: 'none',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 500,
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
};

const inputStyle: React.CSSProperties = {
  padding: '8px 12px',
  border: '1px solid #e5e7eb',
  borderRadius: '4px',
  fontSize: '14px',
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  minWidth: '120px',
};

const tableHeaderStyle: React.CSSProperties = {
  padding: '12px 16px',
  textAlign: 'left',
  fontSize: '14px',
  fontWeight: '600',
  color: '#374151',
  borderBottom: '1px solid #e5e7eb',
  backgroundColor: '#f9fafb',
};

const tableCellStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: '14px',
  color: '#1f2937',
  borderBottom: '1px solid #e5e7eb',
};

// --- 辅助组件 ---

const HealthBadge: React.FC<{ status: string }> = ({ status }) => {
  const defaultConfig = { text: '未知', color: '#6b7280', bg: '#f3f4f6' };
  const map: Record<string, typeof defaultConfig> = {
    healthy: { text: '🟢 健康', color: '#166534', bg: '#dcfce7' },
    warning: { text: '🟠 警告', color: '#92400e', bg: '#fef3c7' },
    critical: { text: '🔴 严重', color: '#991b1b', bg: '#fee2e2' },
    unknown: defaultConfig,
  };
  const { text, color, bg } = map[status] || defaultConfig;
  return (
    <span style={{ backgroundColor: bg, color: color, padding: '2px 8px', borderRadius: '12px', fontSize: '12px' }}>
      {text}
    </span>
  );
};

const TierBadge: React.FC<{ tier: string }> = ({ tier }) => {
  // Dynamic color generation or mapping
  const getColor = (t: string) => {
    if (t.toUpperCase() === 'T1') return '#3b82f6';
    if (t.toUpperCase() === 'T2') return '#8b5cf6';
    if (t.toUpperCase() === 'T3') return '#6b7280';
    return '#4b5563';
  };
  
  const color = getColor(tier);
  return (
    <span style={{ 
      border: `1px solid ${color}`, 
      color: color, 
      padding: '2px 6px', 
      borderRadius: '4px', 
      fontSize: '12px', 
      fontWeight: 600 
    }}>
      {tier}
    </span>
  );
};

const Modal: React.FC<{ 
  isOpen: boolean; 
  onClose: () => void; 
  title: string; 
  children: React.ReactNode;
  onConfirm: () => void;
  confirmText?: string;
  confirmLoading?: boolean;
}> = ({ isOpen, onClose, title, children, onConfirm, confirmText = '确认', confirmLoading = false }) => {
  if (!isOpen) return null;
  
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: '#fff', borderRadius: '8px', width: '500px', maxWidth: '90%',
        padding: '24px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
      }}>
        <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>{title}</h3>
        <div style={{ marginBottom: '24px' }}>{children}</div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button onClick={onClose} style={{ ...buttonStyle, backgroundColor: '#fff', border: '1px solid #d1d5db', color: '#374151' }}>
            取消
          </button>
          <button 
            onClick={onConfirm} 
            disabled={confirmLoading}
            style={{ 
              ...buttonStyle, 
              backgroundColor: '#3b82f6', 
              color: '#fff',
              opacity: confirmLoading ? 0.7 : 1
            }}
          >
            {confirmLoading ? '处理中...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

const Drawer: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title: string;
  width?: string;
}> = ({ isOpen, onClose, children, title, width = '400px' }) => {
  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          onClick={onClose}
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.3)', zIndex: 900
          }} 
        />
      )}
      {/* Drawer Content */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: width,
        backgroundColor: '#fff', boxShadow: '-4px 0 6px rgba(0,0,0,0.1)',
        zIndex: 1000,
        transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.3s ease-in-out',
        display: 'flex', flexDirection: 'column'
      }}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 600 }}>{title}</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '20px' }}>×</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {children}
        </div>
      </div>
    </>
  );
};


// --- 主页面组件 ---

const CommunityPoolPage: React.FC = () => {
  // Data State
  const [items, setItems] = useState<CommunityPoolItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filter State
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [filters, setFilters] = useState({
    tier: '',
    health_status: '',
    is_active: '', // 'true' | 'false' | ''
    priority: ''
  });

  // Selection State
  const [selectedCommunities, setSelectedCommunities] = useState<string[]>([]);

  // Suggestion State
  const [suggestionsList, setSuggestionsList] = useState<TierSuggestionItem[]>([]);
  const [suggestionsTotal, setSuggestionsTotal] = useState(0);
  const [showDrawer, setShowDrawer] = useState(false);
  const [generatingSuggestions, setGeneratingSuggestions] = useState(false);
  const [selectedSuggestionIds, setSelectedSuggestionIds] = useState<number[]>([]);
  const [applyingSuggestions, setApplyingSuggestions] = useState(false);

  // Batch Action State
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [batchType, setBatchType] = useState<'tier' | 'priority' | 'status' | 'auto_tier' | null>(null);
  const [batchTargetValue, setBatchTargetValue] = useState<any>(null); // 'T1' | 'true' | ...
  const [batchReason, setBatchReason] = useState('');
  const [batchLoading, setBatchLoading] = useState(false);

  // History State
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
  const [historyLogs, setHistoryLogs] = useState<TierAuditLogItem[]>([]);
  const [historyCommunity, setHistoryCommunity] = useState<string>('');
  const [historyLoading, setHistoryLoading] = useState(false);
  
  // Rollback State
  const [showRollbackModal, setShowRollbackModal] = useState(false);
  const [rollbackTargetLog, setRollbackTargetLog] = useState<TierAuditLogItem | null>(null);
  const [rollbackReason, setRollbackReason] = useState('');
  const [rollbackLoading, setRollbackLoading] = useState(false);

  // Fetch Data
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        page,
        page_size: pageSize,
      };
      
      if (filters.tier) params.tier = filters.tier;
      if (filters.health_status) params.health_status = filters.health_status;
      if (filters.priority) params.priority = filters.priority;
      
      if (filters.is_active === 'true') {
        params.is_active = true;
      } else if (filters.is_active === 'false') {
        params.is_active = false;
      }

      const res = await getCommunityPool(params);
      setItems(res.items);
      setTotal(res.total);
      // 清空选区，防止跨页操作问题
      setSelectedCommunities([]);
    } catch (err) {
      console.error(err);
      setError('加载社区池失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page, filters]);

  // Handlers
  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1); // Reset to page 1
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedCommunities(items.map(i => i.name));
    } else {
      setSelectedCommunities([]);
    }
  };

  const handleSelectOne = (name: string, checked: boolean) => {
    if (checked) {
      setSelectedCommunities(prev => [...prev, name]);
    } else {
      setSelectedCommunities(prev => prev.filter(n => n !== name));
    }
  };

  // --- Suggestions Logic ---

  const loadSuggestions = async () => {
    try {
      const res = await getTierSuggestions({ 
        status: 'pending',
        min_confidence: 0.7,
        page_size: 100 // Load enough for V1
      });
      setSuggestionsList(res.items);
      setSuggestionsTotal(res.total);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateSuggestions = async () => {
    setGeneratingSuggestions(true);
    try {
      await generateTierSuggestions();
      await loadSuggestions();
      setShowDrawer(true);
    } catch (err) {
      console.error(err);
      alert('生成调级建议失败，请稍后重试');
    } finally {
      setGeneratingSuggestions(false);
    }
  };

  const handleOpenSuggestions = async () => {
    setShowDrawer(true);
    await loadSuggestions();
  };

  const handleSuggestionSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedSuggestionIds(suggestionsList.map(s => s.id));
    } else {
      setSelectedSuggestionIds([]);
    }
  };

  const handleSuggestionSelectOne = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedSuggestionIds(prev => [...prev, id]);
    } else {
      setSelectedSuggestionIds(prev => prev.filter(sid => sid !== id));
    }
  };

  const handleApplySuggestions = async (ids: number[]) => {
    if (!ids.length) return;
    
    // Confirm only if applying multiple
    if (ids.length > 1) {
      if (!confirm(`确认批量应用 ${ids.length} 条建议？`)) return;
    }

    setApplyingSuggestions(true);
    try {
      const res = await applyTierSuggestions({ suggestion_ids: ids });
      alert(`成功应用 ${res.applied_count} 条建议`);
      setSelectedSuggestionIds([]);
      loadSuggestions(); // Refresh drawer
      fetchData(); // Refresh main list to see changes
    } catch (err) {
      console.error(err);
      alert('应用建议失败，请稍后重试');
    } finally {
      setApplyingSuggestions(false);
    }
  };

  // --- Batch Actions Logic ---

  const openBatchModal = (type: 'tier' | 'priority' | 'status' | 'auto_tier', value: any) => {
    setBatchType(type);
    setBatchTargetValue(value);
    setBatchReason('');
    setShowBatchModal(true);
  };

  const handleBatchConfirm = async () => {
    if (!batchReason.trim()) {
      alert('请输入操作原因');
      return;
    }
    
    setBatchLoading(true);
    try {
      const updates: BatchUpdatePayload['updates'] = {};
      if (batchType === 'tier') updates.tier = batchTargetValue;
      if (batchType === 'priority') updates.priority = batchTargetValue;
      if (batchType === 'status') updates.is_active = batchTargetValue;
      if (batchType === 'auto_tier') updates.auto_tier_enabled = batchTargetValue;

      await batchUpdateCommunities({
        communities: selectedCommunities,
        updates,
        reason: batchReason
      });

      alert('批量更新成功');
      setShowBatchModal(false);
      fetchData(); // Refresh list
    } catch (err) {
      console.error(err);
      alert('批量更新失败，请稍后重试');
    } finally {
      setBatchLoading(false);
    }
  };

  // --- History & Rollback Logic ---

  const handleOpenHistory = async (communityName: string) => {
    setHistoryCommunity(communityName);
    setShowHistoryDrawer(true);
    setHistoryLoading(true);
    try {
      const res = await getCommunityAuditLogs(communityName, { page_size: 50 });
      setHistoryLogs(res.items);
    } catch (err) {
      console.error(err);
      alert('加载历史记录失败');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleRollbackClick = (log: TierAuditLogItem) => {
    setRollbackTargetLog(log);
    setRollbackReason('');
    setShowRollbackModal(true);
  };

  const handleRollbackConfirm = async () => {
    if (!rollbackTargetLog || !rollbackReason.trim()) {
      alert('请输入回滚原因');
      return;
    }

    setRollbackLoading(true);
    try {
      await rollbackCommunity(rollbackTargetLog.id, rollbackReason);
      alert('已回滚');
      setShowRollbackModal(false);
      // Refresh history and main list
      handleOpenHistory(historyCommunity); 
      fetchData();
    } catch (err) {
      console.error(err);
      alert('回滚失败，请稍后重试');
    } finally {
      setRollbackLoading(false);
    }
  };

  // Render Helpers
  const getBatchActionText = () => {
    if (batchType === 'tier') return `批量设为 ${batchTargetValue}`;
    if (batchType === 'priority') return `批量设优先级为 ${batchTargetValue}`;
    if (batchType === 'status') return batchTargetValue ? '批量启用' : '批量禁用';
    if (batchType === 'auto_tier') return batchTargetValue ? '批量开启自动调级' : '批量关闭自动调级';
    return '';
  };

  // Stats for header
  const statsText = `共 ${total} 个社区`;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#fff' }}>
      {/* Header */}
      <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1a1a1a', marginBottom: '8px' }}>社区池管理</h1>
          <p style={{ fontSize: '14px', color: '#6b7280' }}>管理 Reddit 社区的分级、状态与优先级配置</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            onClick={handleOpenSuggestions}
            style={{ ...buttonStyle, backgroundColor: '#fff', border: '1px solid #d1d5db', color: '#374151' }}
          >
            📂 查看建议
          </button>
          <button 
            onClick={handleGenerateSuggestions}
            disabled={generatingSuggestions}
            style={{ ...buttonStyle, backgroundColor: '#8b5cf6', color: '#fff' }}
          >
            {generatingSuggestions ? '生成中...' : '✨ 生成新建议'}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div style={{ padding: '12px 24px', backgroundColor: '#fee2e2', color: '#991b1b', fontSize: '14px' }}>
          {error}
        </div>
      )}

      {/* Filter & Action Bar */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        {/* Filters */}
        {/* Tier input changed to flexible text input for advanced filtering or standard select */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>Tier:</span>
          <input 
            type="text" 
            style={{ ...inputStyle, width: '100px' }} 
            placeholder="e.g. T1"
            value={filters.tier} 
            onChange={e => handleFilterChange('tier', e.target.value)} 
          />
        </div>

        <select style={selectStyle} value={filters.health_status} onChange={e => handleFilterChange('health_status', e.target.value)}>
          <option value="">全部健康度</option>
          <option value="healthy">健康</option>
          <option value="warning">警告</option>
          <option value="critical">严重</option>
        </select>

        <select style={selectStyle} value={filters.is_active} onChange={e => handleFilterChange('is_active', e.target.value)}>
          <option value="">全部状态</option>
          <option value="true">启用</option>
          <option value="false">禁用</option>
        </select>

        <div style={{ borderLeft: '1px solid #e5e7eb', height: '24px', margin: '0 8px' }} />

        {/* Stats */}
        <span style={{ fontSize: '14px', color: '#6b7280' }}>{statsText}</span>

        {/* Batch Actions (Visible when selected) */}
        {selectedCommunities.length > 0 && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center', backgroundColor: '#f0f9ff', padding: '4px 12px', borderRadius: '4px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#0369a1' }}>已选 {selectedCommunities.length} 项:</span>
            <button onClick={() => openBatchModal('tier', 'T1')} style={{ ...buttonStyle, fontSize: '12px', padding: '4px 8px', backgroundColor: '#fff', border: '1px solid #bae6fd' }}>设为 T1</button>
            <button onClick={() => openBatchModal('tier', 'T2')} style={{ ...buttonStyle, fontSize: '12px', padding: '4px 8px', backgroundColor: '#fff', border: '1px solid #bae6fd' }}>设为 T2</button>
            <button onClick={() => openBatchModal('tier', 'T3')} style={{ ...buttonStyle, fontSize: '12px', padding: '4px 8px', backgroundColor: '#fff', border: '1px solid #bae6fd' }}>设为 T3</button>
            <div style={{ borderLeft: '1px solid #bae6fd', height: '16px', margin: '0 4px' }}></div>
             <button onClick={() => openBatchModal('auto_tier', true)} style={{ ...buttonStyle, fontSize: '12px', padding: '4px 8px', backgroundColor: '#fff', border: '1px solid #bae6fd' }}>开启自动调级</button>
             <button onClick={() => openBatchModal('auto_tier', false)} style={{ ...buttonStyle, fontSize: '12px', padding: '4px 8px', backgroundColor: '#fff', border: '1px solid #bae6fd' }}>关闭自动调级</button>
            <div style={{ borderLeft: '1px solid #bae6fd', height: '16px', margin: '0 4px' }}></div>
            <button onClick={() => openBatchModal('status', false)} style={{ ...buttonStyle, fontSize: '12px', padding: '4px 8px', backgroundColor: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca' }}>禁用</button>
          </div>
        )}
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ ...tableHeaderStyle, width: '40px' }}>
                <input 
                  type="checkbox" 
                  checked={items.length > 0 && selectedCommunities.length === items.length}
                  onChange={handleSelectAll}
                />
              </th>
              <th style={tableHeaderStyle}>社区名称</th>
              <th style={tableHeaderStyle}>Tier</th>
              <th style={tableHeaderStyle}>优先级</th>
              <th style={tableHeaderStyle}>状态</th>
              <th style={tableHeaderStyle}>自动调级</th>
              <th style={tableHeaderStyle}>日均帖子</th>
              <th style={tableHeaderStyle}>健康状态</th>
              <th style={tableHeaderStyle}>调级建议</th>
              <th style={tableHeaderStyle}>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} style={{ padding: '32px', textAlign: 'center', color: '#6b7280' }}>
                  加载中...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ padding: '32px', textAlign: 'center', color: '#6b7280' }}>
                  暂无数据
                </td>
              </tr>
            ) : (
              items.map(item => (
                <tr key={item.name} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ ...tableCellStyle, textAlign: 'center' }}>
                    <input 
                      type="checkbox"
                      checked={selectedCommunities.includes(item.name)}
                      onChange={e => handleSelectOne(item.name, e.target.checked)}
                    />
                  </td>
                  <td style={{ ...tableCellStyle, fontWeight: 500 }}>{item.name}</td>
                  <td style={tableCellStyle}><TierBadge tier={item.tier} /></td>
                  <td style={tableCellStyle}>
                    <span style={{ 
                      color: item.priority === 'high' ? '#dc2626' : item.priority === 'medium' ? '#d97706' : '#3b82f6' 
                    }}>
                      {item.priority}
                    </span>
                  </td>
                  <td style={tableCellStyle}>
                    {item.is_active ? (
                      <span style={{ color: '#166534', backgroundColor: '#dcfce7', padding: '2px 8px', borderRadius: '12px', fontSize: '12px' }}>启用</span>
                    ) : (
                      <span style={{ color: '#991b1b', backgroundColor: '#fee2e2', padding: '2px 8px', borderRadius: '12px', fontSize: '12px' }}>禁用</span>
                    )}
                  </td>
                  <td style={tableCellStyle}>
                    <div 
                      onClick={() => {
                        setSelectedCommunities([item.name]);
                        openBatchModal('auto_tier', !item.auto_tier_enabled);
                      }}
                      style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                      {item.auto_tier_enabled ? (
                         <span style={{ color: '#166534', fontSize: '12px', fontWeight: 600 }}>✅ 已启用</span>
                      ) : (
                         <span style={{ color: '#9ca3af', fontSize: '12px' }}>⏸ 未启用</span>
                      )}
                    </div>
                  </td>
                  <td style={tableCellStyle}>
                    {item.daily_posts} <span style={{ color: '#9ca3af', fontSize: '12px' }}>({item.recent_metrics.posts_7d} / 7天)</span>
                  </td>
                  <td style={tableCellStyle}><HealthBadge status={item.health_status} /></td>
                  <td style={tableCellStyle}>
                    {item.tier_suggestion && item.tier_suggestion !== 'REMOVE' ? (
                      <span style={{ fontSize: '12px', color: '#6b7280' }}>建议: <strong>{item.tier_suggestion}</strong></span>
                    ) : item.tier_suggestion === 'REMOVE' ? (
                      <span style={{ fontSize: '12px', color: '#ef4444', fontWeight: 600 }}>建议移出</span>
                    ) : (
                      <span style={{ fontSize: '12px', color: '#d1d5db' }}>暂无</span>
                    )}
                  </td>
                  <td style={tableCellStyle}>
                    <button 
                      onClick={() => handleOpenHistory(item.name)}
                      style={{ ...buttonStyle, padding: '4px 8px', fontSize: '12px', backgroundColor: '#fff', border: '1px solid #d1d5db' }}
                    >
                      📜 历史
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #e5e7eb' }}>
        <span style={{ fontSize: '14px', color: '#6b7280' }}>
          显示 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} 条，共 {total} 条
        </span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            disabled={page === 1} 
            onClick={() => setPage(p => p - 1)}
            style={{ ...buttonStyle, backgroundColor: '#fff', border: '1px solid #d1d5db', padding: '6px 12px', fontSize: '12px' }}
          >
            上一页
          </button>
          <button 
            disabled={page * pageSize >= total} 
            onClick={() => setPage(p => p + 1)}
            style={{ ...buttonStyle, backgroundColor: '#fff', border: '1px solid #d1d5db', padding: '6px 12px', fontSize: '12px' }}
          >
            下一页
          </button>
        </div>
      </div>

      {/* Suggestion Drawer */}
      <Drawer 
        isOpen={showDrawer} 
        onClose={() => setShowDrawer(false)} 
        title="调级建议"
        width="500px"
      >
        <div>
          <div style={{ backgroundColor: '#f0f9ff', padding: '12px', borderRadius: '4px', marginBottom: '20px', fontSize: '13px', color: '#0c4a6e' }}>
            当前显示置信度 ≥ 70% 的待审核建议 (共 {suggestionsTotal} 条)
          </div>

          {/* Bulk Actions for Suggestions */}
          {suggestionsList.length > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', borderBottom: '1px solid #f3f4f6', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input 
                  type="checkbox" 
                  checked={suggestionsList.length > 0 && selectedSuggestionIds.length === suggestionsList.length}
                  onChange={handleSuggestionSelectAll}
                  id="selectAllSuggestions"
                />
                <label htmlFor="selectAllSuggestions" style={{ fontSize: '14px', cursor: 'pointer' }}>全选当前页</label>
              </div>
              <button 
                disabled={selectedSuggestionIds.length === 0 || applyingSuggestions}
                onClick={() => handleApplySuggestions(selectedSuggestionIds)}
                style={{ 
                  ...buttonStyle, 
                  backgroundColor: selectedSuggestionIds.length > 0 ? '#2563eb' : '#e5e7eb',
                  color: selectedSuggestionIds.length > 0 ? '#fff' : '#9ca3af',
                  cursor: selectedSuggestionIds.length > 0 ? 'pointer' : 'not-allowed',
                  fontSize: '12px', padding: '6px 12px'
                }}
              >
                {applyingSuggestions ? '应用中...' : `应用选中 (${selectedSuggestionIds.length})`}
              </button>
            </div>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {suggestionsList.map((s, idx) => (
              <div key={idx} style={{ border: '1px solid #e5e7eb', borderRadius: '6px', padding: '16px', position: 'relative' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <input 
                    type="checkbox" 
                    checked={selectedSuggestionIds.includes(s.id)}
                    onChange={e => handleSuggestionSelectOne(s.id, e.target.checked)}
                    style={{ marginTop: '4px' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 600, fontSize: '15px' }}>{s.community_name}</span>
                      <div style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <TierBadge tier={s.current_tier} /> 
                        <span style={{ color: '#9ca3af' }}>→</span> 
                        <TierBadge tier={s.suggested_tier} />
                      </div>
                    </div>
                    
                    <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px', display: 'flex', gap: '12px' }}>
                      <span>置信度: {Math.round(s.confidence * 100)}%</span>
                      <span>评分: {s.priority_score.toFixed(1)}</span>
                    </div>

                    <div style={{ backgroundColor: '#f9fafb', padding: '8px', borderRadius: '4px', marginBottom: '8px' }}>
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#4b5563' }}>
                        {s.reasons.map((r, ri) => (
                          <li key={ri} style={{ marginBottom: '2px' }}>{r}</li>
                        ))}
                      </ul>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                       <button 
                         onClick={() => handleApplySuggestions([s.id])}
                         disabled={applyingSuggestions}
                         style={{ ...buttonStyle, fontSize: '11px', padding: '4px 8px', backgroundColor: '#fff', border: '1px solid #2563eb', color: '#2563eb' }}
                       >
                         应用此条
                       </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {suggestionsList.length === 0 && (
               <div style={{ textAlign: 'center', color: '#9ca3af', padding: '20px' }}>暂无待审核建议</div>
            )}
          </div>
        </div>
      </Drawer>

      {/* History Drawer */}
      <Drawer
        isOpen={showHistoryDrawer}
        onClose={() => setShowHistoryDrawer(false)}
        title={`历史记录: ${historyCommunity}`}
        width="600px"
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', color: '#6b7280', padding: '20px' }}>加载中...</div>
        ) : historyLogs.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#9ca3af', padding: '20px' }}>暂无历史记录</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {historyLogs.map(log => (
              <div key={log.id} style={{ borderBottom: '1px solid #f3f4f6', paddingBottom: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600, fontSize: '14px', color: '#374151' }}>
                    {log.action === 'tier_change' ? 'Tier 变更' : 
                     log.action === 'batch_update' ? '批量更新' :
                     log.action === 'rollback' ? '回滚操作' : log.action}
                  </span>
                  <span style={{ fontSize: '12px', color: '#9ca3af' }}>{new Date(log.created_at).toLocaleString()}</span>
                </div>
                
                <div style={{ fontSize: '13px', color: '#4b5563', marginBottom: '4px' }}>
                  <span style={{ marginRight: '8px' }}>
                    {log.field_changed === 'tier' ? (
                      <>Tier: <TierBadge tier={log.from_value || '?'} /> → <TierBadge tier={log.to_value} /></>
                    ) : log.field_changed === 'multiple' ? (
                      '多项变更 (见快照)'
                    ) : (
                      `${log.field_changed}: ${log.from_value} → ${log.to_value}`
                    )}
                  </span>
                </div>

                <div style={{ fontSize: '12px', color: '#6b7280', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span>操作人: {log.changed_by}</span>
                  <span>来源: {log.change_source === 'auto' ? '🤖 自动' : log.change_source === 'suggestion' ? '💡 建议应用' : '👤 手动'}</span>
                </div>

                {log.reason && (
                  <div style={{ marginTop: '4px', fontSize: '12px', color: '#4b5563', fontStyle: 'italic' }}>
                    "{log.reason}"
                  </div>
                )}

                {/* Rollback Action */}
                <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                  {log.is_rolled_back ? (
                    <span style={{ fontSize: '11px', color: '#dc2626', border: '1px solid #fecaca', padding: '2px 6px', borderRadius: '4px' }}>已回滚</span>
                  ) : log.action !== 'rollback' ? (
                     <button 
                       onClick={() => handleRollbackClick(log)}
                       style={{ ...buttonStyle, fontSize: '11px', padding: '2px 6px', backgroundColor: '#fff', border: '1px solid #9ca3af', color: '#4b5563' }}
                     >
                       ↩️ 回滚到此
                     </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </Drawer>

      {/* Batch Action Modal */}
      <Modal
        isOpen={showBatchModal}
        onClose={() => setShowBatchModal(false)}
        onConfirm={handleBatchConfirm}
        title="确认批量更新"
        confirmLoading={batchLoading}
      >
        <p style={{ marginBottom: '16px', fontSize: '14px', color: '#374151' }}>
          将对 <strong>{selectedCommunities.length}</strong> 个社区应用：<br/>
          <span style={{ fontWeight: 600, color: '#2563eb' }}>{getBatchActionText()}</span>
        </p>
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>操作原因 (必填)</label>
          <textarea
            value={batchReason}
            onChange={e => setBatchReason(e.target.value)}
            placeholder="请输入本次操作原因（会写入审计日志）"
            style={{ width: '100%', height: '80px', ...inputStyle, resize: 'vertical' }}
          />
        </div>
      </Modal>

      {/* Rollback Confirmation Modal */}
      <Modal
        isOpen={showRollbackModal}
        onClose={() => setShowRollbackModal(false)}
        onConfirm={handleRollbackConfirm}
        title="确认回滚"
        confirmLoading={rollbackLoading}
      >
        {rollbackTargetLog && (
          <p style={{ marginBottom: '16px', fontSize: '14px', color: '#374151' }}>
            确认将 <strong>{rollbackTargetLog.community_name}</strong> 回滚到此变更之前的状态？<br/>
            <span style={{ fontSize: '12px', color: '#6b7280' }}>
              此操作会撤销 {new Date(rollbackTargetLog.created_at).toLocaleString()} 的变更。
            </span>
          </p>
        )}
        <div>
          <label style={{ display: 'block', fontSize: '14px', fontWeight: 500, marginBottom: '6px' }}>回滚原因 (必填)</label>
          <textarea
            value={rollbackReason}
            onChange={e => setRollbackReason(e.target.value)}
            placeholder="请输入回滚原因（会写入审计日志）"
            style={{ width: '100%', height: '80px', ...inputStyle, resize: 'vertical' }}
          />
        </div>
      </Modal>

    </div>
  );
};

export default CommunityPoolPage;