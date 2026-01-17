import FeatureItem from './FeatureItem';
import { Feature } from '../../types';

export default function Features() {
  const features: Feature[] = [
    {
      icon: 'fa-bolt',
      iconColor: 'bg-blue-500',
      title: '高效便捷',
      description: '一键操作，无需复杂设置，快速完成任务'
    },
    {
      icon: 'fa-shield-alt',
      iconColor: 'bg-green-500',
      title: '安全可靠',
      description: '本地处理，数据不上传，保护您的隐私安全'
    },
    {
      icon: 'fa-sync-alt',
      iconColor: 'bg-purple-500',
      title: '持续更新',
      description: '定期添加新工具，满足不断变化的需求'
    }
  ];

  return (
    <section className="mb-16">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold mb-4">为什么选择 </h2>
        <p className="text-slate-400 max-w-2xl mx-auto">
          我们致力于提供最实用、最高效的工具集合，让复杂的工作变得简单
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
