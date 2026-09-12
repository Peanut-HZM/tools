import React from 'react';
import { Card } from '@/components/ui/Card';

interface SettingCardProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export default function SettingCard({ title, icon, children, className = '' }: SettingCardProps) {
  // 玻璃化改版：统一走设计系统玻璃卡片，保留原内边距与过渡动画
  return (
    <Card className={`glass-card rounded-xl p-6 transition-all duration-200 ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-ink mb-4 flex items-center gap-2">
          {icon}
          {title}
        </h3>
      )}
      <div>
        {children}
      </div>
    </Card>
  );
}
