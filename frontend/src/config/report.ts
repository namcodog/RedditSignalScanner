export interface ProgressStage {
  id: string;
  labelKey: string;
  progress: number;
}

export const REPORT_CACHE_TTL_MS_DEFAULT = 60_000;
export const REPORT_POLL_INTERVAL_MS = 2000;
export const REPORT_MAX_POLL_ATTEMPTS = 150;

export const REPORT_LOADING_STAGES: ReadonlyArray<ProgressStage> = Object.freeze([
  { id: 'cache', labelKey: 'report.progress.cache', progress: 15 },
  { id: 'fetch', labelKey: 'report.progress.fetch', progress: 55 },
  { id: 'hydrate', labelKey: 'report.progress.hydrate', progress: 75 },
  { id: 'render', labelKey: 'report.progress.render', progress: 95 },
]);

export const REPORT_EXPORT_STAGES: ReadonlyArray<ProgressStage> = Object.freeze([
  { id: 'prepare', labelKey: 'report.export.stage.prepare', progress: 20 },
  { id: 'format', labelKey: 'report.export.stage.format', progress: 55 },
  { id: 'history', labelKey: 'report.export.stage.history', progress: 85 },
  { id: 'complete', labelKey: 'report.export.stage.complete', progress: 100 },
]);

export type ExportStageId = (typeof REPORT_EXPORT_STAGES)[number]['id'];
