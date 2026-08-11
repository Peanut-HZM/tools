/**
 * K8s 工具 - 空状态组件
 * 未选择任何集群连接时在右侧主区域显示
 */
import React from 'react';
import { useI18n } from '../../../i18n';

export const EmptyState: React.FC = () => {
  const { t } = useI18n();

  return (
    <div className="flex-1 flex flex-col items-center justify-center text-slate-500 bg-slate-900">
      {/* K8s 图标：使用 dharmachakra（法轮）象征集群 */}
      <i className="fas fa-dharmachakra text-6xl mb-4 opacity-20"></i>
      <p className="text-lg mb-2">{t.tools['k8s-tool'].selectConnection}</p>
      <p className="text-sm text-slate-600">
        {t.tools['k8s-tool'].emptyConnections}
      </p>
    </div>
  );
};
