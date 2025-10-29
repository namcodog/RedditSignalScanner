/**
 * EvidencePanel Component
 * 
 * 证据面板组件：展示证据列表，支持分页（每页 10 条）
 * 
 * 最后更新: 2025-10-22
 */

import { useState } from 'react';
import { ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';
import type { Evidence } from '@/types';

interface EvidencePanelProps {
  /** 证据列表 */
  evidences: Evidence[];
  
  /** 每页显示数量 */
  pageSize?: number;
}

/**
 * 证据面板组件
 */
export default function EvidencePanel({ evidences, pageSize = 10 }: EvidencePanelProps) {
  const [currentPage, setCurrentPage] = useState(1);

  // 计算分页
  const totalPages = Math.ceil(evidences.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentEvidences = evidences.slice(startIndex, endIndex);

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1));
  };

  const handlePageClick = (page: number) => {
    setCurrentPage(page);
  };

  // 如果没有证据，显示空状态
  if (evidences.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">暂无证据数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 证据列表 */}
      <div className="space-y-3">
        {currentEvidences.map((evidence, index) => (
          <div
            key={evidence.id}
            className="rounded-lg border border-border bg-card p-4 transition-shadow hover:shadow-md"
          >
            {/* 顶部：序号 + 子版块 + 时间 */}
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-secondary/20 text-xs font-semibold text-secondary">
                  {startIndex + index + 1}
                </span>
                <span className="text-sm font-medium text-foreground">
                  {evidence.subreddit}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {new Date(evidence.timestamp).toLocaleDateString('zh-CN', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>

            {/* 证据摘录 */}
            <p className="mb-3 text-sm italic text-muted-foreground">
              "{evidence.excerpt}"
            </p>

            {/* 底部：链接 + 相关性分数 */}
            <div className="flex items-center justify-between">
              <a
                href={evidence.post_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                <span>查看原帖</span>
              </a>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">相关性:</span>
                <div className="flex items-center gap-1">
                  <div className="h-2 w-16 rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-secondary transition-all"
                      style={{
                        width: `${Math.min(
                          100,
                          Math.max(0, (evidence.score ?? 0) * 100)
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs font-medium text-foreground">
                    {evidence.score != null
                      ? `${(evidence.score * 100).toFixed(0)}%`
                      : '待定'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 分页控件 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3">
          {/* 左侧：显示范围 */}
          <div className="text-sm text-muted-foreground">
            显示 {startIndex + 1}-{Math.min(endIndex, evidences.length)} / 共{' '}
            {evidences.length} 条
          </div>

          {/* 右侧：分页按钮 */}
          <div className="flex items-center gap-2">
            {/* 上一页 */}
            <button
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-background text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            {/* 页码按钮 */}
            <div className="flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                // 只显示当前页附近的页码
                if (
                  page === 1 ||
                  page === totalPages ||
                  (page >= currentPage - 1 && page <= currentPage + 1)
                ) {
                  return (
                    <button
                      key={page}
                      onClick={() => handlePageClick(page)}
                      className={`inline-flex h-8 min-w-[2rem] items-center justify-center rounded-md border px-2 text-sm font-medium transition-colors ${
                        page === currentPage
                          ? 'border-secondary bg-secondary text-secondary-foreground'
                          : 'border-border bg-background text-foreground hover:bg-muted'
                      }`}
                    >
                      {page}
                    </button>
                  );
                } else if (
                  page === currentPage - 2 ||
                  page === currentPage + 2
                ) {
                  return (
                    <span key={page} className="px-1 text-muted-foreground">
                      ...
                    </span>
                  );
                }
                return null;
              })}
            </div>

            {/* 下一页 */}
            <button
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-background text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
