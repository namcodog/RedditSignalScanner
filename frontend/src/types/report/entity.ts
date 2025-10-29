export interface EntityMatch {
  name: string;
  mentions: number;
}

export interface EntitySummary {
  brands: EntityMatch[];
  features: EntityMatch[];
  pain_points: EntityMatch[];
}
