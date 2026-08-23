/**
 * MaskUploader — 拖拽上传黑白蒙版图
 */
import { useCallback, useRef, useState } from 'react';

const MAX_SIZE = 10 * 1024 * 1024; // 10MB

interface Props {
  file: File | null;
  preview: string | null;
  onChange: (file: File | null, preview: string | null) => void;
}

export default function MaskUploader({ file, preview, onChange }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSet = useCallback((f: File) => {
    setError(null);
    if (!f.type.startsWith('image/')) {
      setError('请上传图片文件');
      return;
    }
    if (f.size > MAX_SIZE) {
      setError(`文件过大（${(f.size / 1024 / 1024).toFixed(1)}MB），上限 10MB`);
      return;
    }
    const url = URL.createObjectURL(f);
    if (preview) URL.revokeObjectURL(preview);
    onChange(f, url);
  }, [onChange, preview]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) validateAndSet(f);
  }, [validateAndSet]);

  const handleClear = useCallback(() => {
    if (preview) URL.revokeObjectURL(preview);
    onChange(null, null);
    setError(null);
  }, [onChange, preview]);

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-slate-300">蒙版图片</label>
      <p className="text-xs text-slate-500">
        白色区域为需要修改的部分，黑色为保留区域
      </p>

      {preview ? (
        <div className="relative group rounded-lg overflow-hidden border border-slate-600 bg-slate-800">
          <img
            src={preview}
            alt="蒙版预览"
            className="w-full max-h-48 object-contain"
          />
          <button
            onClick={handleClear}
            className="absolute top-2 right-2 px-2 py-1 text-xs bg-red-600/80 hover:bg-red-600 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity"
          >
            移除
          </button>
        </div>
      ) : (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onClick={() => inputRef.current?.click()}
          className={`
            flex flex-col items-center justify-center gap-2 p-6
            border-2 border-dashed rounded-lg cursor-pointer transition-colors
            ${dragOver
              ? 'border-purple-500 bg-purple-500/10'
              : 'border-slate-600 hover:border-slate-500 bg-slate-800/50'
            }
          `}
        >
          <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span className="text-sm text-slate-400">拖拽或点击上传蒙版</span>
          <span className="text-xs text-slate-500">黑白图片，白色 = 修改区域</span>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) validateAndSet(f);
          if (inputRef.current) inputRef.current.value = '';
        }}
        className="hidden"
      />

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
