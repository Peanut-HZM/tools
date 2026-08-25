import { ToolCardProps } from '../../types';

export default function ToolCard({
  icon,
  iconColor,
  title,
  description,
  rating,
  usageCount,
  custom_icon_url,
  require_login,
  onClick
}: ToolCardProps) {
  return (
    <div
      onClick={onClick}
      className="tool-card bg-surface-2 rounded-xl p-6 border border-border hover:border-accent transition-all cursor-pointer relative"
    >
      {/* 需登录标签 */}
      {require_login && (
        <span className="absolute top-3 right-3 bg-accent-warning/20 text-accent-warning text-[10px] px-1.5 py-0.5 rounded border border-accent-warning/30">
          需登录
        </span>
      )}
      <div className={`w-12 h-12 ${iconColor} rounded-lg flex items-center justify-center mb-4`}>
        {custom_icon_url ? (
          <img src={custom_icon_url} alt={title} className="w-6 h-6 object-contain" />
        ) : (
          <i className={`fas ${icon} text-ink-inverse text-xl`}></i>
        )}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-ink-muted text-sm mb-4">{description}</p>
      <div className="flex items-center text-xs text-ink-faint">
        <i className="fas fa-star mr-1"></i>
        <span>{rating}</span>
        <span className="mx-2">•</span>
        <span>{usageCount} 使用</span>
      </div>
    </div>
  );
}
