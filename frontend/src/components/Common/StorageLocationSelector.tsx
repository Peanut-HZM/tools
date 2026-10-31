/**
 * StorageLocationSelector - 存储位置选择器
 *
 * 默认选中「仅保存在本机」；远程服务器不可用时隐藏「上传到服务器」选项。
 */
import React from 'react';
import type { StorageLocation } from '../../types/storage';

interface StorageLocationSelectorProps {
  value: StorageLocation;
  onChange: (value: StorageLocation) => void;
  /** 远程服务器是否可用；false 时隐藏上传选项 */
  serverAvailable: boolean;
}

const StorageLocationSelector: React.FC<StorageLocationSelectorProps> = ({
  value,
  onChange,
  serverAvailable,
}) => {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-ink">存储位置</label>

      <div className="space-y-2">
        <label className="flex items-start gap-2 p-2 border border-border rounded cursor-pointer hover:border-accent-cyan">
          <input
            type="radio"
            name="storage-location"
            value="local"
            checked={value === 'local'}
            onChange={() => onChange('local')}
            className="mt-1"
          />
          <span>
            <span className="block text-sm text-ink">仅保存在本机</span>
            <span className="block text-xs text-ink-faint">
              凭据不离开本机，更安全
            </span>
          </span>
        </label>

        {serverAvailable && (
          <label className="flex items-start gap-2 p-2 border border-border rounded cursor-pointer hover:border-accent-cyan">
            <input
              type="radio"
              name="storage-location"
              value="server"
              checked={value === 'server'}
              onChange={() => onChange('server')}
              className="mt-1"
            />
            <span>
              <span className="block text-sm text-ink">上传到服务器</span>
              <span className="block text-xs text-ink-faint">
                便于多设备访问，密文将离开本机
              </span>
            </span>
          </label>
        )}
      </div>

      {!serverAvailable && (
        <p className="text-xs text-ink-faint">
          当前未配置远程服务器，所有凭据将仅保存在本机。
        </p>
      )}
    </div>
  );
};

export default StorageLocationSelector;
