import { apiClient } from '../client';

export interface CommunityGovernanceSnapshot {
  summary: Record<string, any>;
  effective_communities: Record<string, any>[];
  candidate_communities: Record<string, any>[];
  garbage_communities: Record<string, any>;
  historical_shells: Record<string, any>[];
  anomalies: Record<string, any>[];
}

export const getCommunityGovernanceSummary = async (): Promise<CommunityGovernanceSnapshot> => {
  const response = await apiClient.get<CommunityGovernanceSnapshot>('/admin/communities/governance/summary');
  return response.data;
};

export const getEffectiveCommunities = async (): Promise<{ items: Record<string, any>[]; total: number }> => {
  const response = await apiClient.get<{ items: Record<string, any>[]; total: number }>(
    '/admin/communities/governance/effective',
  );
  return response.data;
};

export const cleanupCommunityGovernanceDev = async (
  payload: { dry_run?: boolean } = {},
): Promise<Record<string, any>> => {
  const response = await apiClient.post<Record<string, any>>('/admin/communities/governance/cleanup-dev', {
    dry_run: payload.dry_run ?? true,
  });
  return response.data;
};
