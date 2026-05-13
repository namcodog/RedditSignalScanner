export type ParsedMarkdownSection = {
  order: number;
  title: string;
  blocks: string[];
};

export const containsHtml = (value: string | null | undefined): boolean =>
  /<\/?[a-z][\s\S]*>/i.test(String(value ?? ''));

export const escapeHtml = (value: string): string =>
  value.replace(/[&<>]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[char] ?? char));

export const normalizeLine = (value: string): string => value.replace(/^[-*]\s*/, '').trim();

export const extractReportMarkdownTitle = (markdown: string | null | undefined): string | null => {
  const content = String(markdown ?? '');
  const match = content.match(/^#\s+(.+)$/m);
  return match?.[1]?.trim() ?? null;
};

export const parseReportMarkdownSections = (markdown: string | null | undefined): ParsedMarkdownSection[] => {
  const content = String(markdown ?? '').trim();
  if (!content) return [];

  const sections: ParsedMarkdownSection[] = [];
  const matches = content.matchAll(/##\s+(\d+)\.\s+([^\n]+)\n([\s\S]*?)(?=\n##\s+\d+\.\s+|$)/g);

  for (const match of matches) {
    const order = Number(match[1]);
    const title = String(match[2] ?? '').trim();
    const body = String(match[3] ?? '').trim();
    if (!Number.isFinite(order) || !title || !body) continue;

    sections.push({
      order,
      title,
      blocks: body
        .split(/\n\s*\n/)
        .map((block) => block.trim())
        .filter(Boolean),
    });
  }

  return sections;
};
