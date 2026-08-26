import React from 'react';
import { Terminal } from 'lucide-react';
import { useI18n } from '../../../i18n';

export const EmptyState: React.FC = () => {
  const { t } = useI18n();
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-ink-faint bg-canvas">
      <Terminal className="w-16 h-16 mb-4 opacity-20" />
      <p className="text-lg">{t.ssh.selectConnection}</p>
    </div>
  );
};
