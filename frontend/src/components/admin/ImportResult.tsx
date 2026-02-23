import type { CommunityImportResult } from '@/services/admin.service';

/**
 * 导入结果展示组件
 * 
 * 功能：
 * - 成功/失败统计
 * - 错误详情列表
 * - 导入历史表格
 * 
 * 基于 PRD-10 Admin社区管理Excel导入
 * 最后更新: 2025-10-14
 */

interface ImportResultProps {
  result: CommunityImportResult;
}

export default function ImportResult({ result }: ImportResultProps) {
  const { status, summary, errors, communities } = result;

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h2 className="mb-4 text-xl font-semibold text-foreground">
        📊 导入结果
      </h2>

      {/* 成功状态 */}
      {status === 'success' && summary && (
        <div className="space-y-4">
          <div className="rounded-md bg-green-50 p-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">✅</span>
              <div>
                <p className="font-semibold text-green-800">
                  成功导入 {summary.imported} 个社区
                </p>
                <p className="text-sm text-green-600">
                  总计 {summary.total} 个，有效 {summary.valid} 个
                </p>
              </div>
            </div>
          </div>

          {/* 导入的社区列表 */}
          {communities && communities.length > 0 && (
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-medium text-foreground">
                导入的社区：
              </h3>
              <div className="max-h-60 overflow-y-auto rounded-md border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-foreground">
                        社区名称
                      </th>
                      <th className="px-4 py-2 text-left font-medium text-foreground">
                        层级
                      </th>
                      <th className="px-4 py-2 text-left font-medium text-foreground">
                        状态
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {communities.map((community: any, index: number) => (
                      <tr
                        key={index}
                        className="border-t border-border hover:bg-muted/50"
                      >
                        <td className="px-4 py-2 text-foreground">
                          {community.name}
                        </td>
                        <td className="px-4 py-2 text-foreground">
                          {community.tier}
                        </td>
                        <td className="px-4 py-2 text-green-600">
                          {community.status}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 验证通过状态 */}
      {status === 'validated' && summary && (
        <div className="rounded-md bg-blue-50 p-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl">✔️</span>
            <div>
              <p className="font-semibold text-blue-800">
                验证通过
              </p>
              <p className="text-sm text-blue-600">
                共 {summary.total} 个社区，数据格式正确，可以正式导入
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 错误状态 */}
      {status === 'error' && errors && errors.length > 0 && (
        <div className="space-y-4">
          <div className="rounded-md bg-red-50 p-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">❌</span>
              <div>
                <p className="font-semibold text-red-800">
                  发现 {errors.length} 个错误
                </p>
                <p className="text-sm text-red-600">
                  请修正以下错误后重新上传
                </p>
              </div>
            </div>
          </div>

          {/* 错误详情列表 */}
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-medium text-foreground">
              错误详情：
            </h3>
            <div className="max-h-60 overflow-y-auto rounded-md border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-foreground">
                      行号
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-foreground">
                      字段
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-foreground">
                      值
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-foreground">
                      错误信息
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {errors.map((error: any, index: number) => (
                    <tr
                      key={index}
                      className="border-t border-border hover:bg-muted/50"
                    >
                      <td className="px-4 py-2 text-foreground">
                        第 {error.row} 行
                      </td>
                      <td className="px-4 py-2 font-mono text-foreground">
                        {error.field}
                      </td>
                      <td className="px-4 py-2 font-mono text-muted-foreground">
                        {error.value ?? '—'}
                      </td>
                      <td className="px-4 py-2 text-red-600">
                        {error.error}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 修正建议 */}
          <div className="rounded-md bg-yellow-50 p-4">
            <p className="text-sm font-medium text-yellow-800">
              💡 修正建议：
            </p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-yellow-700">
              <li>检查 Excel 文件中对应行的数据</li>
              <li>确保必填字段（name、tier、categories、description_keywords）已填写</li>
              <li>确保 name 以 "r/" 开头</li>
              <li>确保 tier 是 seed/gold/silver/admin 之一</li>
              <li>修正后重新上传文件</li>
            </ul>
          </div>
        </div>
      )}

      {/* 统计信息（如果有） */}
      {summary && (
        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-5">
          <div className="rounded-md bg-muted p-3">
            <p className="text-xs text-muted-foreground">总计</p>
            <p className="text-2xl font-bold text-foreground">{summary.total}</p>
          </div>
          <div className="rounded-md bg-muted p-3">
            <p className="text-xs text-muted-foreground">有效</p>
            <p className="text-2xl font-bold text-green-600">{summary.valid}</p>
          </div>
          <div className="rounded-md bg-muted p-3">
            <p className="text-xs text-muted-foreground">无效</p>
            <p className="text-2xl font-bold text-red-600">{summary.invalid}</p>
          </div>
          <div className="rounded-md bg-muted p-3">
            <p className="text-xs text-muted-foreground">重复</p>
            <p className="text-2xl font-bold text-yellow-600">{summary.duplicates}</p>
          </div>
          <div className="rounded-md bg-muted p-3">
            <p className="text-xs text-muted-foreground">已导入</p>
            <p className="text-2xl font-bold text-blue-600">{summary.imported}</p>
          </div>
        </div>
      )}
    </div>
  );
}