import FeatureItem from './FeatureItem';
import { Feature } from '../../types';
import { useI18n } from '../../i18n';

export default function Features() {
  const { t } = useI18n();

  const features: Feature[] = [
    {
      icon: 'fa-bolt',
      iconColor: 'bg-blue-500',
      title: t.features.efficient,
      description: t.features.efficientDesc
    },
    {
      icon: 'fa-shield-alt',
      iconColor: 'bg-green-500',
      title: t.features.secure,
      description: t.features.secureDesc
    },
    {
      icon: 'fa-sync-alt',
      iconColor: 'bg-purple-500',
      title: t.features.update,
      description: t.features.updateDesc
    }
  ];

  return (
    <section className="mb-16">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold mb-4">{t.features.whyChoose} </h2>
        <p className="text-slate-400 max-w-2xl mx-auto">
          {t.features.whyChooseDesc}
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {features.map((feature, index) => (
          <FeatureItem key={index} {...feature} />
        ))}
      </div>
    </section>
  );
}
