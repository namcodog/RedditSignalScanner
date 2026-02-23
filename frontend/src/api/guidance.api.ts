import { apiClient } from './client';

export interface GuidanceExample {
  title: string;
  prompt: string;
  tags?: string[];
  example_id?: string | null;
}

export interface GuidanceInputResponse {
  placeholder: string;
  tips: string[];
  examples: GuidanceExample[];
}

export const getInputGuidance = async (): Promise<GuidanceInputResponse> => {
  const response = await apiClient.get<GuidanceInputResponse>('/guidance/input');
  return response.data;
};
