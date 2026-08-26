import { ToolCardProps } from '../../types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

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
    <Card
      onClick={onClick}
      className="p-6 hover:border-accent transition-all cursor-pointer relative"
    >
      {/* 需登录标签 */}
      {require_login && (
        <Badge variant="warning" className="absolute top-3 right-3 text-[10px]">
          需登录
        </Badge>
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
    </Card>
  );
}
