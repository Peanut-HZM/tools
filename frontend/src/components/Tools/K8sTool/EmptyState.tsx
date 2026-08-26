/**
 * K8s 工具 - 空状态组件
 * 未选择任何集群连接时在右侧主区域显示
 */
import React from 'react';
import { Circle } from 'lucide-react';
import { useI18n } from '../../../i18n';

export const EmptyState: React.FC = () => {
  const { t } = useI18n();

  return (
    <div className="flex-1 flex flex-col items-center justify-center text-ink-faint bg-canvas">
      {/* K8s 图标：使用圆形象征集群（替代法轮） */}
      <Circle className="w-16 h-16 mb-4 opacity-20" />
      <p className="text-lg mb-2">{t.tools['k8s-tool'].selectConnection}</p>
      <p className="text-sm text-ink-faint">
        {t.tools['k8s-tool'].emptyConnections}
      </p>
    </div>
  );
};
