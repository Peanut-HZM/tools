import { Statistic } from '../../types';

export default function Statistics() {
  const statistics: Statistic[] = [
    { value: '50+', label: '工具数量' },
    { value: '10K+', label: '每日使用' },
    { value: '99.9%', label: '服务可用' },
    { value: '4.8', label: '用户评分' }
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
