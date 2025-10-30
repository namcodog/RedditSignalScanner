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
      category: z.string().nullish(),
      daily_posts: nonNegativeInt.nullish(),
      avg_comment_length: nonNegativeInt.nullish(),
      from_cache: z.boolean().nullish(),
      members: nonNegativeInt.nullish(),
    }),
  ),
  // P1: 补充“Top N of Total + 来源”
  total_communities: nonNegativeInt.optional(),
  top_n: nonNegativeInt.optional(),
  seed_source: z.string().nullish().optional(),
});

const reportMetadataSchema = z.object({
  analysis_version: z.string(),
  confidence_score: boundedProbability,
  processing_time_seconds: z.number().min(0),
  cache_hit_rate: boundedProbability,
  total_mentions: nonNegativeInt,
  recovery_applied: z.string().nullish(),
  fallback_quality: z
    .object({
      cache_coverage: boundedProbability,
      data_freshness_hours: z.number().min(0),
      estimated_accuracy: boundedProbability,
    })
    .nullish(),
});

const painPointSchema = z.object({
  description: z.string(),
  frequency: nonNegativeInt,
  sentiment_score: z.number().min(-1).max(1),
  severity: z.enum(['low', 'medium', 'high']),
  example_posts: z.array(
    z.object({
      community: z.string(),
      content: z.string().nullish(),
      upvotes: nonNegativeInt.nullish(),
      url: z.string().nullish(),
      author: z.string().nullish(),
      permalink: z.string().nullish(),
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
  market_share: z.number().min(0).max(100).nullish(),
});

const opportunitySchema = z.object({
  description: z.string(),
  relevance_score: boundedProbability,
  potential_users: z.string(),
  key_insights: z.array(z.string()),
});

const entityMatchSchema = z.object({
  name: z.string(),
  mentions: nonNegativeInt,
});

const entitySummarySchema = z.object({
  brands: z.array(entityMatchSchema),
  features: z.array(entityMatchSchema),
  pain_points: z.array(entityMatchSchema),
});

const reportContentSchema = z.object({
  executive_summary: executiveSummarySchema,
  pain_points: z.array(painPointSchema),
  competitors: z.array(competitorSchema),
  opportunities: z.array(opportunitySchema),
  action_items: z.array(actionItemSchema),
  entity_summary: entitySummarySchema,
});

export const reportResponseSchema = z.object({
  task_id: z.string(),
  status: z.string(),
  generated_at: z.string(),
  product_description: z.string().nullish(),
  report_html: z.string().nullish(),
  report: reportContentSchema,
  metadata: reportMetadataSchema,
  overview: overviewSchema,
  stats: statsSchema,
});

export type ReportResponseParsed = z.infer<typeof reportResponseSchema>;
