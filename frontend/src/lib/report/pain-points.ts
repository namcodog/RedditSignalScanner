import type { PainPoint } from '@/types';
import type { PainPointViewModel } from '@/types/report/pain-point';

const VALID_SEVERITIES = new Set(['low', 'medium', 'high'] as const);

const deriveSeverity = (
  pain: PainPoint
): PainPointViewModel['severity'] => {
  const incoming = (pain as Partial<PainPoint>).severity;
  if (incoming && VALID_SEVERITIES.has(incoming)) {
    return incoming;
  }

  if (pain.sentiment_score <= -0.6) {
    return 'high';
  }
  if (pain.sentiment_score <= -0.3) {
    return 'medium';
  }
  return 'low';
};

const extractUserExamples = (pain: PainPoint): string[] => {
  const examples = Array.isArray((pain as Partial<PainPoint>).user_examples)
    ? (pain as Partial<PainPoint>).user_examples ?? []
    : [];

  if (examples.length > 0) {
    return examples.map(example => example.trim()).filter(Boolean).slice(0, 3);
  }

  const sentences = pain.description
    .split(/[。.!?!？]/u)
    .map(sentence => sentence.trim())
    .filter(Boolean);

  return sentences.slice(0, 3);
};

export const normalizePainPoints = (
  painPoints: PainPoint[]
): PainPointViewModel[] =>
  painPoints.map(pain => ({
    description: pain.description,
    frequency: pain.frequency,
    sentimentScore: pain.sentiment_score,
    severity: deriveSeverity(pain),
    userExamples: extractUserExamples(pain),
  }));
