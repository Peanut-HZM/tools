import { useState } from 'react';

/**
 * 图片预览组件接口
 */
interface ImagePreviewProps {
  /** Base64 编码的图片数据（不含 data: 前缀） */
  base64Data: string;
  /** 图片 MIME 类型，如 image/png、image/jpeg */
  contentType: string;
}

/**
 * 图片预览组件
 *
 * 将 Base64 图片数据组装为 data URL 并在容器内居中显示，
 * 加载失败时展示降级提示，避免界面出现空白或破碎图标。
 */
export default function ImagePreview({ base64Data, contentType }: ImagePreviewProps) {
  // 加载失败标记：触发降级提示，避免显示破损图标
  const [error, setError] = useState(false);

  // 组装 data URL 供 <img> 直接渲染
  const dataUrl = `data:${contentType};base64,${base64Data}`;

  if (error) {
    return (
      <div className="text-center py-8 text-ink-faint">
        <i className="fas fa-image text-4xl mb-3 opacity-30"></i>
        <p>图片加载失败</p>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-4 bg-canvas rounded-lg">
      <img
        src={dataUrl}
        alt="Response"
        className="max-w-full max-h-[500px] object-contain"
        onError={() => setError(true)}
      />
    </div>
  );
}