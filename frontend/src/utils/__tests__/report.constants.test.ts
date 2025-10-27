import { describe, expect, it } from 'vitest';

import {
  REPORT_CACHE_TTL_MS_DEFAULT,
  REPORT_POLL_INTERVAL_MS,
  REPORT_MAX_POLL_ATTEMPTS,
  REPORT_LOADING_STAGES,
  REPORT_EXPORT_STAGES,
} from '@/config/report';

describe('report config 常量', () => {
  it('应集中导出报告的默认时序参数', () => {
    expect(REPORT_CACHE_TTL_MS_DEFAULT).toBe(60_000);
    expect(REPORT_POLL_INTERVAL_MS).toBe(2000);
    expect(REPORT_MAX_POLL_ATTEMPTS).toBe(150);
  });

  it('应提供加载阶段的元数据并按进度排序', () => {
    expect(REPORT_LOADING_STAGES.map(stage => stage.id)).toEqual([
      'cache',
      'fetch',
      'hydrate',
      'render',
    ]);
    expect(REPORT_LOADING_STAGES[0].progress).toBeLessThan(REPORT_LOADING_STAGES[3].progress);
    expect(REPORT_LOADING_STAGES.every(stage => stage.progress >= 0 && stage.progress <= 100)).toBe(true);
  });

  it('应导出导出阶段信息并以完成阶段结束', () => {
    expect(REPORT_EXPORT_STAGES.map(stage => stage.id)).toEqual([
      'prepare',
      'format',
      'history',
      'complete',
    ]);
    expect(REPORT_EXPORT_STAGES.find(stage => stage.id === 'complete')?.progress).toBe(100);
  });
});
