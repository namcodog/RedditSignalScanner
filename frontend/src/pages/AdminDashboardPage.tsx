/**
 * Admin Dashboard Page
 * 
 * 基于 PRD-07 Admin后台设计
 * 参考界面: https://v0-reddit-signal-scanner.vercel.app
 * 
 * 功能:
 * 1. 社区验收 - 社区列表表格（10列）
 * 2. 算法验收 - 分析任务列表
 * 3. 用户反馈 - 反馈汇总
 * 
 * 最后更新: 2025-10-15 Day 10
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { type CommunityData } from '@/services/admin.service';
import { ROUTES } from '@/router';

/**
 * Mock数据（Day 10使用，Day 11替换为真实API）
 */
const MOCK_COMMUNITIES: CommunityData[] = [
  {
    community: 'r/startups',
    hit_7d: 83,
    last_crawled_at: '2025/9/15 19:20:00',
    dup_ratio: 0.08,
    spam_ratio: 0.06,
    topic_score: 0.74,
    c_score: 82,
    status_color: 'green',
    labels: ['状态:核心', '主题:创业'],
  },
  {
    community: 'r/technology',
    hit_7d: 45,
    last_crawled_at: '2025/9/14 16:30:00',
    dup_ratio: 0.18,
    spam_ratio: 0.12,
    topic_score: 0.52,
    c_score: 48,
    status_color: 'red',
    labels: ['状态:黑名单', '风险:广告多'],
  },
  {
    community: 'r/ArtificialIntelligence',
    hit_7d: 67,
    last_crawled_at: '2025/9/15 22:45:00',
    dup_ratio: 0.12,
    spam_ratio: 0.08,
    topic_score: 0.68,
    c_score: 65,
    status_color: 'yellow',
    labels: ['状态:实验', '主题:AI'],
  },
];

/**
 * 状态标签组件
 */
const StatusBadge: React.FC<{ status: 'green' | 'yellow' | 'red' }> = ({ status }) => {
  const statusMap = {
    green: { text: '正常', bgColor: '#dcfce7', textColor: '#166534' },
    yellow: { text: '警告', bgColor: '#fef3c7', textColor: '#92400e' },
    red: { text: '异常', bgColor: '#fee2e2', textColor: '#991b1b' },
  };

  const { text, bgColor, textColor } = statusMap[status];

  return (
    <span
      style={{
        backgroundColor: bgColor,
        color: textColor,
        padding: '4px 8px',
        borderRadius: '4px',
        display: 'inline-block',
        fontSize: '14px',
      }}
    >
      {text}
    </span>
  );
};

/**
 * 社区验收Tab
 */
