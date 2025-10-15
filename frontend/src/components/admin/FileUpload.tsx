/**
 * 文件上传组件
 * 
 * 功能：
 * - 文件选择器
 * - 上传进度条
 * - 仅验证选项
 * 
 * 基于 PRD-10 Admin社区管理Excel导入
 * 最后更新: 2025-10-14
 */

import { useState, useRef } from 'react';

interface FileUploadProps {
  onUpload: (file: File, dryRun: boolean) => Promise<void>;
  isLoading: boolean;
}

export default function FileUpload({ onUpload, isLoading }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 处理文件选择
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // 验证文件类型
      const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
      ];
      
      if (!validTypes.includes(file.type) && !file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        alert('请选择 Excel 文件（.xlsx 或 .xls）');
        return;
      }

      // 验证文件大小（最大 10MB）
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        alert('文件大小不能超过 10MB');
        return;
      }

      setSelectedFile(file);
    }
  };

  // 处理上传
  const handleUpload = async () => {
    if (!selectedFile) {
      alert('请先选择文件');
      return;
    }

    await onUpload(selectedFile, dryRun);
  };

  // 重置文件选择
  const handleReset = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-4">
      {/* 文件选择器 */}
      <div className="flex items-center gap-4">
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFileChange}
          disabled={isLoading}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className={`inline-flex cursor-pointer items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent hover:text-accent-foreground ${
            isLoading ? 'cursor-not-allowed opacity-50' : ''
          }`}
        >
          选择文件
        </label>
        {selectedFile && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-foreground">{selectedFile.name}</span>
            <span className="text-xs text-muted-foreground">
              ({(selectedFile.size / 1024).toFixed(2)} KB)
            </span>
            {!isLoading && (
              <button
                onClick={handleReset}
                className="text-sm text-destructive hover:underline"
              >
                移除
              </button>
            )}
          </div>
        )}
      </div>

      {/* 仅验证选项 */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="dry-run"
          checked={dryRun}
          onChange={(e) => setDryRun(e.target.checked)}
          disabled={isLoading}
          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
        />
        <label
          htmlFor="dry-run"
          className="text-sm text-foreground"
        >
          ☑️ 仅验证（不导入）
        </label>
      </div>

      {/* 上传按钮 */}
      <button
        onClick={handleUpload}
        disabled={!selectedFile || isLoading}
        className={`inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 ${
          (!selectedFile || isLoading) ? 'cursor-not-allowed opacity-50' : ''
        }`}
      >
        {isLoading ? (
          <>
            <svg
              className="mr-2 h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            {dryRun ? '验证中...' : '上传中...'}
          </>
        ) : (
          <>{dryRun ? '验证' : '上传并导入'}</>
        )}
      </button>

      {/* 提示信息 */}
      <div className="rounded-md bg-muted p-4">
        <p className="text-sm text-muted-foreground">
          💡 <strong>提示：</strong>
        </p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-muted-foreground">
          <li>支持 .xlsx 和 .xls 格式</li>
          <li>文件大小不超过 10MB</li>
          <li>勾选"仅验证"可以先检查数据格式，不会导入到数据库</li>
          <li>验证通过后，取消勾选再次上传即可正式导入</li>
        </ul>
      </div>
    </div>
  );
}

