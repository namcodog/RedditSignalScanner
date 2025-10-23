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

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  adminService,
  type BetaFeedbackItem,
  type CommunityData,
  type QualityMetrics,
} from '@/services/admin.service';
import { ROUTES } from '@/router';



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
 * 社区验收Tab（使用真实API）
 */
const CommunityReviewTab: React.FC = () => {
  const [communities, setCommunities] = useState<CommunityData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // 从API加载社区数据
  useEffect(() => {
    const fetchCommunities = async () => {
      try {
        setLoading(true);
        const data = await adminService.getCommunities({ page_size: 200 });
        setCommunities(data.items);
        setError(null);
      } catch (err) {
        setError('加载社区列表失败');
        console.error('Failed to fetch communities:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchCommunities();
  }, []);

  // 过滤社区
  const filteredCommunities = communities.filter((community) => {
    const matchesSearch = community.community.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || community.status_color === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // 加载状态
  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <p>加载中...</p>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#ef4444' }}>
        <p>{error}</p>
      </div>
    );
  }

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
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setLoading(true);
        const data = await adminService.getAnalysisTasks({ limit: 50 });
        setTasks(data.items);
        setError(null);
      } catch (err) {
        setError('加载分析任务失败');
        console.error('Failed to fetch analysis tasks:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#6b7280' }}>
        <p>加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#ef4444' }}>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '16px' }}>
        算法验收
      </h2>

      {tasks.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#6b7280', padding: '48px' }}>
          <p>暂无分析任务数据</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ padding: '10px 8px', textAlign: 'left', fontSize: '13px', fontWeight: '600' }}>任务ID</th>
                <th style={{ padding: '10px 8px', textAlign: 'left', fontSize: '13px', fontWeight: '600' }}>用户</th>
                <th style={{ padding: '10px 8px', textAlign: 'center', fontSize: '13px', fontWeight: '600' }}>状态</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>耗时(秒)</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>置信度</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>社区数</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>帖子数</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>痛点</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>竞品</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>机会</th>
                <th style={{ padding: '10px 8px', textAlign: 'right', fontSize: '13px', fontWeight: '600' }}>缓存率</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task, index) => (
                <tr
                  key={task.task_id}
                  style={{
                    borderBottom: '1px solid #e5e7eb',
                    backgroundColor: index % 2 === 0 ? '#ffffff' : '#f9fafb',
                  }}
                >
                  <td style={{ padding: '10px 8px', fontSize: '13px' }}>
                    {String(task.task_id).substring(0, 8)}...
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px' }}>
                    {task.user_email}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'center' }}>
                    <span style={{
                      padding: '3px 6px',
                      borderRadius: '4px',
                      backgroundColor: task.status === 'completed' ? '#dcfce7' : task.status === 'failed' ? '#fee2e2' : '#fef3c7',
                      color: task.status === 'completed' ? '#166534' : task.status === 'failed' ? '#991b1b' : '#92400e',
                      fontSize: '11px'
                    }}>
                      {task.status}
                    </span>
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.processing_seconds !== null ? task.processing_seconds.toFixed(1) : '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.confidence_score !== null ? (
                      <span style={{
                        color: task.confidence_score >= 0.7 ? '#166534' : task.confidence_score >= 0.5 ? '#92400e' : '#991b1b',
                        fontWeight: '600'
                      }}>
                        {(task.confidence_score * 100).toFixed(0)}%
                      </span>
                    ) : '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.communities_count || '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.posts_analyzed || '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.pain_points_count || '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.competitors_count || '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.opportunities_count || '-'}
                  </td>
                  <td style={{ padding: '10px 8px', fontSize: '13px', textAlign: 'right' }}>
                    {task.cache_hit_rate !== null && task.cache_hit_rate !== undefined ? (
                      <span style={{
                        color: task.cache_hit_rate >= 0.8 ? '#166534' : task.cache_hit_rate >= 0.5 ? '#92400e' : '#991b1b'
                      }}>
                        {(task.cache_hit_rate * 100).toFixed(0)}%
                      </span>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

/**
 * 用户反馈Tab
 */
const UserFeedbackTab: React.FC = () => {
  const [feedbackList, setFeedbackList] = useState<BetaFeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFeedback = async () => {
      try {
        setLoading(true);
        const response = await adminService.getBetaFeedbackList();
        setFeedbackList(response.items);
        setError(null);
      } catch (err) {
        setError('加载用户反馈失败');
        console.error('Failed to fetch feedback:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchFeedback();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#6b7280' }}>
        <p>加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#ef4444' }}>
        <p>{error}</p>
      </div>
    );
  }

  // 计算汇总数据
  const satisfiedCount = feedbackList.filter(f => f.satisfaction === 'satisfied').length;
  const satisfactionRate = feedbackList.length > 0 ? (satisfiedCount / feedbackList.length) * 100 : 0;

  return (
    <div style={{ padding: '24px' }}>
      <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '24px' }}>
        用户反馈列表
      </h2>

      {/* 汇总卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '32px' }}>
        <div style={{ backgroundColor: '#f9fafb', padding: '20px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>总反馈数</div>
          <div style={{ fontSize: '32px', fontWeight: '600', color: '#3b82f6' }}>
            {feedbackList.length}
          </div>
        </div>

        <div style={{ backgroundColor: '#f9fafb', padding: '20px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>满意率</div>
          <div style={{ fontSize: '32px', fontWeight: '600', color: '#10b981' }}>
            {satisfactionRate.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* 反馈列表 */}
      {feedbackList.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#6b7280', padding: '48px' }}>
          <p>暂无用户反馈数据</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>任务ID</th>
                <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>满意度</th>
                <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>缺失社区</th>
                <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>评论</th>
                <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {feedbackList.map((feedback, index) => (
                <tr
                  key={feedback.id}
                  style={{
                    borderBottom: '1px solid #e5e7eb',
                    backgroundColor: index % 2 === 0 ? '#ffffff' : '#f9fafb',
                  }}
                >
                  <td style={{ padding: '12px', fontSize: '14px' }}>
                    {feedback.task_id.substring(0, 8)}...
                  </td>
                  <td style={{ padding: '12px', fontSize: '14px' }}>
                    <span style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: feedback.satisfaction === 'satisfied' ? '#dcfce7' : '#fee2e2',
                      color: feedback.satisfaction === 'satisfied' ? '#166534' : '#991b1b',
                      fontSize: '12px'
                    }}>
                      {feedback.satisfaction === 'satisfied' ? '满意' : '不满意'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontSize: '14px' }}>
                    {feedback.missing_communities && feedback.missing_communities.length > 0
                      ? feedback.missing_communities.join(', ')
                      : '-'}
                  </td>
                  <td style={{ padding: '12px', fontSize: '14px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {feedback.comments || '-'}
                  </td>
                  <td style={{ padding: '12px', fontSize: '14px' }}>
                    {new Date(feedback.created_at).toLocaleString('zh-CN')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

/**
 * 数据质量Tab
 */
const MetricsTab: React.FC = () => {
  const [metrics, setMetrics] = useState<QualityMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const data = await adminService.getQualityMetrics();
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError('加载数据失败');
        console.error('Failed to fetch metrics:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  // 计算最新指标（取最后一天的数据）
  const latestMetrics = metrics.length > 0 ? metrics[metrics.length - 1] : null;

  // 计算平均值
  const avgCollectionRate =
    metrics.length > 0
      ? metrics.reduce((sum, m) => sum + m.collection_success_rate, 0) / metrics.length
      : 0;
  const avgDupRate =
    metrics.length > 0
      ? metrics.reduce((sum, m) => sum + m.deduplication_rate, 0) / metrics.length
      : 0;
  const avgP50 =
    metrics.length > 0
      ? metrics.reduce((sum, m) => sum + m.processing_time_p50, 0) / metrics.length
      : 0;
  const avgP95 =
    metrics.length > 0
      ? metrics.reduce((sum, m) => sum + m.processing_time_p95, 0) / metrics.length
      : 0;

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#6b7280' }}>
        <p>加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#ef4444' }}>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
        数据质量看板 v0
      </h2>

      {/* 核心指标卡片 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        {/* 采集成功率 */}
        <div
          style={{
            padding: '20px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
          }}
        >
          <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>
            采集成功率
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1f2937' }}>
            {latestMetrics
              ? `${(latestMetrics.collection_success_rate * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
            7天平均: {(avgCollectionRate * 100).toFixed(1)}%
          </div>
        </div>

        {/* 重复率 */}
        <div
          style={{
            padding: '20px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
          }}
        >
          <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>
            重复率
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1f2937' }}>
            {latestMetrics
              ? `${(latestMetrics.deduplication_rate * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
            7天平均: {(avgDupRate * 100).toFixed(1)}%
          </div>
        </div>

        {/* 处理耗时 */}
        <div
          style={{
            padding: '20px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
          }}
        >
          <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>
            处理耗时
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1f2937' }}>
            {latestMetrics ? `${latestMetrics.processing_time_p50.toFixed(1)}s` : 'N/A'}
          </div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
            P50: {avgP50.toFixed(1)}s | P95: {avgP95.toFixed(1)}s
          </div>
        </div>
      </div>

      {/* 数据表格 */}
      <div style={{ marginTop: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
          历史数据（最近 7 天）
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={tableHeaderStyle}>日期</th>
              <th style={tableHeaderStyle}>采集成功率</th>
              <th style={tableHeaderStyle}>重复率</th>
              <th style={tableHeaderStyle}>处理耗时 P50</th>
              <th style={tableHeaderStyle}>处理耗时 P95</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr key={metric.date}>
                <td style={tableCellStyle}>{metric.date}</td>
                <td style={tableCellStyle}>
                  {(metric.collection_success_rate * 100).toFixed(1)}%
                </td>
                <td style={tableCellStyle}>
                  {(metric.deduplication_rate * 100).toFixed(1)}%
                </td>
                <td style={tableCellStyle}>{metric.processing_time_p50.toFixed(1)}s</td>
                <td style={tableCellStyle}>{metric.processing_time_p95.toFixed(1)}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/**
 * Admin Dashboard主页面
 */
const AdminDashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'community' | 'algorithm' | 'feedback' | 'metrics'>('community');
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
          <button
            onClick={() => setActiveTab('metrics')}
            style={{
              padding: '12px 24px',
              border: 'none',
              borderBottom: activeTab === 'metrics' ? '2px solid #3b82f6' : '2px solid transparent',
              backgroundColor: 'transparent',
              color: activeTab === 'metrics' ? '#3b82f6' : '#6b7280',
              fontSize: '14px',
              fontWeight: activeTab === 'metrics' ? '600' : '400',
              cursor: 'pointer',
            }}
          >
            数据质量
          </button>
        </div>
      </div>

      {/* Tab内容 */}
      {activeTab === 'community' && <CommunityReviewTab />}
      {activeTab === 'algorithm' && <AlgorithmReviewTab />}
      {activeTab === 'feedback' && <UserFeedbackTab />}
      {activeTab === 'metrics' && <MetricsTab />}
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
