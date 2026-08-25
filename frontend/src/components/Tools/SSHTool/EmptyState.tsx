import React from 'react';
import { useI18n } from '../../../i18n';

export const EmptyState: React.FC = () => {
  const { t } = useI18n();
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-ink-faint bg-canvas">
      <i className="fas fa-terminal text-6xl mb-4 opacity-20"></i>
      <p className="text-lg">{t.ssh.selectConnection}</p>
    </div>
  );
};
