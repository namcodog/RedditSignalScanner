export type ExportFormat = 'json' | 'csv' | 'text';

export interface ExportHistoryEntry {
  taskId: string;
  format: ExportFormat;
  timestamp: string;
}

const STORAGE_KEY = 'rss_export_history_v1';
const MAX_HISTORY_ITEMS = 10;

const safeStorage = (): Storage | null => {
  try {
    if (typeof window === 'undefined') return null;
    return window.localStorage;
  } catch {
    return null;
  }
};

export const getExportHistory = (): ExportHistoryEntry[] => {
  const storage = safeStorage();
  if (!storage) return [];

  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ExportHistoryEntry[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(item =>
      item && typeof item.taskId === 'string' && typeof item.format === 'string' && typeof item.timestamp === 'string'
    );
  } catch {
    return [];
  }
};

export const addExportHistoryEntry = (entry: ExportHistoryEntry): ExportHistoryEntry[] => {
  const storage = safeStorage();
  const existing = getExportHistory().filter(item =>
    !(item.taskId === entry.taskId && item.format === entry.format && item.timestamp === entry.timestamp)
  );
  const updated = [entry, ...existing].slice(0, MAX_HISTORY_ITEMS);

  if (storage) {
    try {
      storage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // ignore storage errors
    }
  }

  return updated;
};
