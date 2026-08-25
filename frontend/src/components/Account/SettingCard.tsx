import React from 'react';

interface SettingCardProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export default function SettingCard({ title, icon, children, className = '' }: SettingCardProps) {
  return (
    <div className={`bg-surface-1/50 backdrop-blur-sm border border-border/50 rounded-xl p-6 hover:border-border/50 transition-all duration-200 ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-ink-inverse mb-4 flex items-center gap-2">
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
