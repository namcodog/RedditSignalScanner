/**
 * 导出工具函数
 *
 * 支持导出分析报告为 JSON 和 CSV 格式
 * 基于 PRD-05 前端交互设计
 */

import type { ReportResponse } from '@/types';

// 定义导出用的报告数据类型
type ExportReport = ReportResponse['report'];

/**
 * 导出报告为 JSON 格式
 *
 * @param report 分析报告数据
 * @param taskId 任务ID
 */
export function exportToJSON(report: ExportReport, taskId: string): void {
  try {
    const dataStr = JSON.stringify(report, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `reddit-signal-scanner-${taskId}-${getTimestamp()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);

    console.log('[Export] JSON export successful:', taskId);
  } catch (error) {
    console.error('[Export] JSON export failed:', error);
    throw new Error('JSON 导出失败');
  }
}

/**
 * 导出报告为 CSV 格式
 *
 * @param report 分析报告数据
 * @param taskId 任务ID
 */
export function exportToCSV(report: ExportReport, taskId: string): void {
  try {
    // CSV Header
    let csv = 'Type,Rank,Text/Name,Score,Details,Keywords/Features\n';

    // Pain Points
    if (report.pain_points && report.pain_points.length > 0) {
      report.pain_points.forEach((pain, index: number) => {
        const text = escapeCSV(pain.description);
        const communities = pain.example_posts ? pain.example_posts.map(p => p.community).join('; ') : '';
        const details = `Frequency: ${pain.frequency}; Sentiment: ${(pain.sentiment_score * 100).toFixed(0)}%`;
        csv += `Pain Point,${index + 1},"${text}",${pain.frequency},"${details}","${communities}"\n`;
      });
    }

    // Competitors
    if (report.competitors && report.competitors.length > 0) {
      report.competitors.forEach((comp, index: number) => {
        const name = escapeCSV(comp.name);
        const strengths = comp.strengths ? comp.strengths.join('; ') : '';
        const weaknesses = comp.weaknesses ? comp.weaknesses.join('; ') : '';
        const details = `Mentions: ${comp.mentions}; Sentiment: ${comp.sentiment}; Strengths: ${strengths}; Weaknesses: ${weaknesses}`;
        csv += `Competitor,${index + 1},"${name}",${comp.mentions},"${details}","${strengths}"\n`;
      });
    }

    // Opportunities
    if (report.opportunities && report.opportunities.length > 0) {
      report.opportunities.forEach((opp, index: number) => {
        const description = escapeCSV(opp.description);
        const potentialUsers = escapeCSV(opp.potential_users);
        const details = `Relevance: ${(opp.relevance_score * 100).toFixed(0)}%; Potential Users: ${potentialUsers}`;
        csv += `Opportunity,${index + 1},"${description}",${(opp.relevance_score * 100).toFixed(0)},"${details}","${potentialUsers}"\n`;
      });
    }

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `reddit-signal-scanner-${taskId}-${getTimestamp()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);

    console.log('[Export] CSV export successful:', taskId);
  } catch (error) {
    console.error('[Export] CSV export failed:', error);
    throw new Error('CSV 导出失败');
  }
}

/**
 * 转义 CSV 字段中的特殊字符
 * 
 * @param text 原始文本
 * @returns 转义后的文本
 */
function escapeCSV(text: string): string {
  if (!text) return '';
  // 替换双引号为两个双引号
  return text.replace(/"/g, '""');
}

/**
 * 获取当前时间戳字符串
 * 
 * @returns 格式化的时间戳 (YYYYMMDD-HHMMSS)
 */
function getTimestamp(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  return `${year}${month}${day}-${hours}${minutes}${seconds}`;
}

/**
 * 导出报告摘要为文本格式
 *
 * @param report 分析报告数据
 * @param taskId 任务ID
 */
export function exportToText(report: ExportReport, taskId: string): void {
  try {
    let text = '# Reddit Signal Scanner - 分析报告\n\n';
    text += `任务ID: ${taskId}\n`;
    text += `生成时间: ${new Date().toLocaleString('zh-CN')}\n\n`;

    text += '## 概览\n\n';
    if (report.executive_summary) {
      text += `- 分析社区数: ${report.executive_summary.total_communities}\n`;
      text += `- 关键洞察数: ${report.executive_summary.key_insights}\n`;
      text += `- 最重要机会: ${report.executive_summary.top_opportunity}\n\n`;
    }

    // Pain Points
    if (report.pain_points && report.pain_points.length > 0) {
      text += '## 用户痛点\n\n';
      report.pain_points.forEach((pain, index: number) => {
        text += `${index + 1}. ${pain.description}\n`;
        text += `   - 提及次数: ${pain.frequency}\n`;
        text += `   - 情感分数: ${(pain.sentiment_score * 100).toFixed(0)}%\n`;
        if (pain.example_posts && pain.example_posts.length > 0) {
          text += `   - 来源社区: ${pain.example_posts.map(p => p.community).join(', ')}\n`;
        }
        text += '\n';
      });
    }

    // Competitors
    if (report.competitors && report.competitors.length > 0) {
      text += '## 竞品分析\n\n';
      report.competitors.forEach((comp, index: number) => {
        text += `${index + 1}. ${comp.name}\n`;
        text += `   - 提及次数: ${comp.mentions}\n`;
        text += `   - 情感倾向: ${comp.sentiment}\n`;
        if (comp.strengths && comp.strengths.length > 0) {
          text += `   - 优势: ${comp.strengths.join(', ')}\n`;
        }
        if (comp.weaknesses && comp.weaknesses.length > 0) {
          text += `   - 劣势: ${comp.weaknesses.join(', ')}\n`;
        }
        text += '\n';
      });
    }

    // Opportunities
    if (report.opportunities && report.opportunities.length > 0) {
      text += '## 商业机会\n\n';
      report.opportunities.forEach((opp, index: number) => {
        text += `${index + 1}. ${opp.description}\n`;
        text += `   - 相关性分数: ${(opp.relevance_score * 100).toFixed(0)}%\n`;
        text += `   - 潜在用户: ${opp.potential_users}\n`;
        text += '\n';
      });
    }

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `reddit-signal-scanner-${taskId}-${getTimestamp()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);

    console.log('[Export] Text export successful:', taskId);
  } catch (error) {
    console.error('[Export] Text export failed:', error);
    throw new Error('文本导出失败');
  }
}

