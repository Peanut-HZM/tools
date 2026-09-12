import { Recommendation } from '../../types';
import { LucideIcon } from 'lucide-react';
import { useI18n, interpolate } from '../../i18n';
import { iconTintClass } from '../../utils/iconTint';

export default function RecommendationCard({ icon: Icon, iconColor, title, description, action }: Recommendation) {
  const { t } = useI18n();

  const handleClick = () => {
    alert(interpolate(t.errors.toolNotImplemented, { toolId: title }));
  };

  return (
    <div className="bg-surface-1 rounded-xl p-6 border border-border">
      <div className="flex items-center mb-4">
        {/* iconColor 改经 tint 色板映射（饱和色块已废弃），图标颜色由 tint 类提供 */}
        <div className={`w-10 h-10 rounded-lg mr-3 ${iconTintClass(iconColor)}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-sm text-ink-muted">{description}</p>
        </div>
      </div>
      <button
        onClick={handleClick}
        className="w-full bg-primary hover:bg-accent-hover text-ink-inverse py-2 rounded-button whitespace-nowrap transition-colors"
      >
        {action}
      </button>
    </div>
  );
}
