import { Statistic } from '../../types';
import { useI18n } from '../../i18n';

export default function Statistics() {
  const { t } = useI18n();

  const statistics: Statistic[] = [
    { value: '50+', label: t.stats.toolsCount },
    { value: '10K+', label: t.stats.dailyUsage },
    { value: '99.9%', label: t.stats.uptime },
    { value: '4.8', label: t.stats.rating }
  ];

  return (
    <section className="mb-16">
      <div className="bg-slate-800 rounded-xl p-8 border border-slate-700">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-center">
          {statistics.map((stat, index) => (
            <div key={index}>
              <div className="text-3xl font-bold text-primary mb-2">{stat.value}</div>
              <div className="text-slate-400">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
