/**
 * HistoryDrawer — 右侧抽屉 + 分页历史列表
 */
import { useCallback, useEffect } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenHistory } from '../../../../hooks/useImageGenHistory';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import { getResultUrl } from '../../../../api/imageGenerationApi';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import type { HistoryItem } from '../../../../api/imageGenerationApi';

function HistoryCard({ item }: { item: HistoryItem }) {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const currentResult = useImageGenStore((s) => s.currentResult);
  const setCurrentResult = useImageGenStore((s) => s.setCurrentResult);
  const deleteHistory = useImageGenStore((s) => s.deleteHistory);
  const setHistoryDrawerOpen = useImageGenStore((s) => s.setHistoryDrawerOpen);

  const operationLabels: Record<string, string> = {
    text2img: igT.tabs.text2img,
    img2img: igT.tabs.img2img,
    inpaint: igT.tabs.inpaint,
    upload_edit: igT.tabs.uploadEdit,
  };

  const handleView = useCallback(async () => {
    // 构建一个 GenerateResponse 来复用 ResultPanel 逻辑
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
      setHistoryDrawerOpen(false);
    } catch {
      // 忽略
    }
  }, [item, setCurrentResult, setHistoryDrawerOpen]);

  const handleDelete = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    deleteHistory(item.id);
  }, [item.id, deleteHistory]);

  const isSelected = currentResult?.history_id === item.id;
  const statusIcon = item.status === 'success' ? '✓' : item.status === 'failed' ? '✗' : '⊘';
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
            <span className="px-1.5 py-0.5 text-[10px] bg-surface-2 text-ink-muted rounded">
              {operationLabels[item.operation] || item.operation}
            </span>
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
          title={igT.history.delete}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export default function HistoryDrawer() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const historyDrawerOpen = useImageGenStore((s) => s.historyDrawerOpen);
  const setHistoryDrawerOpen = useImageGenStore((s) => s.setHistoryDrawerOpen);
  const { history, historyTotal, historyLoading, page, totalPages, goNext, goPrev, refresh } = useImageGenHistory();

  // 打开抽屉时加载
  useEffect(() => {
    if (historyDrawerOpen) refresh();
  }, [historyDrawerOpen, refresh]);

  if (!historyDrawerOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={() => setHistoryDrawerOpen(false)}
      />

      {/* 抽屉 */}
      <div className="fixed right-0 top-0 h-full w-80 bg-canvas border-l border-border z-50 flex flex-col shadow-lg">
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h3 className="text-lg font-medium text-ink">{igT.history.title}</h3>
          <button
            onClick={() => setHistoryDrawerOpen(false)}
            className="p-1 text-ink-muted hover:text-ink transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 列表 */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
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
              className="px-3 py-1 text-sm"
            >
              {igT.history.prevPage}
            </Button>
            <span className="text-xs text-ink-faint">
              {page + 1} / {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={goNext}
              disabled={(page + 1) >= totalPages}
              className="px-3 py-1 text-sm"
            >
              {igT.history.nextPage}
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
