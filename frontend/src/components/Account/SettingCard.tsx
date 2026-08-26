import React from 'react';
import { Card } from '@/components/ui/Card';

interface SettingCardProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export default function SettingCard({ title, icon, children, className = '' }: SettingCardProps) {
  return (
    <Card className={`backdrop-blur-sm bg-surface-1/50 border-border/50 p-6 transition-all duration-200 ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-ink-inverse mb-4 flex items-center gap-2">
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
