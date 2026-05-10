import { parseReportMarkdownSections } from '@/lib/report-markdown';
import { normalizeRedditUrl } from '@/lib/reddit-url';
import type { StructuredReport } from '@/types/report/response';

export const FIXED_REPORT_SECTION_TITLES = [
  { order: 1, title: '开篇概览' },
  { order: 2, title: '决策风向标' },
  { order: 3, title: '概览（市场健康度诊断）' },
  { order: 4, title: '核心战场推荐（画像分级）' },
  { order: 5, title: '用户痛点拆解' },
  { order: 6, title: '关键决策驱动力' },
  { order: 7, title: '商业机会' },
] as const;

const DECISION_CARD_ALIASES: Record<string, string[]> = {
  需求趋势: ['需求趋势'],
  '难题与攻略比': ['难题与攻略比', '问题与解决方案比', 'P/S'],
  核心社群: ['核心社群', '核心社群/社区', '高潜力社群'],
  落地机会: ['落地机会', '明确机会点', '机会点'],
};

const toSectionText = (markdown: string | null | undefined): Record<number, string> =>
  Object.fromEntries(
    parseReportMarkdownSections(markdown).map((section) => [
      section.order,
      [section.title, ...section.blocks].join('\n'),
    ])
  );

const includesAny = (value: string, candidates: string[]): boolean =>
  candidates.some((candidate) => value.includes(candidate));

const isClickableRedditUrl = (value: string | undefined): value is string =>
  Boolean(value) &&
  /^https?:\/\/(?:www\.)?reddit\.com\/r\/[^/]+\/comments\/[^/]+/i.test(value ?? '');

export const validateMarkdownCanonicalAlignment = (
  structured: StructuredReport | null | undefined,
  markdown: string | null | undefined
): string[] => {
  if (!structured) return ['missing canonical report'];

  const issues: string[] = [];
  const sections = parseReportMarkdownSections(markdown);
  const sectionText = toSectionText(markdown);

  if (sections.length !== FIXED_REPORT_SECTION_TITLES.length) {
    issues.push(
      `markdown section count mismatch: expected ${FIXED_REPORT_SECTION_TITLES.length}, got ${sections.length}`
    );
  }

  FIXED_REPORT_SECTION_TITLES.forEach((expected) => {
    const actual = sections.find((section) => section.order === expected.order);
    if (!actual) {
      issues.push(`missing markdown section ${expected.order}`);
      return;
    }
    if (actual.title.trim() !== expected.title) {
      issues.push(
        `section ${expected.order} title mismatch: expected "${expected.title}", got "${actual.title.trim()}"`
      );
    }
  });

  const section2 = sectionText[2] || '';
  structured.decision_cards.forEach((card) => {
    const aliases = DECISION_CARD_ALIASES[card.title] || [card.title];
    if (!includesAny(section2, aliases)) {
      issues.push(`decision card missing from markdown section 2: ${card.title}`);
    }
  });

  const section4 = sectionText[4] || '';
  structured.battlefields.forEach((battlefield) => {
    if (!section4.includes(battlefield.name)) {
      issues.push(`battlefield missing from markdown section 4: ${battlefield.name}`);
    }
  });

  const section5 = sectionText[5] || '';
  structured.pain_points.forEach((painPoint) => {
    if (!section5.includes(painPoint.title)) {
      issues.push(`pain point missing from markdown section 5: ${painPoint.title}`);
    }
  });

  const section6 = sectionText[6] || '';
  structured.drivers.forEach((driver) => {
    if (!section6.includes(driver.title)) {
      issues.push(`driver missing from markdown section 6: ${driver.title}`);
    }
  });

  const section7 = sectionText[7] || '';
  structured.opportunities.forEach((opportunity) => {
    if (!section7.includes(opportunity.title)) {
      issues.push(`opportunity missing from markdown section 7: ${opportunity.title}`);
    }
  });

  return issues;
};

export const collectCanonicalEvidenceLinks = (
  structured: StructuredReport | null | undefined
): string[] => {
  if (!structured) return [];

  const links = [
    ...(structured.pain_points || []).flatMap((painPoint) =>
      (painPoint.evidence_chain || [])
        .map((item) => normalizeRedditUrl(item.url))
        .filter(isClickableRedditUrl)
    ),
    ...(structured.opportunities || []).flatMap((opportunity) =>
      (opportunity.evidence_chain || [])
        .map((item) => normalizeRedditUrl(item.url))
        .filter(isClickableRedditUrl)
    ),
  ];

  return Array.from(new Set(links));
};

export const validateCanonicalEvidenceLinks = (
  structured: StructuredReport | null | undefined
): string[] => {
  if (!structured) return ['missing canonical report'];

  const issues: string[] = [];
  structured.pain_points.forEach((painPoint) => {
    (painPoint.evidence_chain || []).forEach((evidence) => {
      if (!isClickableRedditUrl(normalizeRedditUrl(evidence.url))) {
        issues.push(`pain evidence is not clickable: ${painPoint.title}`);
      }
    });
  });
  structured.opportunities.forEach((opportunity) => {
    (opportunity.evidence_chain || []).forEach((evidence) => {
      if (!isClickableRedditUrl(normalizeRedditUrl(evidence.url))) {
        issues.push(`opportunity evidence is not clickable: ${opportunity.title}`);
      }
    });
  });
  return issues;
};
