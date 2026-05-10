import type { PainPoint } from '@/types/analysis.types';
import type { StructuredPainPoint } from '@/types/report/response';

type PainEvidenceSource = Pick<
  PainPoint,
  'description' | 'text' | 'example_posts' | 'user_examples'
>;

type PainEvidenceSourceLike = Partial<PainEvidenceSource>;

const collectChineseTokens = (value: string): string[] => {
  const matches = value.match(/[\u4e00-\u9fff]{2,}/g) ?? [];
  const tokens: string[] = [];
  matches.forEach((match) => {
    tokens.push(match);
    if (match.length <= 2) return;
    for (let index = 0; index < match.length - 1; index += 1) {
      tokens.push(match.slice(index, index + 2));
    }
  });
  return tokens;
};

const tokenize = (value: string): string[] => {
  const normalized = value.toLowerCase();
  const englishTokens = normalized.match(/[a-z0-9]{2,}/g) ?? [];
  return [...englishTokens, ...collectChineseTokens(value)];
};

const buildStructuredPainAnchor = (painPoint: StructuredPainPoint): string =>
  [
    painPoint.title,
    ...(painPoint.user_voices ?? []),
    painPoint.data_impression ?? '',
    painPoint.interpretation,
  ]
    .filter(Boolean)
    .join(' ');

const buildEvidenceSourceAnchor = (painPoint: PainEvidenceSource): string =>
  [
    painPoint.description,
    painPoint.text ?? '',
    ...(painPoint.user_examples ?? []),
    ...((painPoint.example_posts ?? []).map((post) => post.content ?? '') ?? []),
  ]
    .filter(Boolean)
    .join(' ');

const scorePainAlignment = (
  structuredPainPoint: StructuredPainPoint,
  source: PainEvidenceSource
): number => {
  const structuredAnchor = buildStructuredPainAnchor(structuredPainPoint);
  const sourceAnchor = buildEvidenceSourceAnchor(source);
  if (!structuredAnchor || !sourceAnchor) return 0;

  const structuredTokens = new Set(tokenize(structuredAnchor));
  const sourceTokens = new Set(tokenize(sourceAnchor));
  let score = 0;

  structuredTokens.forEach((token) => {
    if (token.length > 1 && sourceTokens.has(token)) {
      score += token.length >= 4 ? 3 : 2;
    }
  });

  const title = structuredPainPoint.title.trim();
  const sourceTitle = `${source.description} ${source.text ?? ''}`.trim();
  if (title && sourceTitle) {
    if (sourceTitle.includes(title) || title.includes(sourceTitle)) {
      score += 8;
    }
  }

  return score;
};

export const alignPainEvidenceSources = (
  structuredPainPoints: StructuredPainPoint[] | undefined,
  rawPainPoints: PainEvidenceSource[] | undefined
): PainEvidenceSourceLike[] => {
  const structured = structuredPainPoints ?? [];
  const raw = rawPainPoints ?? [];
  const used = new Set<number>();

  return structured.map((painPoint, index) => {
    let bestIndex = -1;
    let bestScore = -1;

    raw.forEach((source, sourceIndex) => {
      if (used.has(sourceIndex)) return;
      const score = scorePainAlignment(painPoint, source);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = sourceIndex;
      }
    });

    if (bestIndex >= 0 && bestScore > 0) {
      used.add(bestIndex);
      return raw[bestIndex]!;
    }

    if (raw[index] && !used.has(index)) {
      used.add(index);
      return raw[index]!;
    }

    return { example_posts: [] };
  });
};
