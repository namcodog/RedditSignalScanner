export interface PainPointViewModel {
  description: string;
  frequency: number;
  sentimentScore: number;
  severity: 'low' | 'medium' | 'high';
  userExamples: string[];
}
