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
import type { EntitySummary } from '@/types/report/entity';
import type { Sources } from '@/types';

describe('report 类型模块', () => {
  it('暴露核心类型以便页面复用', () => {
    expectTypeOf<ReportResponse['metadata']>().toMatchTypeOf<ReportMetadata>();
    expectTypeOf<ReportResponse['stats']>().toMatchTypeOf<Stats>();
    expectTypeOf<ReportResponse['report']['executive_summary']>().toMatchTypeOf<ExecutiveSummary>();
    expectTypeOf<ReportResponse['report']['action_items']>().toMatchTypeOf<ActionItem[]>();
    expectTypeOf<ReportResponse['report']['entity_summary']>().toMatchTypeOf<EntitySummary>();
    expectTypeOf<ReportResponse['sources']>().toMatchTypeOf<Sources | null | undefined>();
  });
});
