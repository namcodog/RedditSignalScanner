import { describe, it, expect } from 'vitest';

import { normalizePainPoints } from '@/lib/report/pain-points';
import type { PainPoint } from '@/types';

describe('normalizePainPoints', () => {
  it('根据情感分数补全严重程度并提取示例', () => {
    const rawPainPoints: PainPoint[] = [
      {
        description: '支付流程太复杂。用户需要多次点击才能完成订单。',
        frequency: 12,
        sentiment_score: -0.75,
        severity: undefined as unknown as PainPoint['severity'],
        example_posts: [],
        user_examples: [],
      },
    ];

    const normalized = normalizePainPoints(rawPainPoints);

    expect(normalized).toHaveLength(1);
    expect(normalized[0].severity).toBe('high');
    expect(normalized[0].userExamples).toEqual([
      '支付流程太复杂',
      '用户需要多次点击才能完成订单',
    ]);
  });
});
