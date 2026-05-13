export type CluePrimaryTag = 'validate' | 'write' | 'both';
export type ClueSecondaryTag = 'trend' | 'switch' | 'pitfall' | 'opportunity';
export type ClueListTab = 'all' | 'validate' | 'write';
export type ClueBoxTab = 'favorites' | 'copied';

export interface QuotePreview {
  text: string;
  community: string;
  permalink: string;
}

export interface ValidationSheet {
  hypothesis: string;
  target_user: string;
  next_action: string;
  success_signal: string;
  stop_signal: string;
  copy_payload: string;
}

export interface ContentSheet {
  core_thesis: string;
  angle: string;
  title_hooks: string[];
  outline: string[];
  quote_pack: string[];
  copy_payload: string;
}

export interface ClueCard {
  id: string;
  title: string;
  one_liner: string;
  audience: string;
  why_now: string;
  primary_tag: CluePrimaryTag;
  secondary_tags: ClueSecondaryTag[];
  preview_quotes: QuotePreview[];
  hotpost_detail_url: string;
  published_at: string;
  favorited: boolean;
}

export interface ClueDetail extends ClueCard {
  source_meta: {
    observation_topic: string;
    time_window_days: number;
    thread_count: number;
    community_count: number;
    intent_tags: string[];
  };
  full_quotes: QuotePreview[];
  validation_sheet?: ValidationSheet | null;
  content_sheet?: ContentSheet | null;
}

export interface ClueListResponse {
  items: ClueCard[];
  next_cursor: string | null;
}
