import { Recommendation } from '../../types';

export default function RecommendationCard({ icon, iconColor, title, description, action }: Recommendation) {
  const handleClick = () => {
    alert(`跳转到 ${title} 工具页面`);
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
      <div className="flex items-center mb-4">
        <div className={`w-10 h-10 ${iconColor} rounded-lg flex items-center justify-center mr-3`}>
          <i className={`fas ${icon} text-white`}></i>
        </div>
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-sm text-slate-400">{description}</p>
        </div>
      </div>
      <button
        onClick={handleClick}
        className="w-full bg-primary hover:bg-blue-700 text-white py-2 rounded-button whitespace-nowrap transition-colors"
      >
        {action}
      </button>
    </div>
  );
}
