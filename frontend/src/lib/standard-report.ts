import type { ReportResponse } from '@/types/report/response';

export type StandardReportSnapshot = {
  slug: string;
  title: string;
  prompt: string;
  topic_profile_id: string;
  task_id: string;
  validated_at: string;
  summary: Record<string, unknown>;
  report: ReportResponse;
};

export type StandardReportManifestItem = Pick<
  StandardReportSnapshot,
  'slug' | 'title' | 'prompt' | 'topic_profile_id' | 'task_id' | 'validated_at' | 'summary'
> & { snapshot_url: string };

export const fetchJson = async <T,>(url: string): Promise<T> => {
  const response = await fetch(url, { credentials: 'same-origin' });
  if (!response.ok) {
    throw new Error(`Failed to load ${url}`);
  }
  return (await response.json()) as T;
};

export const loadStandardReportSnapshot = async (slug: string): Promise<StandardReportSnapshot> => {
  const manifest = await fetchJson<StandardReportManifestItem[]>('/topic-profile-reports/index.json');
  const target = manifest.find((item) => item.slug === slug);
  if (!target) {
    throw new Error('snapshot not found');
  }
  return fetchJson<StandardReportSnapshot>(target.snapshot_url);
};

export const formatStandardSnapshotTime = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

export const buildStandardReportPrefillState = (
  prompt: string,
  options?: {
    title?: string;
  }
) => ({
  prefillSource: 'standard-report' as const,
  prefillHint: '刚看完这份标准样板。输入框已经清空，直接按你的真实问题重写就行。',
  ...(options?.title ? { prefillStandardTitle: options.title } : {}),
  ...(prompt ? { prefillPromptSuggestion: prompt } : {}),
});
