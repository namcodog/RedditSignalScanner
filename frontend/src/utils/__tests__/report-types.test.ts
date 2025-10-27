import { describe, it, expectTypeOf } from 'vitest';

import '@/types/report/metadata';
import '@/types/report/stats';
import '@/types/report/executive';
import '@/types/report/action-items';

import type { ReportMetadata } from '@/types/report/metadata';
import type { Stats } from '@/types/report/stats';
import type { ExecutiveSummary } from '@/types/report/executive';
import type { ActionItem } from '@/types/report/action-items';
import type { ReportResponse } from '@/types/report';

describe('report 类型模块', () => {
  it('暴露核心类型以便页面复用', () => {
    expectTypeOf<ReportResponse>().toMatchTypeOf<{
      metadata: ReportMetadata;
      stats: Stats;
      report: {
        executive_summary: ExecutiveSummary;
        action_items: ActionItem[];
      };
    }>();
  });
});
