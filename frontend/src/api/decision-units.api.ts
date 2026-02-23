import { apiClient } from './client';

export interface DecisionUnit {
  id: string;
  task_id: string;
  signal_type: string;
  title: string;
  summary: string;
  confidence: number;
  created_at: string;
  evidence?: Record<string, any>;
}

export interface DecisionUnitListResponse {
  items: DecisionUnit[];
  total: number;
}

export interface DecisionUnitFeedbackRequest {
  label: 'correct' | 'incorrect' | 'mismatch' | 'valuable' | 'worthless';
  note?: string;
  evidence_id?: string;
}

export const getDecisionUnits = async (params?: { signal_type?: string; limit?: number }) => {
  const response = await apiClient.get<DecisionUnitListResponse>('/decision-units', { params });
  return response.data;
};

export const getDecisionUnitDetail = async (id: string) => {
  const response = await apiClient.get<DecisionUnit>(`/decision-units/${id}`);
  return response.data;
};

export const submitDecisionUnitFeedback = async (id: string, feedback: DecisionUnitFeedbackRequest) => {
  const response = await apiClient.post(`/decision-units/${id}/feedback`, feedback);
  return response.data;
};
