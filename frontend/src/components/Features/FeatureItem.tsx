import { Feature } from '../../types';

export default function FeatureItem({ icon, iconColor, title, description }: Feature) {
  return (
    <div className="text-center">
      <div className={`w-16 h-16 ${iconColor} rounded-full flex items-center justify-center mx-auto mb-4`}>
        <i className={`fas ${icon} text-white text-xl`}></i>
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-slate-400">{description}</p>
    </div>
  );
}
