/**
 * 图像生成后端切换组件
 * localStorage 键: image_gen_backend
 * 可选值: 'dify' | 'selfdev'
 */

import { useState } from 'react';
import { Button } from '@/components/ui/Button';

const STORAGE_KEY = 'image_gen_backend';

export type ImageGenBackend = 'dify' | 'selfdev';

export function getBackend(): ImageGenBackend {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === 'dify' || raw === 'selfdev') return raw;
  return 'selfdev';
}

export function setBackend(b: ImageGenBackend): void {
  localStorage.setItem(STORAGE_KEY, b);
}

export default function BackendSwitch() {
  const [backend, setBackendState] = useState<ImageGenBackend>(getBackend());

  const handleChange = (b: ImageGenBackend) => {
    setBackend(b);
    setBackendState(b);
    // 触发 storage 事件，让其他组件感知
    window.dispatchEvent(new Event('image-gen-backend-changed'));
  };

  return (
    <div className="inline-flex rounded-lg bg-surface-1 p-1">
      <Button
        variant={backend === 'dify' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => handleChange('dify')}
      >
        Dify
      </Button>
      <Button
        variant={backend === 'selfdev' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => handleChange('selfdev')}
      >
        自研 Agent
      </Button>
    </div>
  );
}
