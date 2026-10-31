/**
 * StorageLocationBadge - 存储位置徽章
 *
 * 🔒 本机 / ☁️ 服务器
 *
 * 侧栏较窄时用 compact 模式只显示图标（hover 提示说明含义），
 * 避免文字徽章把连接别名挤成只剩首字母。
 */
import React from 'react';
import type { StorageLocation } from '../../types/storage';

interface StorageLocationBadgeProps {
  location: StorageLocation;
  /** 紧凑模式：只显示图标，省出横向空间（窄侧栏用） */
  compact?: boolean;
}

const StorageLocationBadge: React.FC<StorageLocationBadgeProps> = ({ location, compact }) => {
  const isLocal = location === 'local';
  const label = isLocal ? '本机' : '服务器';
  const hint = isLocal ? '凭据仅保存在本机，不会上传' : '凭据已上传到服务器';

  if (compact) {
    return (
      <span
        className={`inline-flex items-center justify-center w-4 h-4 rounded text-[10px] border shrink-0 ${
          isLocal
            ? 'border-accent-cyan/50 text-accent-cyan'
            : 'border-border text-ink-faint'
        }`}
        title={`${label} — ${hint}`}
        aria-label={`存储位置：${label}`}
      >
        {isLocal ? '🔒' : '☁️'}
      </span>
    );
  }

  return (
    <span
      // whitespace-nowrap + shrink-0：防止「服务器」被压成竖排换行
      className={`inline-flex items-center gap-0.5 px-1.5 py-0 rounded text-[10px] border whitespace-nowrap shrink-0 ${
        isLocal
          ? 'border-accent-cyan/50 text-accent-cyan'
          : 'border-border text-ink-faint'
      }`}
      title={hint}
    >
      {isLocal ? '🔒' : '☁️'} {label}
    </span>
  );
};

export default StorageLocationBadge;
