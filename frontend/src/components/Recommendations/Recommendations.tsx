import RecommendationCard from './RecommendationCard';
import { Recommendation } from '../../types';
import { useI18n } from '../../i18n';

export default function Recommendations() {
  const { t } = useI18n();

  const recommendations: Recommendation[] = [
    {
      icon: 'fa-file-pdf',
      iconColor: 'bg-blue-500',
      title: t.recommendations.items.pdfToWord.title,
      description: t.recommendations.items.pdfToWord.desc,
      action: t.recommendations.action
    },
    {
      icon: 'fa-compress',
      iconColor: 'bg-green-500',
      title: t.recommendations.items.imageCompress.title,
      description: t.recommendations.items.imageCompress.desc,
      action: t.recommendations.action
    },
    {
      icon: 'fa-lock',
      iconColor: 'bg-purple-500',
      title: t.recommendations.items.passwordGen.title,
      description: t.recommendations.items.passwordGen.desc,
      action: t.recommendations.action
    }
  ];

  return (
    <section className="mb-16">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-4">{t.recommendations.title}</h2>
        <p className="text-slate-400">{t.recommendations.subtitle}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {recommendations.map((rec, index) => (
          <RecommendationCard key={index} {...rec} />
        ))}
      </div>
    </section>
  );
}
