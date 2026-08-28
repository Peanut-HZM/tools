/**
 * K8s 控制台 - 分页器组件
 *
 * 简洁分页器：上一页/下一页 + 页码显示 + 每页条数切换
 */
import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';

export interface PaginationProps {
  total: number;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

const PAGE_SIZE_OPTIONS = [10, 20, 50];

export const Pagination: React.FC<PaginationProps> = ({
  total,
  currentPage,
  pageSize,
  onPageChange,
  onPageSizeChange,
}) => {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const end = Math.min(currentPage * pageSize, total);

  return (
    <div className="flex items-center justify-between px-3 py-2 border-t border-border bg-surface-1/30 text-xs text-ink-muted shrink-0">
      {/* 左侧：总数 + 每页条数 */}
      <div className="flex items-center gap-3">
        <span>共 {total} 条</span>
        <Select
          value={String(pageSize)}
          onValueChange={(val) => {
            onPageSizeChange(Number(val));
            onPageChange(1);
          }}
        >
          <SelectTrigger className="h-6 w-auto px-2 py-0 text-xs border-border bg-surface-2">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((size) => (
              <SelectItem key={size} value={String(size)}>
                {size}条/页
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 中间：页码 */}
      <span>
        第 {currentPage} 页 / 共 {totalPages} 页
        {total > 0 && <span className="ml-1">（{start}-{end}）</span>}
      </span>

      {/* 右侧：翻页按钮 */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="flex items-center gap-1 px-2 py-1 rounded border border-border hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-3 h-3" />
          上一页
        </button>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="flex items-center gap-1 px-2 py-1 rounded border border-border hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          下一页
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};
