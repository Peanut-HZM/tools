import { ArrowRight, Eye, Star } from 'lucide-react';
import { ToolCardProps } from '../../types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { resolveIcon } from '../../utils/iconResolver';
import { iconTintClass } from '../../utils/iconTint';

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
      variant="solid"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onClick();
        }
      }}
      className="group relative min-h-[154px] cursor-pointer p-4 transition-[border-color,box-shadow,transform] duration-150 hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md dark:hover:border-indigo-400/30"
    >
      {/* 需登录标签 */}
      {require_login && (
        <Badge variant="warning" className="absolute right-11 top-3 text-[10px]">
          需登录
        </Badge>
      )}
      <ArrowRight className="absolute right-4 top-4 h-3.5 w-3.5 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
      <div className="flex items-start gap-3">
      <div className={`h-10 w-10 shrink-0 rounded-xl ${iconTintClass(iconColor)}`}>
        {custom_icon_url ? (
          <img src={custom_icon_url} alt={title} className="h-5 w-5 object-contain" />
        ) : (
          <Icon className="h-5 w-5" />
        )}
      </div>
      <div className="min-w-0 flex-1 pr-3">
        <h3 className="truncate text-sm font-semibold text-ink">{title}</h3>
        <p className="mt-1 line-clamp-2 min-h-9 text-xs leading-[18px] text-ink-muted">{description}</p>
      </div>
      </div>
      <div className="mt-4 flex items-center gap-1.5 border-t border-border/70 pt-3 text-[11px] text-ink-faint">
        <Eye className="h-3 w-3" />
        <span>{usageCount} 使用</span>
        <span className="mx-1 text-border-strong">·</span>
        <Star className="h-3 w-3" />
        <span>{rating}</span>
      </div>
    </Card>
  );
}