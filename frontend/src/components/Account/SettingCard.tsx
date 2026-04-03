import React from 'react';

interface SettingCardProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export default function SettingCard({ title, icon, children, className = '' }: SettingCardProps) {
  return (
    <div className={`bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 hover:border-slate-600/50 transition-all duration-200 ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          {icon}
          {title}
        </h3>
      )}
      <div>
        {children}
      </div>
    </div>
  );
}
