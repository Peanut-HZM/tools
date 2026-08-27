import { Star } from 'lucide-react';
import { ToolCardProps } from '../../types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { resolveIcon } from '../../utils/iconResolver';

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
  // 后端 `tool.icon` 字段仍是 FA class 字符串（如 'fa-image'），通过共享工具
  // 解析成 lucide 组件，避免运行时依赖 Font Awesome CDN。
  // 后续后端存储迁完后此组件可直接接收 LucideIcon 类型。
  const Icon = resolveIcon(icon);
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
          <Icon className="w-6 h-6 text-white" />
        )}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-ink-muted text-sm mb-4">{description}</p>
      <div className="flex items-center text-xs text-ink-faint">
        <Star className="w-3 h-3 mr-1" />
        <span>{rating}</span>
        <span className="mx-2">•</span>
        <span>{usageCount} 使用</span>
      </div>
    </Card>
  );
}