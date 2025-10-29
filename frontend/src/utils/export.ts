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
    const timestamp = getTimestamp();
    const baseName = `reddit-signal-scanner-${taskId}-${timestamp}`;

    const downloads: Array<{ filename: string; content: string }> = [];

    if (report.pain_points && report.pain_points.length > 0) {
      const rows = report.pain_points.map((pain, index) => {
        const communities = pain.example_posts?.map(p => p.community).join('; ') ?? '';
        return [
          String(index + 1),
          pain.description,
          String(pain.frequency),
          (pain.sentiment_score * 100).toFixed(0),
          communities,
        ];
      });

      const csv = buildCSV(
        ['Rank', 'Description', 'Frequency', 'SentimentScore(%)', 'Communities'],
        rows
      );
      downloads.push({
        filename: `${baseName}-pain-points.csv`,
        content: csv,
      });
    }

    if (report.competitors && report.competitors.length > 0) {
      const rows = report.competitors.map((comp, index) => [
        String(index + 1),
        comp.name,
        String(comp.mentions),
        String(comp.sentiment),
        comp.strengths?.join('; ') ?? '',
        comp.weaknesses?.join('; ') ?? '',
      ]);

      const csv = buildCSV(
        ['Rank', 'Name', 'Mentions', 'Sentiment', 'Strengths', 'Weaknesses'],
        rows
      );
      downloads.push({
        filename: `${baseName}-competitors.csv`,
        content: csv,
      });
    }

    if (report.opportunities && report.opportunities.length > 0) {
      const rows = report.opportunities.map((opp, index) => [
        String(index + 1),
        opp.description,
        (opp.relevance_score * 100).toFixed(0),
        opp.potential_users,
        opp.key_insights?.join('; ') ?? '',
      ]);

      const csv = buildCSV(
        ['Rank', 'Description', 'Relevance(%)', 'PotentialUsers', 'KeyInsights'],
        rows
      );
      downloads.push({
        filename: `${baseName}-opportunities.csv`,
        content: csv,
      });
    }

    if (report.action_items && report.action_items.length > 0) {
      const rows = report.action_items.map((action, index) => [
        String(index + 1),
        action.problem_definition,
        (action.priority * 100).toFixed(0),
        (action.confidence * 100).toFixed(0),
        (action.urgency * 100).toFixed(0),
        (action.product_fit * 100).toFixed(0),
        action.evidence_chain?.map(item => item.note || item.title).join('; ') ?? '',
      ]);

      const csv = buildCSV(
        ['Rank', 'ProblemDefinition', 'Priority(%)', 'Confidence(%)', 'Urgency(%)', 'ProductFit(%)', 'Evidence'],
        rows
      );
      downloads.push({
        filename: `${baseName}-action-items.csv`,
        content: csv,
      });
    }

    if (report.entity_summary) {
      const categories: Array<{ category: string; entries: typeof report.entity_summary.brands }> = [
        { category: 'brands', entries: report.entity_summary.brands ?? [] },
        { category: 'features', entries: report.entity_summary.features ?? [] },
        { category: 'pain_points', entries: report.entity_summary.pain_points ?? [] },
      ];

      const rows = categories.flatMap(({ category, entries }) =>
        entries.map(item => [category, item.name, String(item.mentions)])
      );

      if (rows.length > 0) {
        const csv = buildCSV(['Category', 'Entity', 'Mentions'], rows);
        downloads.push({
          filename: `${baseName}-entities.csv`,
          content: csv,
        });
      }
    }

    if (downloads.length === 0) {
      throw new Error('没有可导出的数据');
    }

    downloads.forEach(({ filename, content }) => triggerDownload(filename, content, 'text/csv;charset=utf-8'));

    console.log('[Export] CSV export successful:', downloads.map(({ filename }) => filename));
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

function buildCSV(headers: string[], rows: string[][]): string {
  const headerLine = headers.join(',');
  const rowLines = rows.map(fields =>
    fields
      .map(field => `"${escapeCSV(field)}"`)
      .join(',')
  );
  return [headerLine, ...rowLines].join('\n');
}

function triggerDownload(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
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

    if (report.action_items && report.action_items.length > 0) {
      text += '## 行动建议\n\n';
      report.action_items.forEach((action, index: number) => {
        text += `${index + 1}. ${action.problem_definition}\n`;
        text += `   - 优先级: ${(action.priority * 100).toFixed(0)}%\n`;
        text += `   - 信心 / 紧迫 / 契合: ${(action.confidence * 100).toFixed(0)}% / ${(action.urgency * 100).toFixed(0)}% / ${(action.product_fit * 100).toFixed(0)}%\n`;
        if (action.suggested_actions && action.suggested_actions.length > 0) {
          text += `   - 建议行动: ${action.suggested_actions.join('; ')}\n`;
        }
        if (action.evidence_chain && action.evidence_chain.length > 0) {
          text += `   - 证据链: ${action.evidence_chain.map(e => e.title).join('; ')}\n`;
        }
        text += '\n';
      });
    }

    if (report.entity_summary) {
      text += '## 关键实体\n\n';
      const sections: Array<[string, typeof report.entity_summary.brands]> = [
        ['品牌', report.entity_summary.brands ?? []],
        ['功能', report.entity_summary.features ?? []],
        ['痛点词', report.entity_summary.pain_points ?? []],
      ];

      sections.forEach(([label, items]) => {
        if (!items.length) {
          return;
        }
        text += `- ${label}: `;
        text += items
          .map(item => `${item.name} (${item.mentions})`)
          .join(', ');
        text += '\n';
      });

      text += '\n';
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
