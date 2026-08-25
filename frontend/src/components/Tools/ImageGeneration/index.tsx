/**
 * ImageGeneration — 图像生成主页面
 *
 * 两栏布局：左侧 1/4 对话面板 + 右侧 3/4 图片展示
 */
import ChatPanel from './ChatPanel';
import ImagePanel from './ImagePanel';

export default function ImageGeneration() {
  return (
    <div className="flex h-[calc(100vh-128px)] gap-4">
      <ChatPanel />
      <ImagePanel />
    </div>
  );
}
