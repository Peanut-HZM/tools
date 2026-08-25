/**
 * UploadEditForm — 对话式上传编辑
 * 参考图 + edit_type 选择 + 对话输入框
 */
import { useState } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import ImageUploader from '../components/ImageUploader';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import type { EditType } from '../../../../api/imageGenerationApi';

const EDIT_TYPE_KEYS = [
  'upscale',
  'denoise',
  'relight',
  'style_transfer',
  'background_remove',
] as const;

const EDIT_TYPE_LABELS: Record<string, string> = {
  upscale: 'editTypeUpscale',
  denoise: 'editTypeDenoise',
  relight: 'editTypeRelight',
  style_transfer: 'editTypeStyleTransfer',
  background_remove: 'editTypeBackgroundRemove',
};

export default function UploadEditForm() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const { chat, loading } = useImageGenerate();
  const referenceImage = useImageGenStore((s) => s.referenceImage);
  const referenceImagePreview = useImageGenStore((s) => s.referenceImagePreview);
  const setReferenceImage = useImageGenStore((s) => s.setReferenceImage);
  const params = useImageGenStore((s) => s.params);
  const setParams = useImageGenStore((s) => s.setParams);
  const [prompt, setPrompt] = useState('');

  const handleSend = async () => {
    if (!prompt.trim() || loading || !referenceImage) return;
    const userInput = prompt;
    setPrompt('');
    await chat(userInput, {
      edit_type: params.edit_type,
      referenceImage,
    });
  };

  return (
    <div className="space-y-4">
      {/* 参考图 */}
      <ImageUploader
        label={igT.form.editImage}
        file={referenceImage}
        preview={referenceImagePreview}
        onChange={setReferenceImage}
      />

      {/* 编辑类型 */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-ink-muted">{igT.form.editType}</label>
        <select
          value={params.edit_type}
          onChange={(e) => setParams({ edit_type: e.target.value as EditType })}
          className="w-full px-3 py-2 bg-surface-1 border border-border rounded-lg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {EDIT_TYPE_KEYS.map((k) => (
            <option key={k} value={k}>
              {igT.form[EDIT_TYPE_LABELS[k] as keyof typeof igT.form] as string}
            </option>
          ))}
        </select>
      </div>

      {/* 对话输入框 */}
      <div className="flex gap-2">
        <Input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={igT.form.placeholder.uploadEdit}
          disabled={loading || !referenceImage}
          className="flex-1"
        />
        <Button
          onClick={handleSend}
          disabled={loading || !prompt.trim() || !referenceImage}
          className="px-6"
        >
          {igT.chat.send}
        </Button>
      </div>
    </div>
  );
}
