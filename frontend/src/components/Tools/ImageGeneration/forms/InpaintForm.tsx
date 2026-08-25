/**
 * InpaintForm — 对话式局部重绘
 * 参考图 + 蒙版图 + 对话输入框
 */
import { useState } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import ImageUploader from '../components/ImageUploader';
import MaskUploader from '../components/MaskUploader';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export default function InpaintForm() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const { chat, loading } = useImageGenerate();
  const referenceImage = useImageGenStore((s) => s.referenceImage);
  const referenceImagePreview = useImageGenStore((s) => s.referenceImagePreview);
  const setReferenceImage = useImageGenStore((s) => s.setReferenceImage);
  const maskImage = useImageGenStore((s) => s.maskImage);
  const maskImagePreview = useImageGenStore((s) => s.maskImagePreview);
  const setMaskImage = useImageGenStore((s) => s.setMaskImage);
  const [prompt, setPrompt] = useState('');

  const handleSend = async () => {
    if (!prompt.trim() || loading || !referenceImage || !maskImage) return;
    const userInput = prompt;
    setPrompt('');
    await chat(userInput, {
      referenceImage,
      maskImage,
    });
  };

  return (
    <div className="space-y-4">
      {/* 参考图 */}
      <ImageUploader
        label={igT.form.sourceImage}
        file={referenceImage}
        preview={referenceImagePreview}
        onChange={setReferenceImage}
      />

      {/* 蒙版 */}
      <MaskUploader
        file={maskImage}
        preview={maskImagePreview}
        onChange={setMaskImage}
      />

      {/* 对话输入框 */}
      <div className="flex gap-2">
        <Input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={igT.form.placeholder.inpaint}
          disabled={loading || !referenceImage || !maskImage}
          className="flex-1"
        />
        <Button
          onClick={handleSend}
          disabled={loading || !prompt.trim() || !referenceImage || !maskImage}
          className="px-6"
        >
          {igT.chat.send}
        </Button>
      </div>
    </div>
  );
}
