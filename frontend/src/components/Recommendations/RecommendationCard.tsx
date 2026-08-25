import { Recommendation } from '../../types';
import { useI18n, interpolate } from '../../i18n';

export default function RecommendationCard({ icon, iconColor, title, description, action }: Recommendation) {
  const { t } = useI18n();

  const handleClick = () => {
    alert(interpolate(t.errors.toolNotImplemented, { toolId: title }));
  };

  return (
    <div className="bg-surface-1 rounded-xl p-6 border border-border">
      <div className="flex items-center mb-4">
        <div className={`w-10 h-10 ${iconColor} rounded-lg flex items-center justify-center mr-3`}>
          <i className={`fas ${icon} text-ink-inverse`}></i>
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
