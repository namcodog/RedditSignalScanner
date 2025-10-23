/**
 * Admin 社区管理 - Excel 批量导入页面
 * 
 * 基于 PRD-10 Admin社区管理Excel导入
 * 最后更新: 2025-10-14
 */

import { useState, useEffect } from 'react';
import {
  adminService,
  CommunityImportHistoryEntry,
  CommunityImportResult,
} from '@/services/admin.service';
import FileUpload from '@/components/admin/FileUpload';
import ImportResult from '@/components/admin/ImportResult';

export default function CommunityImport() {
  const [importResult, setImportResult] = useState<CommunityImportResult | null>(null);
  const [importHistory, setImportHistory] = useState<CommunityImportHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState<number>(0);

  // 下载模板
  const handleDownloadTemplate = async () => {
    try {
      const blob = await adminService.downloadCommunityTemplate();
      const finalBlob = blob.type
        ? blob
        : new Blob([blob], {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          });
      const url = window.URL.createObjectURL(finalBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'community_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('下载模板失败:', error);
      alert('下载模板失败，请稍后重试');
    }
  };

  // 上传并导入
  const handleUpload = async (file: File, dryRun: boolean) => {
    setIsLoading(true);
    setImportResult(null);
    setProgress(0);

    try {
      const result = await adminService.uploadCommunityImport(file, {
        dryRun,
        onProgress: (pct) => setProgress(pct),
      });
      setImportResult(result);
      setProgress(100);

      // 如果导入成功，刷新历史记录
      if (result.status === 'success') {
        await fetchImportHistory();
      }
    } catch (error: any) {
      console.error('上传失败:', error);
      setProgress(0);
      setImportResult({
        status: 'error',
        summary: {
          total: 0,
          valid: 0,
          invalid: 0,
          duplicates: 0,
          imported: 0,
        },
        errors: [
          {
            row: 0,
            field: 'file',
            value: file.name,
            error: error?.message || '上传失败，请检查网络连接或文件格式',
          },
        ],
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 获取导入历史
  const fetchImportHistory = async () => {
    try {
      const history = await adminService.getCommunityImportHistory();
      setImportHistory(history);
    } catch (error) {
      console.error('获取历史记录失败:', error);
    }
  };

  // 组件挂载时获取历史记录
  useEffect(() => {
    fetchImportHistory();
  }, []);

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">社区管理 - 批量导入</h1>
        <p className="mt-2 text-muted-foreground">
          通过 Excel 文件批量导入社区数据
        </p>
      </div>

      {/* 步骤 1：下载模板 */}
      <div className="mb-8 rounded-lg border border-border bg-card p-6">
        <h2 className="mb-4 text-xl font-semibold text-foreground">
          📥 步骤 1：下载模板
        </h2>
        <button
          onClick={handleDownloadTemplate}
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          下载 Excel 模板
        </button>
        <p className="mt-4 text-sm text-muted-foreground">
          💡 提示：请按照模板格式填写社区信息，必填字段包括：name、tier、categories、description_keywords
        </p>
      </div>

      {/* 步骤 2：上传文件 */}
      <div className="mb-8 rounded-lg border border-border bg-card p-6">
        <h2 className="mb-4 text-xl font-semibold text-foreground">
          📤 步骤 2：上传 Excel 文件
        </h2>
        <FileUpload
          onUpload={handleUpload}
          isLoading={isLoading}
        />
        {/* 上传进度条（P1：上传进度显示） */}
        {isLoading && (
          <div className="mt-4">
            <div className="h-2 w-full rounded bg-muted">
              <div
                className="h-2 rounded bg-primary transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-1 text-right text-xs text-muted-foreground">{progress}%</p>
          </div>
        )}
      </div>

      {/* 导入结果 */}
      {importResult && (
        <div className="mb-8">
          <ImportResult result={importResult} />
        </div>
      )}

      {/* 导入历史 */}
      <div className="rounded-lg border border-border bg-card p-6">
        <h2 className="mb-4 text-xl font-semibold text-foreground">
          📋 导入历史
        </h2>
        {importHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无导入记录</p>
        ) : (
          <div className="space-y-2">
            {importHistory.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-md border border-border bg-muted/50 p-3"
              >
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted-foreground">
                    {new Date(item.uploaded_at).toLocaleString('zh-CN')}
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {item.filename}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    总计 {item.summary.total} 个，导入 {item.summary.imported} 个
                  </span>
                </div>
                <span
                  className={`text-sm font-medium ${
                    item.status === 'success'
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {item.status === 'success' ? '✅ 成功' : '❌ 失败'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
