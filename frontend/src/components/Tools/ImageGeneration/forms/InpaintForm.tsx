/**
 * InpaintForm — 局部重绘表单
 * prompt + ImageUploader (参考图) + MaskUploader (蒙版)
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import ImageUploader from '../components/ImageUploader';
import MaskUploader from '../components/MaskUploader';
import { useI18n } from '../../../../i18n';

const MODEL_KEYS = [
  'auto',
  'doubao_seedream',
  'qwen_image',
  'sdxl',
] as const;

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function InpaintForm({ onPolish, polishing }: Props) {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const prompt = useImageGenStore((s) => s.prompt);
  const setPrompt = useImageGenStore((s) => s.setPrompt);
  const params = useImageGenStore((s) => s.params);
  const setParams = useImageGenStore((s) => s.setParams);
  const referenceImage = useImageGenStore((s) => s.referenceImage);
  const referenceImagePreview = useImageGenStore((s) => s.referenceImagePreview);
  const setReferenceImage = useImageGenStore((s) => s.setReferenceImage);
  const maskImage = useImageGenStore((s) => s.maskImage);
  const maskImagePreview = useImageGenStore((s) => s.maskImagePreview);
  const setMaskImage = useImageGenStore((s) => s.setMaskImage);

  const modelLabels: Record<string, string> = {
    auto: igT.form.modelAuto,
    doubao_seedream: igT.form.modelDoubao,
    qwen_image: igT.form.modelQwen,
    sdxl: igT.form.modelSdxl,
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

      {/* 提示词 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-300">{igT.form.inpaintPrompt}</label>
          <button
            type="button"
            onClick={onPolish}
            disabled={polishing}
            className="px-2.5 py-1 text-xs bg-purple-600/20 text-purple-400 hover:bg-purple-600/30 rounded transition-colors disabled:opacity-50"
          >
            {polishing ? igT.form.polishing : `✨ ${igT.form.polishShort}`}
          </button>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          placeholder={igT.form.placeholder.inpaint}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
      </div>

      {/* 模型 */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">{igT.form.modelPreference}</label>
        <select
          value={params.model_preference}
          onChange={(e) => setParams({ model_preference: e.target.value as any })}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {MODEL_KEYS.map((m) => (
            <option key={m} value={m}>{modelLabels[m] ?? m}</option>
          ))}
        </select>
      </div>
    </div>
  );
}