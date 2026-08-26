/**
 * Img2ImgForm — 对话式图生图
 * 参考图 + 强度滑块 + 对话输入框
 */
import { useState } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import ImageUploader from '../components/ImageUploader';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Slider } from '@/components/ui/Slider';

export default function Img2ImgForm() {
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
      strength: params.strength,
      model_preference: params.model_preference,
      referenceImage,
    });
  };

  return (
    <div className="space-y-4">
      {/* 参考图 */}
      <ImageUploader
        label={igT.form.referenceImage}
        file={referenceImage}
        preview={referenceImagePreview}
        onChange={setReferenceImage}
      />

      {/* 强度滑块 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-ink-muted">{igT.form.strength}</label>
          <span className="text-xs text-ink-muted tabular-nums">{params.strength.toFixed(2)}</span>
        </div>
        <Slider
          min={0}
          max={1}
          step={0.05}
          value={[params.strength]}
          onValueChange={(v) => setParams({ strength: v[0] })}
          className="w-full"
        />
        <div className="flex justify-between text-[10px] text-ink-faint">
          <span>{igT.form.strengthMin}</span>
          <span>{igT.form.strengthMax}</span>
        </div>
      </div>

      {/* 对话输入框 */}
      <div className="flex gap-2">
        <Input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={igT.form.placeholder.img2img}
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
