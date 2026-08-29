/**
 * ImageGen 工具渲染器
 *
 * 显示图像生成结果：
 * - 顶部：工具名 badge + 操作类型 badge（文生图/图生图/局部重绘/指令编辑）+ 模型标签
 * - 润色后 prompt：可折叠展开
 * - 图片网格（1-4 张）：缩略图 + 点击放大（新标签页打开）
 * - 执行中状态：「正在生成图像...」
 * - 失败状态：显示 error message
 *
 * 安全：所有图片 URL 经 safeHref 校验（仅 http/https），
 * 避免 javascript: / data: / file: 等危险 scheme 触发 XSS。
 */
import React, { useState } from 'react';
import type { ToolRendererProps } from '@/stores/useToolRegistry';
import { safeHref } from './WebSearchRenderer';

/** operation -> 中文标签 */
const OPERATION_LABELS: Record<string, string> = {
  text2img: '文生图',
  img2img: '图生图',
  inpaint: '局部重绘',
  upload_edit: '指令编辑',
};

/** result.content 解析后的结构（兼容 string / object 两种形态） */
interface ImageGenContent {
  operation?: string;
  model_used?: string;
  revised_prompt?: string;
  image_count?: number;
}

export const ImageGenRenderer: React.FC<ToolRendererProps> = ({ call, result, pending }) => {
  const operation = (call.arguments?.operation as string | undefined) ?? '';
  const [showPrompt, setShowPrompt] = useState(false);

  // 解析 result.content（兼容 string / object）
  const content = React.useMemo<ImageGenContent>(() => {
    if (!result) return {};
    const c = result.content;
    if (typeof c === 'string') {
      try {
        return JSON.parse(c) as ImageGenContent;
      } catch {
        return {};
      }
    }
    if (c && typeof c === 'object') {
      return c as ImageGenContent;
    }
    return {};
  }, [result]);

  // 提取 type === 'image' 的附件 URL
  const imageUrls = React.useMemo<string[]>(() => {
    if (!result?.attachments) return [];
    return result.attachments
      .filter((a) => a.type === 'image')
      .map((a) => a.url);
  }, [result]);

  // 图片数量影响 grid 布局：1 张单列，>=2 张两列
  const gridCols = imageUrls.length <= 1 ? 'grid-cols-1' : 'grid-cols-2';

  return (
    <div className="rounded-lg border border-surface-2 bg-surface-1 dark:bg-canvas p-3 text-sm">
      {/* 顶部：工具名 + 操作类型 + 模型 */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-info/10 text-accent-info">
          image_gen
        </span>
        {operation && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-2 text-ink-faint dark:text-ink-muted">
            {OPERATION_LABELS[operation] ?? operation}
          </span>
        )}
        {content.model_used && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-surface-2 text-ink-faint dark:text-ink-muted">
            {content.model_used}
          </span>
        )}
      </div>

      {/* 执行中：仅当 pending 且尚无 result 时显示（已有 result 时由 StatusLine 接管） */}
      {pending && !result && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-3">
          正在生成图像...
        </div>
      )}

      {/* 失败 */}
      {result && !result.success && (
        <div className="text-danger text-xs py-2">
          生成失败：{result.error ?? '未知错误'}
        </div>
      )}

      {/* 润色后 prompt（可折叠） */}
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

      {/* 图片网格 */}
      {result?.success && imageUrls.length > 0 && (
        <div className={`grid gap-2 mt-2 ${gridCols}`}>
          {imageUrls.map((url, idx) => {
            // URL 必须经过 safeHref 校验，避免 javascript: 等危险 scheme
            const safe = safeHref(url);
            return (
              <div
                key={idx}
                className="rounded overflow-hidden border border-surface-2 bg-surface-1"
              >
                {safe ? (
                  <a
                    href={safe}
                    target="_blank"
                    rel="noopener noreferrer nofollow"
                    className="block"
                  >
                    <img
                      src={safe}
                      alt={`生成图片 ${idx + 1}`}
                      className="w-full h-auto object-cover cursor-pointer hover:opacity-90 transition-opacity"
                      loading="lazy"
                    />
                  </a>
                ) : (
                  <div className="px-2 py-3 text-xs text-ink-faint break-all">
                    [图片 URL 不安全，无法显示：{url}]
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 成功但无图片 */}
      {result?.success && imageUrls.length === 0 && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          未生成图片
        </div>
      )}
    </div>
  );
};

export default ImageGenRenderer;
