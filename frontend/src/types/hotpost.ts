// frontend/src/types/hotpost.ts

export type HotPostMode = 'trending' | 'rant' | 'opportunity';
export type TimeFilter = 'week' | 'month' | 'year' | 'all';
export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'none';

export interface HotPostRequest {
  query: string;
  mode?: HotPostMode;
  subreddits?: string[]; // Max 10
  time_filter?: TimeFilter;
  limit?: number; // 1-100, default 30
}

export interface HotPost {
  rank: number;
  id: string;
  title: string;
  body_preview: string;
  score: number;
  num_comments: number;
  heat_score?: number;
  rant_score?: number;
  rant_signals?: string[];
  resonance_count?: number;
  subreddit: string;
  author: string;
  reddit_url: string;
  created_utc: number;
  signals: string[];
  signal_score: number;
  why_relevant?: string;
  why_important?: string;
  top_comments: Array<{
    author: string;
    body: string;
    score: number;
    id?: string;
    comment_fullname?: string;
    permalink?: string;
  }>;
}

// --- Rant Mode Structures ---

export interface PainPoint {
  rank?: number;
  category: string;
  category_en?: string;
  description?: string;
  severity?: 'critical' | 'high' | 'medium' | 'low' | string;
  mentions?: number;
  percentage?: number;
  key_takeaway?: string;
  user_voice?: string;
  business_implication?: string;
  sample_quotes?: string[];
  evidence_urls?: string[];
  evidence?: Array<{
    title?: string;
    score?: number;
    comments?: number;
    url?: string;
    key_quote?: string;
  }>;
  evidence_posts?: HotPost[];
}

export interface CompetitorMention {
  name: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  mentions: number;
  sentiment_score?: number;
  common_praise?: string[];
  common_complaint?: string[];
  typical_context?: string;
  sample_quote?: string;
  vs_adobe?: string;
  evidence_quote?: string;
}

export interface MigrationIntent {
  already_left?: string; // e.g. "20%"
  considering?: string;
  staying_reluctantly?: string;
  total_mentions?: number;
  percentage?: number;
  status_distribution?: Record<string, number>;
  destinations?: Array<{ name?: string; mentions?: number; sentiment?: string }>;
  key_quote?: string;
}

// --- Opportunity Mode Structures ---

export interface Opportunity {
  rank?: number;
  need?: string; // The unmet need
  need_en?: string;
  urgency?: string;
  mentions?: number;
  summary?: string;
  mentions?: number;
  me_too_count?: number; // demand_signal
  willingness_to_pay?: 'high' | 'medium' | 'low';
  pay_evidence?: string;
  price_range?: string;
  key_takeaway?: string;
  user_voice?: string;
  current_workarounds?: Array<{ solution?: string; pain?: string; name?: string; satisfaction?: string }>;
  opportunity_signal?: 'high' | 'medium' | 'low';
  evidence?: Array<{
    title?: string;
    score?: number;
    comments?: number;
    me_too_comments?: number;
    subreddit?: string;
    url?: string;
    key_quote?: string;
  }>;
  evidence_posts?: HotPost[];
}

export interface ExistingTool {
    name: string;
    sentiment: 'positive' | 'neutral' | 'negative';
    mentions?: number;
    sentiment_score?: number;
    common_praise?: string[];
    common_complaint?: string[];
    praised_for?: string[];
    criticized_for?: string[];
    pros?: string[]; // legacy alias
    cons?: string[]; // legacy alias
    gap_analysis?: string;
}

export interface UserSegment {
    segment?: string;
    percentage?: string;
    core_need?: string;
    key_need?: string;
    price_sensitivity?: string;
    segment_name?: string; // legacy alias
    needs?: string[]; // legacy alias
    typical_profile?: string; // legacy alias
    typical_quote?: string;
}

export interface MarketOpportunity {
  gap?: string;
  target_user?: string;
  pricing_hint?: string;
  gtm_channel?: string;
  strength?: string;
  unmet_gap?: string;
  demand_signal?: string;
  competition_level?: string;
  recommendation?: string;
}

// --- Trending Mode Structures ---

export interface TrendingTopic {
    rank: number;
    topic: string;
    heat_score: number;
    time_trend: '新兴🆕' | '持续热门' | '下降中↓' | string;
    key_takeaway: string;
    evidence: Array<{
        title: string;
        score: number;
        comments?: number;
        subreddit: string;
        url: string;
        key_quote?: string;
    }>;
    evidence_posts?: HotPost[];
}

// --- Main Response ---

export interface HotPostResponse {
  query_id: string;
  query: string;
  mode: HotPostMode;
  search_time: string;
  from_cache: boolean;
  status?: 'queued' | 'waiting' | 'processing' | 'completed' | 'success' | 'failed';
  
  // Queue Info
  position?: number;
  estimated_wait_seconds?: number;

  // Summary & Stats
  summary: string;
  markdown_report?: string;
  confidence: ConfidenceLevel;
  evidence_count: number;
  community_distribution: Record<string, number | string>;
  sentiment_overview?: {
    positive: number;
    neutral: number;
    negative: number;
  };
  rant_intensity?: Record<string, number>;
  need_urgency?: Record<string, number>;
  opportunity_strength?: string;

  // Core Data
  top_posts: HotPost[];
  key_comments?: any[];
  top_rants?: HotPost[];
  top_discovery_posts?: HotPost[];

  // Mode Specific - Rant
  pain_points?: PainPoint[];
  competitor_mentions?: CompetitorMention[];
  migration_intent?: MigrationIntent;

  // Mode Specific - Opportunity
  opportunities?: Opportunity[];
  unmet_needs?: Opportunity[]; // Backend might send 'unmet_needs', let's support both or alias
  existing_tools?: ExistingTool[];
  user_segments?: UserSegment[];
  market_opportunity?: MarketOpportunity | string;

  // Mode Specific - Trending
  trending_keywords?: string[];
  topics?: TrendingTopic[]; // Backend 'topics'

  reliability_note?: string;
  next_steps?: {
    deepdive_available?: boolean;
    deepdive_token?: string | null;
    suggested_keywords?: string[];
  };
  notes?: string[];
  debug_info?: {
    query_source?: string;
    search_query?: string;
    query_parts?: string[];
    keywords?: string[];
    time_filter?: string;
    sort?: string;
    subreddits?: string[];
    raw_posts?: number;
    filtered_posts?: number;
    relevance_filtered?: number;
  };

  // Meta
  communities: Array<string | {
    name: string;
    subscribers?: number;
    active_users?: number;
    description?: string;
  }>;
  related_queries: string[];
}

export interface DeepDiveRequest {
  query_id: string;
  product_desc?: string;
  seed_subreddits?: string[];
}

export interface DeepDiveResponse {
  deepdive_token: string;
  expires_in_seconds: number;
}
