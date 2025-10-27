import { render, screen } from '@testing-library/react';
import { describe, it } from 'vitest';

import { TranslationProvider } from '@/i18n/TranslationProvider';
import { ActionItemsList } from '../ActionItem';

describe('ActionItemsList 空状态', () => {
  it('应复用共享空状态组件并展示翻译文案', () => {
    render(
      <TranslationProvider initialLocale="zh">
        <ActionItemsList items={[]} />
      </TranslationProvider>
    );

    const empty = screen.getByTestId('shared-empty-state');
    expect(empty).toHaveTextContent('暂无行动建议');
  });
});
