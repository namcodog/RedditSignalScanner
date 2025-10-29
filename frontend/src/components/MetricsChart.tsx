/**
 * 质量指标图表组件
 *
 * 基于 Spec 007 User Story 2 (US2) - Task T029
 * 使用 recharts 展示质量指标趋势
 * 最后更新: 2025-10-27
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ChartDataPoint } from '@/types/metrics';
import { DEFAULT_METRICS_THRESHOLDS } from '@/types/metrics';

interface MetricsChartProps {
  /** 图表数据 */
  data: ChartDataPoint[];

  /** 图表高度（默认 400px） */
  height?: number;

  /** 是否显示图例（默认 true） */
  showLegend?: boolean;
}

/**
 * 自定义 Tooltip 组件
 */
interface ChartTooltipPayload {
  name?: string | number;
  value?: number | string;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: ChartTooltipPayload[];
}

const CustomTooltip: React.FC<ChartTooltipProps> = ({
  active,
  payload,
  label,
}) => {
  if (!active || !payload || payload.length === 0 || label == null) {
    return null;
  }

  const displayLabel = typeof label === 'string' ? label : String(label);

  return (
    <div
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        border: '1px solid #ccc',
        borderRadius: '8px',
        padding: '12px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
      }}
    >
      <p style={{ margin: '0 0 8px 0', fontWeight: 'bold', fontSize: '14px' }}>
        {displayLabel}
      </p>

      {payload.map((entry, index: number) => {
        if (!entry || entry.value == null) {
          return null;
        }
        const value =
          typeof entry.value === 'number'
            ? entry.value
            : Number(entry.value ?? 0);
        const name = typeof entry.name === 'string' ? entry.name : String(entry.name ?? '');

        const isAbnormal =
          (name === '缓存命中率' &&
            value < DEFAULT_METRICS_THRESHOLDS.minCacheHitRate) ||
          (name === '重复率' &&
            value > DEFAULT_METRICS_THRESHOLDS.maxDuplicateRate) ||
          (name === 'Precision@50' &&
            value < DEFAULT_METRICS_THRESHOLDS.minPrecisionAt50);

        return (
          <p
            key={`item-${index}`}
            style={{
              margin: '4px 0',
              color: entry.color,
              fontSize: '13px',
              fontWeight: isAbnormal ? 'bold' : 'normal',
            }}
          >
            {name}: {value}%
            {isAbnormal && ' ⚠️'}
          </p>
        );
      })}
    </div>
  );
};

/**
 * 质量指标图表组件
 *
 * @example
 * ```tsx
 * <MetricsChart
 *   data={chartData}
 *   height={400}
 *   showLegend={true}
 * />
 * ```
 */
export const MetricsChart: React.FC<MetricsChartProps> = ({
  data,
  height = 400,
  showLegend = true,
}) => {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#999',
          fontSize: '14px',
        }}
      >
        暂无数据
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={data}
        margin={{
          top: 10,
          right: 30,
          left: 0,
          bottom: 0,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: '#666' }}
          tickLine={{ stroke: '#e0e0e0' }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: '#666' }}
          tickLine={{ stroke: '#e0e0e0' }}
          domain={[0, 100]}
          label={{
            value: '百分比 (%)',
            angle: -90,
            position: 'insideLeft',
            style: { fontSize: 12, fill: '#666' },
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        {showLegend && (
          <Legend
            wrapperStyle={{ fontSize: '13px' }}
            iconType="line"
            iconSize={16}
          />
        )}

        {/* 缓存命中率 */}
        <Line
          type="monotone"
          dataKey="cacheHitRate"
          name="缓存命中率"
          stroke="#1890ff"
          strokeWidth={2}
          dot={{ r: 4, fill: '#1890ff' }}
          activeDot={{ r: 6 }}
        />

        {/* 重复率 */}
        <Line
          type="monotone"
          dataKey="duplicateRate"
          name="重复率"
          stroke="#ff4d4f"
          strokeWidth={2}
          dot={{ r: 4, fill: '#ff4d4f' }}
          activeDot={{ r: 6 }}
        />

        {/* Precision@50 */}
        <Line
          type="monotone"
          dataKey="precisionAt50"
          name="Precision@50"
          stroke="#52c41a"
          strokeWidth={2}
          dot={{ r: 4, fill: '#52c41a' }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default MetricsChart;
