/**
 * ResultPanel — 生成结果展示：大图 + 下载 + "以此图为参考" + 删除
 */
import { useState, useEffect, useCallback } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { getResultUrl } from '../../../../api/imageGenerationApi';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

export default function ResultPanel() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const currentResult = useImageGenStore((s) => s.currentResult);
  const useImageAsReference = useImageGenStore((s) => s.useImageAsReference);
  const loading = useImageGenStore((s) => s.loading);

  const [resultUrls, setResultUrls] = useState<string[]>([]);
  const [loadingUrls, setLoadingUrls] = useState(false);

  // 加载结果图签名 URL（generate 返回的 image_urls 可能是 OSS key，需要刷新签名）
  useEffect(() => {
    if (!currentResult?.history_id) {
      setResultUrls([]);
      return;
    }

    // 如果 image_urls 已经是完整 URL（http 开头），直接使用
    if (currentResult.image_urls.length > 0 && currentResult.image_urls[0].startsWith('http')) {
      setResultUrls(currentResult.image_urls);
      return;
    }

    // 否则通过 result 端点获取签名 URL
    setLoadingUrls(true);
    getResultUrl(currentResult.history_id)
      .then((resp) => {
        setResultUrls(resp.result_url ? [resp.result_url] : []);
      })
      .catch(() => {
        // 降级使用原始 URLs
        setResultUrls(currentResult.image_urls);
      })
      .finally(() => setLoadingUrls(false));
  }, [currentResult]);

  const handleDownload = useCallback(async (url: string, index: number) => {
    try {
      const resp = await fetch(url);
      const blob = await resp.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `image-gen-${currentResult?.history_id?.slice(0, 8) || 'result'}-${index + 1}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);
    } catch {
      // 降级：直接打开
      window.open(url, '_blank');
    }
  }, [currentResult]);

  const handleUseAsRef = useCallback((url: string) => {
    useImageAsReference(url);
  }, [useImageAsReference]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[300px] gap-4">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-ink-muted text-sm">{igT.result.generating}</p>
      </div>
    );
  }

  if (!currentResult) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[300px] text-ink-faint">
        <svg className="w-16 h-16 mb-4 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <p className="text-sm">{igT.result.noResult}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 结果信息 */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-3">
          <Badge variant="secondary">
            {currentResult.model_used}
          </Badge>
          <span className="text-ink-faint">
            {currentResult.duration_ms ? `${(currentResult.duration_ms / 1000).toFixed(1)}s` : ''}
          </span>
        </div>
      </div>

      {/* 图片网格 */}
      {loadingUrls ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className={`grid gap-3 ${resultUrls.length === 1 ? 'grid-cols-1' : 'grid-cols-2'}`}>
          {resultUrls.map((url, i) => (
            <Card key={i} className="group relative overflow-hidden">
              <img
                src={url}
                alt={igT.result.imageAlt.replace('{index}', String(i + 1))}
                className="w-full object-contain max-h-96"
              />
              {/* 悬浮操作栏 */}
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleDownload(url, i)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    {igT.result.download}
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleUseAsRef(url)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    {igT.result.useAsReference}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* 提示词 */}
      <div className="text-xs text-ink-faint line-clamp-2">
        <span className="text-ink-muted">{igT.result.promptLabel}</span>{currentResult.prompt}
      </div>
    </div>
  );
}
