/**
 * ImagePanel — 右侧图片展示面板（3/4 宽度）
 * 包含：生成结果展示 + 内嵌历史列表
 */
import { useCallback } from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/Tooltip';
import { useImageGenStore } from '../../../stores/imageGenerationStore';
import { useImageGenHistory } from '../../../hooks/useImageGenHistory';
import { useImageGenerate } from '../../../hooks/useImageGenerate';
import { getResultUrl } from '../../../api/imageGenerationApi';
import { useI18n } from '../../../i18n';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import ResultPanel from './components/ResultPanel';
import type { HistoryItem } from '../../../api/imageGenerationApi';

function HistoryCard({ item }: { item: HistoryItem }) {
  const igT = useI18n().t.imageGeneration;
  const currentResult = useImageGenStore((s) => s.currentResult);
  const setCurrentResult = useImageGenStore((s) => s.setCurrentResult);
  const deleteHistory = useImageGenStore((s) => s.deleteHistory);

  const operationLabels: Record<string, string> = {
    text2img: '文生图',
    img2img: '图生图',
    inpaint: '局部重绘',
    upload_edit: '上传编辑',
  };

  const handleView = useCallback(async () => {
    try {
      const resp = await getResultUrl(item.id);
      setCurrentResult({
        history_id: item.id,
        image_urls: resp.result_url ? [resp.result_url] : [],
        model_used: item.model_used || '',
        duration_ms: item.duration_ms || 0,
        operation: item.operation,
        prompt: item.prompt,
      });
    } catch {
      // 忽略
    }
  }, [item, setCurrentResult]);

  const handleDelete = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    deleteHistory(item.id);
  }, [item.id, deleteHistory]);

  const isSelected = currentResult?.history_id === item.id;
  const statusIcon = item.status === 'success' ? '✓' : item.status === 'failed' ? '✗' : '';
  const statusColor = item.status === 'success' ? 'text-success' : item.status === 'failed' ? 'text-danger' : 'text-ink-faint';

  return (
    <div
      onClick={handleView}
      className={`
        p-3 rounded-lg border cursor-pointer transition-all
        ${isSelected
          ? 'border-blue-500 bg-accent-info/10'
          : 'border-border bg-surface-1/50 hover:border-border hover:bg-surface-1'
        }
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="secondary">
              {operationLabels[item.operation] || item.operation}
            </Badge>
            <span className={`text-xs ${statusColor}`}>{statusIcon}</span>
          </div>
          <p className="text-xs text-ink-muted truncate">{item.prompt}</p>
          {item.created_at && (
            <p className="text-[10px] text-ink-faint mt-1">
              {new Date(item.created_at).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={handleDelete}
          className="p-1 text-ink-faint hover:text-danger transition-colors"
          aria-label="删除"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export default function ImagePanel() {
  const igT = useI18n().t.imageGeneration;
  const { history, historyTotal, historyLoading, page, totalPages, goNext, goPrev, refresh } = useImageGenHistory();

  return (
    <div className="w-3/4 flex flex-col min-h-0 bg-canvas">
      {/* 生成结果 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        <ResultPanel />
      </div>

      {/* 历史列表 */}
      <div className="border-t border-border bg-surface-1/30 flex-shrink-0">
        <div className="px-4 py-2 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-medium text-ink-muted">{igT.history.title}</h3>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={refresh}
                  className="text-xs text-ink-muted hover:text-ink transition-colors"
                  aria-label="刷新"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
              </TooltipTrigger>
              <TooltipContent>刷新</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        <div className="h-48 overflow-y-auto p-3 space-y-2">
          {historyLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-ink-faint text-sm">
              {igT.history.empty}
            </div>
          ) : (
            history.map((item) => <HistoryCard key={item.id} item={item} />)
          )}
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3 border-t border-border">
            <Button
              variant="secondary"
              size="sm"
              onClick={goPrev}
              disabled={page === 0}
              className="px-3 py-1 text-xs"
            >
              上一页
            </Button>
            <span className="text-xs text-ink-faint">
              {page + 1} / {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={goNext}
              disabled={(page + 1) >= totalPages}
              className="px-3 py-1 text-xs"
            >
              下一页
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
