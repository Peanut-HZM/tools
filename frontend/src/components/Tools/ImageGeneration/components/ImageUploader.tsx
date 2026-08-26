/**
 * ImageUploader — 拖拽上传 + 点击上传 + 预览 + 10MB 校验
 */
import { useCallback, useRef, useState } from 'react';
import { useI18n } from '../../../../i18n';
import { Card } from '@/components/ui/Card';

const MAX_SIZE = 10 * 1024 * 1024; // 10MB

interface Props {
  label?: string;
  file: File | null;
  preview: string | null;
  onChange: (file: File | null, preview: string | null) => void;
  error?: string;
}

export default function ImageUploader({ label, file, preview, onChange, error: externalError }: Props) {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const defaultLabel = label ?? igT.form.referenceImage;

  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSet = useCallback((f: File) => {
    setError(null);
    if (!f.type.startsWith('image/')) {
      setError(igT.form.invalidImageType);
      return;
    }
    if (f.size > MAX_SIZE) {
      setError(igT.form.fileTooLarge.replace('{size}', (f.size / 1024 / 1024).toFixed(1)));
      return;
    }
    const url = URL.createObjectURL(f);
    // 清理旧的 URL
    if (preview) URL.revokeObjectURL(preview);
    onChange(f, url);
  }, [onChange, preview, igT.form.invalidImageType, igT.form.fileTooLarge]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) validateAndSet(f);
  }, [validateAndSet]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) validateAndSet(f);
    // 清空 input value 以便重复上传同一文件
    if (inputRef.current) inputRef.current.value = '';
  }, [validateAndSet]);

  const handleClear = useCallback(() => {
    if (preview) URL.revokeObjectURL(preview);
    onChange(null, null);
    setError(null);
  }, [onChange, preview]);

  const displayError = externalError || error;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-ink-muted">{defaultLabel}</label>

      {preview ? (
        <Card className="relative group overflow-hidden">
          <img
            src={preview}
            alt={igT.form.preview}
            className="w-full max-h-48 object-contain"
          />
          <button
            onClick={handleClear}
            className="absolute top-2 right-2 px-2 py-1 text-xs bg-red-600/80 hover:bg-red-600 text-ink-inverse rounded opacity-0 group-hover:opacity-100 transition-opacity"
          >
            {igT.form.remove}
          </button>
        </Card>
      ) : (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => inputRef.current?.click()}
          className={`
            flex flex-col items-center justify-center gap-2 p-6
            border-2 border-dashed rounded-lg cursor-pointer transition-colors
            ${dragOver
              ? 'border-accent-info bg-accent-info/10'
              : 'border-border hover:border-border bg-surface-1/50'
            }
          `}
        >
          <svg className="w-8 h-8 text-ink-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-sm text-ink-muted">
            {igT.form.uploadHint}
          </span>
          <span className="text-xs text-ink-faint">
            {igT.form.uploadFormat}
          </span>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      {displayError && (
        <p className="text-xs text-danger">{displayError}</p>
      )}
    </div>
  );
}