/**
 * 工具网格骨架屏 — 替代"加载中..."文字
 * 模拟 8 个工具卡片的占位布局，带闪烁动画
 */

export default function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {Array.from({ length: 8 }).map((_, index) => (
        <div
          key={index}
          className="bg-slate-800 rounded-xl p-5 border border-slate-700/50"
        >
          {/* 图标占位 */}
          <div className="w-12 h-12 rounded-lg bg-slate-700/50 animate-pulse mb-4" />
          {/* 标题占位 */}
          <div className="h-5 bg-slate-700/50 rounded animate-pulse mb-2 w-3/4" />
          {/* 描述占位 */}
          <div className="h-4 bg-slate-700/50 rounded animate-pulse mb-1 w-full" />
          <div className="h-4 bg-slate-700/50 rounded animate-pulse w-2/3" />
        </div>
      ))}
    </div>
  );
}
