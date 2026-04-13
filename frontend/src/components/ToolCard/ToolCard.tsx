import { ToolCardProps } from '../../types';

export default function ToolCard({
  icon,
  iconColor,
  title,
  description,
  rating,
  usageCount,
  custom_icon_url,
  onClick
}: ToolCardProps) {
  return (
    <div
      onClick={onClick}
      className="tool-card bg-slate-800 rounded-xl p-6 border border-slate-700 hover:border-primary transition-all cursor-pointer"
    >
      <div className={`w-12 h-12 ${iconColor} rounded-lg flex items-center justify-center mb-4`}>
        {custom_icon_url ? (
          <img src={custom_icon_url} alt={title} className="w-6 h-6 object-contain" />
        ) : (
          <i className={`fas ${icon} text-white text-xl`}></i>
        )}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-slate-400 text-sm mb-4">{description}</p>
      <div className="flex items-center text-xs text-slate-500">
        <i className="fas fa-star mr-1"></i>
        <span>{rating}</span>
        <span className="mx-2">•</span>
        <span>{usageCount} 使用</span>
      </div>
    </div>
  );
}
