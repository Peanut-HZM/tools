import RecommendationCard from './RecommendationCard';
import { Recommendation } from '../../types';

export default function Recommendations() {
  const recommendations: Recommendation[] = [
    {
      icon: 'fa-file-pdf',
      iconColor: 'bg-blue-500',
      title: 'PDF 转 Word',
      description: '高精度转换，保持原有格式',
      action: '立即使用'
    },
    {
      icon: 'fa-compress',
      iconColor: 'bg-green-500',
      title: '图片压缩',
      description: '无损压缩，减小文件体积',
      action: '立即使用'
    },
    {
      icon: 'fa-lock',
      iconColor: 'bg-purple-500',
      title: '密码生成',
      description: '安全密码，自定义强度',
      action: '立即使用'
    }
  ];

  return (
    <section className="mb-16">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-4">热门推荐</h2>
        <p className="text-slate-400">最受欢迎的工具，大家都在用</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {recommendations.map((rec, index) => (
          <RecommendationCard key={index} {...rec} />
        ))}
      </div>
    </section>
  );
}
