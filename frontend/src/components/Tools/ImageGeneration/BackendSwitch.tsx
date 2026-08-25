/**
 * 图像生成后端切换组件
 * localStorage 键: image_gen_backend
 * 可选值: 'dify' | 'selfdev'
 */

import { useState } from 'react';

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
      <button
        onClick={() => handleChange('dify')}
        className={`px-4 py-1 rounded text-sm transition ${
          backend === 'dify'
            ? 'bg-accent text-white'
            : 'text-ink-muted hover:text-ink'
        }`}
      >
        Dify
      </button>
      <button
        onClick={() => handleChange('selfdev')}
        className={`px-4 py-1 rounded text-sm transition ${
          backend === 'selfdev'
            ? 'bg-accent text-white'
            : 'text-ink-muted hover:text-ink'
        }`}
      >
        自研 Agent
      </button>
    </div>
  );
}
