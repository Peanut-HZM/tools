/**
 * Img2ImgForm — 对话式图生图
 * 参考图 + 强度滑块 + 对话输入框
 */
import { useState } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import ImageUploader from '../components/ImageUploader';
import { useI18n } from '../../../../i18n';

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
          <label className="text-sm font-medium text-slate-300">{igT.form.strength}</label>
          <span className="text-xs text-slate-400 tabular-nums">{params.strength.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={params.strength}
          onChange={(e) => setParams({ strength: parseFloat(e.target.value) })}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>{igT.form.strengthMin}</span>
          <span>{igT.form.strengthMax}</span>
        </div>
      </div>

      {/* 对话输入框 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={igT.form.placeholder.img2img}
          disabled={loading || !referenceImage}
          className="flex-1 px-4 py-2 bg-slate-700 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={loading || !prompt.trim() || !referenceImage}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {igT.chat.send}
        </button>
      </div>
    </div>
  );
}