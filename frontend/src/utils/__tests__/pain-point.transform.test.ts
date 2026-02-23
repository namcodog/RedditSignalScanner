import { describe, it, expect } from 'vitest';

import { normalizePainPoints } from '@/lib/report/pain-points';
import type { PainPoint } from '@/types';

describe('normalizePainPoints', () => {
  it('根据情感分数补全严重程度并提取示例', () => {
    const painPoints: PainPoint[] = [
      {
        text: '支付流程复杂',
        description: '支付流程太复杂。用户需要多次点击才能完成订单。',
        frequency: 10,
        sentiment_score: -0.8,
        severity: 'high' as const,
        example_posts: [],
        user_examples: [],
      },
    ];

    const normalized = normalizePainPoints(painPoints);

    expect(normalized).toHaveLength(1);
    expect(normalized[0]?.severity).toBe('high');
    expect(normalized[0]?.userExamples).toEqual([
      '支付流程太复杂',
      '用户需要多次点击才能完成订单',
    ]);
  });
});
