import React, { useState, useEffect } from 'react';
import { 
  downloadTemplate, 
  importCommunities, 
  getImportHistory, 
  ImportHistoryItem 
} from '@/api/admin.api';

const CommunityImportPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [history, setHistory] = useState<ImportHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await getImportHistory();
      setHistory(data);
    } catch (err) {
      console.error('Failed to load history', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0] || null);
      setImportResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setImportResult(null);
    try {
      const result = await importCommunities(file, dryRun);
      setImportResult(result);
      if (!dryRun) {
        // Refresh history if it was a real run
        loadHistory();
      }
    } catch (err: any) {
      console.error('Import failed', err);
      alert('导入失败: ' + (err.message || '未知错误'));
    } finally {
      setUploading(false);
    }
  };

  // Status mapping helper
  const getStatusInfo = (status: string) => {
    const map: Record<string, { text: string; colorClass: string }> = {
      'validated': { text: '验证通过', colorClass: 'bg-blue-100 text-blue-800' },
      'success': { text: '导入成功', colorClass: 'bg-green-100 text-green-800' },
      'error': { text: '失败', colorClass: 'bg-red-100 text-red-800' },
      'completed': { text: '完成', colorClass: 'bg-green-100 text-green-800' }, // Legacy fallback
      'failed': { text: '失败', colorClass: 'bg-red-100 text-red-800' }, // Legacy fallback
    };
    return map[status] || { text: status, colorClass: 'bg-gray-100 text-gray-800' };
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">社区批量导入</h1>
          <p className="text-sm text-gray-500 mt-1">上传 Excel 文件批量添加或更新社区池</p>
        </div>
        <button
          onClick={() => downloadTemplate()}
          className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 flex items-center gap-2 text-sm font-medium transition-colors"
        >
          📥 下载模板
        </button>
      </div>

      {/* Upload Section */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold mb-4">上传文件</h2>
        
        <div className="flex flex-col gap-4 max-w-xl">
          <input
            type="file"
            accept=".xlsx, .xls"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100"
          />
          
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="dryRun"
              checked={dryRun}
              onChange={e => setDryRun(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="dryRun" className="text-sm text-gray-700 dark:text-gray-300">
              仅验证 (Dry Run) - 检查数据但不写入数据库
            </label>
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className={`w-full py-2 px-4 rounded font-medium text-white transition-colors ${
              !file || uploading 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {uploading ? '处理中...' : '开始导入'}
          </button>
        </div>

        {/* Result Display */}
        {importResult && (
          <div className={`mt-6 p-4 rounded border ${
            importResult.status === 'success' || importResult.status === 'validated' 
              ? 'bg-green-50 border-green-200' 
              : 'bg-yellow-50 border-yellow-200'
          }`}>
            <h3 className="font-semibold mb-2">
              导入结果 ({dryRun ? '验证模式' : '执行模式'})
            </h3>
            
            {importResult.summary && (
              <div className="grid grid-cols-3 gap-4 text-sm mb-4">
                <div>
                  <span className="text-gray-500">总行数:</span>
                  <span className="font-mono ml-2">{importResult.summary.total}</span>
                </div>
                <div>
                  <span className="text-gray-500">有效:</span>
                  <span className="font-mono ml-2 text-green-600">{importResult.summary.valid}</span>
                </div>
                <div>
                  <span className="text-gray-500">无效:</span>
                  <span className="font-mono ml-2 text-red-600">{importResult.summary.invalid}</span>
                </div>
                <div>
                  <span className="text-gray-500">重复:</span>
                  <span className="font-mono ml-2 text-yellow-600">{importResult.summary.duplicates}</span>
                </div>
                <div>
                  <span className="text-gray-500">成功导入:</span>
                  <span className="font-mono ml-2 text-blue-600">{importResult.summary.imported}</span>
                </div>
              </div>
            )}

            {importResult.errors && importResult.errors.length > 0 && (
              <div className="mt-4">
                <h4 className="font-medium text-sm mb-2 text-red-800">错误详情:</h4>
                <div className="bg-white p-3 rounded border border-gray-200 max-h-48 overflow-y-auto text-xs font-mono">
                  {importResult.errors.map((err: any, idx: number) => (
                    <div key={idx} className="text-red-600 mb-1">
                      Row {err.row}: {err.field ? `[${err.field}] ` : ''}{err.error} {err.value ? `(Value: ${err.value})` : ''}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {importResult.status === 'validated' && dryRun && (
              <p className="mt-4 text-sm text-green-700">
                ✅ 数据验证通过。取消勾选"仅验证"并再次点击"开始导入"以写入数据库。
              </p>
            )}
          </div>
        )}
      </div>

      {/* History Section */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">导入历史</h2>
          <button 
            onClick={loadHistory}
            className="text-sm text-blue-600 hover:underline"
          >
            刷新
          </button>
        </div>

        {loadingHistory ? (
          <div className="text-center py-8 text-gray-500">加载中...</div>
        ) : history.length === 0 ? (
          <div className="text-center py-8 text-gray-500">暂无导入记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时间</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">文件名</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作人</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">模式</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">结果 (总/导入/无效)</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {history.map((item) => {
                  const statusInfo = getStatusInfo(item.status);
                  return (
                    <tr key={item.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(item.uploaded_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {item.filename}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {item.uploaded_by}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {item.dry_run ? '验证' : '执行'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {item.summary ? (
                          <>
                            {item.summary.total} / <span className="text-green-600">{item.summary.imported}</span> / <span className="text-red-600">{item.summary.invalid}</span>
                          </>
                        ) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusInfo.colorClass}`}>
                          {statusInfo.text}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default CommunityImportPage;
