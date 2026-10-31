/**
 * StorageLocationBadge - 存储位置徽章
 *
 * 🔒 本机 / ☁️ 服务器
 */
import React from 'react';
import type { StorageLocation } from '../../types/storage';

interface StorageLocationBadgeProps {
  location: StorageLocation;
}

const StorageLocationBadge: React.FC<StorageLocationBadgeProps> = ({ location }) => {
  const isLocal = location === 'local';

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${
        isLocal
          ? 'border-accent-cyan/50 text-accent-cyan'
          : 'border-border text-ink-faint'
      }`}
      title={isLocal ? '凭据仅保存在本机，不会上传' : '凭据已上传到服务器'}
    >
      {isLocal ? '🔒' : '☁️'} {isLocal ? '本机' : '服务器'}
    </span>
  );
};

export default StorageLocationBadge;