const CommunityReviewTab: React.FC = () => {
  const [communities] = useState<CommunityData[]>(MOCK_COMMUNITIES);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // 过滤社区
  const filteredCommunities = communities.filter((community) => {
    const matchesSearch = community.community.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || community.status_color === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div style={{ padding: '24px' }}>
      {/* 搜索和筛选 */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px' }}>
        <input
          type="text"
          placeholder="搜索社区..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            flex: 1,
            padding: '8px 12px',
            border: '1px solid #e5e7eb',
            borderRadius: '4px',
            fontSize: '14px',
          }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #e5e7eb',
            borderRadius: '4px',
            fontSize: '14px',
            minWidth: '150px',
          }}
        >
          <option value="all">全部状态</option>
          <option value="green">正常</option>
          <option value="yellow">警告</option>
          <option value="red">异常</option>
        </select>
        <Link
          to={ROUTES.ADMIN_COMMUNITY_IMPORT}
          style={{
            backgroundColor: '#10b981',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            padding: '8px 16px',
            fontSize: '14px',
            cursor: 'pointer',
            textDecoration: 'none',
            display: 'inline-flex',
            alignItems: 'center',
          }}
        >
          📥 批量导入
        </Link>
        <button
          style={{
            backgroundColor: '#3b82f6',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            padding: '8px 16px',
            fontSize: '14px',
            cursor: 'pointer',
          }}
          onClick={() => alert('生成 Patch 功能（Day 11实现）')}
        >
          生成 Patch
        </button>
        <button
          style={{
            backgroundColor: '#3b82f6',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            padding: '8px 16px',
            fontSize: '14px',
            cursor: 'pointer',
          }}
          onClick={() => alert('一键开 PR 功能（Day 11实现）')}
        >
          一键开 PR
        </button>
      </div>

      {/* 社区列表表格 */}
      <div style={{ overflowX: 'auto' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            border: '1px solid #e5e7eb',
          }}
        >
          <thead>
            <tr style={{ backgroundColor: '#f3f4f6' }}>
              <th style={tableHeaderStyle}>社区名</th>
              <th style={tableHeaderStyle}>7天命中</th>
              <th style={tableHeaderStyle}>最后抓取</th>
              <th style={tableHeaderStyle}>重复率</th>
              <th style={tableHeaderStyle}>垃圾率</th>
              <th style={tableHeaderStyle}>主题分</th>
              <th style={tableHeaderStyle}>C-Score</th>
              <th style={tableHeaderStyle}>状态</th>
              <th style={tableHeaderStyle}>标签</th>
              <th style={tableHeaderStyle}>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredCommunities.map((community) => (
              <tr key={community.community} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={tableCellStyle}>{community.community}</td>
                <td style={{ ...tableCellStyle, textAlign: 'right' }}>{community.hit_7d}</td>
                <td style={tableCellStyle}>{community.last_crawled_at}</td>
                <td style={{ ...tableCellStyle, textAlign: 'right' }}>
                  {(community.dup_ratio * 100).toFixed(1)}%
                </td>
                <td style={{ ...tableCellStyle, textAlign: 'right' }}>
                  {(community.spam_ratio * 100).toFixed(1)}%
                </td>
                <td style={{ ...tableCellStyle, textAlign: 'right' }}>{community.topic_score * 100}</td>
                <td style={{ ...tableCellStyle, textAlign: 'right' }}>{community.c_score}</td>
                <td style={{ ...tableCellStyle, textAlign: 'center' }}>
                  <StatusBadge status={community.status_color} />
                </td>
                <td style={tableCellStyle}>
                  {community.labels.map((label, idx) => (
                    <span key={idx} style={{ marginRight: '4px' }}>
                      {label}
                    </span>
                  ))}
                </td>
                <td style={{ ...tableCellStyle, textAlign: 'center' }}>
                  <select
                    style={{
                      padding: '4px 12px',
                      border: '1px solid #e5e7eb',
                      borderRadius: '4px',
                      fontSize: '14px',
                      cursor: 'pointer',
                    }}
                    onChange={(e) => {
                      if (e.target.value) {
                        alert(`${e.target.value} 功能（Day 11实现）`);
                        e.target.value = '';
                      }
                    }}
                  >
                    <option value="">操作</option>
                    <option value="approve">通过/核心</option>
                    <option value="experiment">进实验</option>
                    <option value="pause">暂停</option>
                    <option value="blacklist">黑名单</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/**
 * 算法验收Tab
 */
const AlgorithmReviewTab: React.FC = () => {
  return (
    <div style={{ padding: '24px', textAlign: 'center', color: '#6b7280' }}>
      <p>算法验收功能（Day 11实现）</p>
    </div>
  );
};

/**
 * 用户反馈Tab
 */
const UserFeedbackTab: React.FC = () => {
  return (
    <div style={{ padding: '24px', textAlign: 'center', color: '#6b7280' }}>
      <p>用户反馈功能（Day 11实现）</p>
    </div>
  );
};

/**
 * Admin Dashboard主页面
 */
const AdminDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'community' | 'algorithm' | 'feedback'>('community');
  const [systemStatus] = useState('系统正常');

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#ffffff' }}>
      {/* 页面标题 */}
      <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1a1a1a', marginBottom: '8px' }}>
          Reddit Signal Scanner
        </h1>
        <p style={{ fontSize: '18px', color: '#6b7280', marginBottom: '8px' }}>Admin Dashboard</p>
        <p style={{ fontSize: '14px', color: '#22c55e' }}>{systemStatus}</p>
      </div>

      {/* Tab导航 */}
      <div style={{ borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', gap: '0', padding: '0 24px' }}>
          <button
            onClick={() => setActiveTab('community')}
            style={{
              padding: '12px 24px',
              border: 'none',
              borderBottom: activeTab === 'community' ? '2px solid #3b82f6' : '2px solid transparent',
              backgroundColor: 'transparent',
              color: activeTab === 'community' ? '#3b82f6' : '#6b7280',
              fontSize: '14px',
              fontWeight: activeTab === 'community' ? '600' : '400',
              cursor: 'pointer',
            }}
          >
            社区验收
          </button>
          <button
            onClick={() => setActiveTab('algorithm')}
            style={{
              padding: '12px 24px',
              border: 'none',
              borderBottom: activeTab === 'algorithm' ? '2px solid #3b82f6' : '2px solid transparent',
              backgroundColor: 'transparent',
              color: activeTab === 'algorithm' ? '#3b82f6' : '#6b7280',
              fontSize: '14px',
              fontWeight: activeTab === 'algorithm' ? '600' : '400',
              cursor: 'pointer',
            }}
          >
            算法验收
          </button>
          <button
            onClick={() => setActiveTab('feedback')}
            style={{
              padding: '12px 24px',
              border: 'none',
              borderBottom: activeTab === 'feedback' ? '2px solid #3b82f6' : '2px solid transparent',
              backgroundColor: 'transparent',
              color: activeTab === 'feedback' ? '#3b82f6' : '#6b7280',
              fontSize: '14px',
              fontWeight: activeTab === 'feedback' ? '600' : '400',
              cursor: 'pointer',
            }}
          >
            用户反馈
          </button>
        </div>
      </div>

      {/* Tab内容 */}
      {activeTab === 'community' && <CommunityReviewTab />}
      {activeTab === 'algorithm' && <AlgorithmReviewTab />}
      {activeTab === 'feedback' && <UserFeedbackTab />}
    </div>
  );
};

// 表格样式
const tableHeaderStyle: React.CSSProperties = {
  padding: '12px 16px',
  textAlign: 'left',
  fontSize: '14px',
  fontWeight: '600',
  color: '#374151',
  border: '1px solid #e5e7eb',
};

const tableCellStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: '14px',
  color: '#1f2937',
  border: '1px solid #e5e7eb',
};

export default AdminDashboardPage;

