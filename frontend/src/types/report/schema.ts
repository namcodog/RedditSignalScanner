import { z } from 'zod';

const nonNegativeInt = z.number().int().min(0);
const percentageInt = z.number().int().min(0).max(100);
const boundedProbability = z.number().min(0).max(1);

const evidenceItemSchema = z.object({
  title: z.string(),
  url: z.string().nullable().optional(),
  note: z.string(),
});

const actionItemSchema = z.object({
  problem_definition: z.string(),
  evidence_chain: z.array(evidenceItemSchema),
  suggested_actions: z.array(z.string()),
  confidence: boundedProbability,
  urgency: boundedProbability,
  product_fit: boundedProbability,
  priority: boundedProbability,
});

const executiveSummarySchema = z.object({
  total_communities: nonNegativeInt,
  key_insights: nonNegativeInt,
  top_opportunity: z.string(),
});

const statsSchema = z.object({
  total_mentions: nonNegativeInt,
  positive_mentions: nonNegativeInt,
  negative_mentions: nonNegativeInt,
  neutral_mentions: nonNegativeInt,
});

const overviewSchema = z.object({
  sentiment: z.object({
    positive: percentageInt,
    negative: percentageInt,
    neutral: percentageInt,
  }),
  top_communities: z.array(
    z.object({
      name: z.string(),
      mentions: nonNegativeInt,
      relevance: percentageInt,
      category: z.string().optional(),
      daily_posts: nonNegativeInt.optional(),
      avg_comment_length: nonNegativeInt.optional(),
      from_cache: z.boolean().optional(),
      members: nonNegativeInt.optional(),
    }),
  ),
});

const reportMetadataSchema = z.object({
  analysis_version: z.string(),
  confidence_score: boundedProbability,
  processing_time_seconds: z.number().min(0),
  cache_hit_rate: boundedProbability,
  total_mentions: nonNegativeInt,
  recovery_applied: z.string().optional(),
  fallback_quality: z
    .object({
      cache_coverage: boundedProbability,
      data_freshness_hours: z.number().min(0),
      estimated_accuracy: boundedProbability,
    })
    .optional(),
});

const painPointSchema = z.object({
  description: z.string(),
  frequency: nonNegativeInt,
  sentiment_score: z.number().min(-1).max(1),
  severity: z.enum(['low', 'medium', 'high']),
  example_posts: z.array(
    z.object({
      community: z.string(),
      content: z.string().optional(),
      upvotes: nonNegativeInt.optional(),
      url: z.string().optional(),
      author: z.string().optional(),
      permalink: z.string().optional(),
    }),
  ),
  user_examples: z.array(z.string()),
});

const competitorSchema = z.object({
  name: z.string(),
  mentions: nonNegativeInt,
  sentiment: z.string(),
  strengths: z.array(z.string()),
  weaknesses: z.array(z.string()),
  market_share: z.number().min(0).max(100).optional(),
});

const opportunitySchema = z.object({
  description: z.string(),
  relevance_score: boundedProbability,
  potential_users: z.string(),
  key_insights: z.array(z.string()),
});

const reportContentSchema = z.object({
  executive_summary: executiveSummarySchema,
  pain_points: z.array(painPointSchema),
  competitors: z.array(competitorSchema),
  opportunities: z.array(opportunitySchema),
  action_items: z.array(actionItemSchema),
});

export const reportResponseSchema = z.object({
  task_id: z.string(),
  status: z.string(),
  generated_at: z.string(),
  product_description: z.string().optional(),
  report_html: z.string().optional(),
  report: reportContentSchema,
  metadata: reportMetadataSchema,
  overview: overviewSchema,
  stats: statsSchema,
});

export type ReportResponseParsed = z.infer<typeof reportResponseSchema>;
