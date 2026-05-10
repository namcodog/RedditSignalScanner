import type { ReactNode } from 'react';
import clsx from 'clsx';

import {
  containsHtml,
  escapeHtml,
  extractReportMarkdownTitle,
  normalizeLine,
  parseReportMarkdownSections,
} from '@/lib/report-markdown';

type EditorialReportDocumentProps = {
  markdown?: string | null | undefined;
  html?: string | null | undefined;
  emptyMessage?: string;
  className?: string;
};

const renderMarkdownBlock = (block: string, key: string): ReactNode => {
  const lines = block
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) return null;

  const isList = lines.every((line) => /^[-*]\s+/.test(line));
  if (isList) {
    return (
      <ul key={key} className="space-y-2 pl-5 text-[0.98rem] leading-8 text-muted-foreground marker:text-primary/70">
        {lines.map((line, index) => (
          <li key={`${key}-item-${index}`} className="break-words">
            {normalizeLine(line)}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div key={key} className="space-y-3">
      {lines.map((line, index) => {
        const emphasisMatch = line.match(/^\*\*(.+)\*\*$/);
        if (emphasisMatch?.[1]) {
          return (
            <h4 key={`${key}-line-${index}`} className="text-[1rem] font-semibold tracking-[0.01em] text-foreground">
              {emphasisMatch[1].trim()}
            </h4>
          );
        }

        return (
          <p key={`${key}-line-${index}`} className="break-words text-[0.98rem] leading-8 text-muted-foreground">
            {line}
          </p>
        );
      })}
    </div>
  );
};

const EditorialReportDocument = ({
  markdown,
  html,
  emptyMessage = '这份完整报告暂时还没有生成文档版本。',
  className,
}: EditorialReportDocumentProps) => {
  const sections = parseReportMarkdownSections(markdown);
  const title = extractReportMarkdownTitle(markdown);

  if (sections.length > 0) {
    return (
      <div className={clsx('space-y-5', className)}>
        {title ? (
          <section className="editorial-reading-surface rounded-[26px] px-5 py-5 md:px-6">
            <div className="surface-section-kicker">完整正文</div>
            <h3 className="mt-3 max-w-4xl text-[1.45rem] font-semibold leading-[1.35] text-foreground md:text-[1.7rem]">
              {title}
            </h3>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
              这里保留完整论证和动作建议，方便你把判断、依据和下一步一次看清。
            </p>
          </section>
        ) : null}

        {sections.map((section) => (
          <section key={section.order} className="editorial-reading-surface rounded-[26px] px-5 py-5 md:px-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className="editorial-order-badge">{String(section.order).padStart(2, '0')}</span>
              <h3 className="font-display text-[1.3rem] font-semibold leading-tight text-foreground md:text-[1.55rem]">
                {section.order}. {section.title}
              </h3>
            </div>
            <div className="mt-5 space-y-4">
              {section.blocks.map((block, index) => renderMarkdownBlock(block, `${section.order}-${index}`))}
            </div>
          </section>
        ))}
      </div>
    );
  }

  if (containsHtml(html)) {
    return (
      <article
        className={clsx(
          'editorial-prose editorial-reading-html rounded-[26px] border border-border/70 bg-background/78 px-5 py-6 md:px-8',
          className,
        )}
        dangerouslySetInnerHTML={{ __html: html ?? '' }}
      />
    );
  }

  if (markdown) {
    return (
      <pre
        className={clsx(
          'editorial-reading-fallback whitespace-pre-wrap break-words rounded-[26px] border border-border/70 bg-background/78 px-5 py-6 font-sans text-[0.98rem] leading-8 text-foreground md:px-8',
          className,
        )}
        dangerouslySetInnerHTML={{ __html: escapeHtml(markdown) }}
      />
    );
  }

  return <p className="text-sm leading-7 text-muted-foreground">{emptyMessage}</p>;
};

export default EditorialReportDocument;
