/**
 * VideoGen 工具渲染器
 *
 * 显示视频生成结果：
 * - 顶部：工具名 badge + 模型标签
 * - 润色后 prompt：可折叠展开
 * - 视频播放器（内嵌 <video>）
 * - 执行中/失败状态
 *
 * 安全：URL 经 safeHref 校验。
 */
import React, { useState } from 'react';
import type { ToolRendererProps } from '@/stores/useToolRegistry';
import { safeHref } from './WebSearchRenderer';

interface VideoGenContent {
  model_used?: string;
  revised_prompt?: string;
  task_id?: string;
}

export const VideoGenRenderer: React.FC<ToolRendererProps> = ({ call, result, pending }) => {
  const [showPrompt, setShowPrompt] = useState(false);

  const content = React.useMemo<VideoGenContent>(() => {
    if (!result) return {};
    const c = result.content;
    if (typeof c === 'string') {
      try { return JSON.parse(c) as VideoGenContent; } catch { return {}; }
    }
    if (c && typeof c === 'object') return c as VideoGenContent;
    return {};
  }, [result]);

  const videoUrl = React.useMemo<string>(() => {
    if (!result?.attachments) return '';
    const found = result.attachments.find(
      (a) => (a.type === 'file' || a.url?.includes('video-gen/')) && a.url,
    );
    return found?.url || '';
  }, [result]);

  return (
    <div className="rounded-lg border border-surface-2 bg-surface-1 dark:bg-canvas p-3 text-sm">
      {/* 顶部 */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-info/10 text-accent-info">
          video_gen
        </span>
        {content.model_used && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-surface-2 text-ink-faint dark:text-ink-muted">
            {content.model_used}
          </span>
        )}
        {content.task_id && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-surface-2 text-ink-faint dark:text-ink-muted">
            任务: {content.task_id}
          </span>
        )}
      </div>

      {/* 执行中 */}
      {pending && !result && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-3">
          正在生成视频，请耐心等待…
        </div>
      )}

      {/* 失败 */}
      {result && !result.success && (
        <div className="text-danger text-xs py-2">
          生成失败：{result.error ?? '未知错误'}
        </div>
      )}

      {/* 润色 prompt */}
      {result?.success && content.revised_prompt && (
        <div className="mb-2">
          <button
            type="button"
            onClick={() => setShowPrompt((v) => !v)}
            className="text-xs text-accent-info hover:underline"
          >
            {showPrompt ? '收起润色 prompt' : '查看润色 prompt'}
          </button>
          {showPrompt && (
            <div className="mt-1 px-2 py-1 rounded bg-surface-2 text-xs text-ink-faint dark:text-ink-muted italic whitespace-pre-wrap break-words">
              {content.revised_prompt}
            </div>
          )}
        </div>
      )}

      {/* 视频播放器 */}
      {result?.success && videoUrl && (
        <div className="mt-2 rounded overflow-hidden border border-surface-2 bg-black">
          {safeHref(videoUrl) ? (
            <video
              src={safeHref(videoUrl)!}
              controls
              className="w-full max-h-[480px]"
              preload="metadata"
            />
          ) : (
            <div className="px-2 py-3 text-xs text-ink-faint break-all">
              [视频 URL 不安全，无法显示]
            </div>
          )}
        </div>
      )}

      {/* 成功但无视频 */}
      {result?.success && !videoUrl && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          未生成视频
        </div>
      )}
    </div>
  );
};

export default VideoGenRenderer;
