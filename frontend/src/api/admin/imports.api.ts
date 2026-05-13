import { apiClient } from '../client';

export const downloadTemplateBlob = async (): Promise<Blob> => {
  const response = await apiClient.get('/admin/communities/template', {
    responseType: 'blob',
  });
  return response.data as Blob;
};

export const downloadTemplate = async (): Promise<void> => {
  const blob = await downloadTemplateBlob();
  const url = window.URL.createObjectURL(new Blob([blob]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'community_template.xlsx');
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export interface CommunityImportSummary {
  total: number;
  valid: number;
  invalid: number;
  duplicates: number;
  imported: number;
}

export interface CommunityImportResult {
  status: string;
  summary: CommunityImportSummary;
  errors?: unknown[];
  communities?: unknown[];
}

export interface ImportCommunitiesOptions {
  dryRun?: boolean | undefined;
  onUploadProgress?: ((percent: number) => void) | undefined;
}

export const importCommunities = async (
  file: File,
  options: ImportCommunitiesOptions | boolean = {},
): Promise<CommunityImportResult> => {
  const normalizedOptions = typeof options === 'boolean' ? { dryRun: options } : options;
  const formData = new FormData();
  formData.append('file', file);

  const config: Record<string, unknown> = {
    params: { dry_run: normalizedOptions.dryRun ?? false },
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  };
  if (normalizedOptions.onUploadProgress) {
    config['onUploadProgress'] = (event: { lengthComputable?: boolean; total?: number; loaded: number }) => {
      if (!event.lengthComputable || !event.total) return;
      normalizedOptions.onUploadProgress?.(Math.round((event.loaded / event.total) * 100));
    };
  }

  const response = await apiClient.post('/admin/communities/import', formData, config);
  return response.data as CommunityImportResult;
};

export interface ImportHistoryItem {
  id: number;
  filename: string;
  status: string;
  uploaded_by: string;
  uploaded_at: string;
  dry_run: boolean;
  summary: CommunityImportSummary;
  error_log?: string;
}

export const getImportHistory = async (limit: number = 50): Promise<ImportHistoryItem[]> => {
  const response = await apiClient.get<{ imports: ImportHistoryItem[] }>('/admin/communities/import-history', {
    params: { limit },
  });
  return response.data.imports || [];
};
