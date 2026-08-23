/**
 * Img2ImgForm — 图生图表单
 * prompt + ImageUploader + strength slider + size + n + model
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import ImageUploader from '../components/ImageUploader';
import { useI18n } from '../../../../i18n';

const SIZE_KEYS = ['1024x1024', '1024x1792', '1792x1024', '512x512', '768x768'] as const;

const MODEL_KEYS = [
  'auto',
  'doubao_seedream',
  'qwen_image',
  'dall_e_3',
  'sdxl',
] as const;

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function Img2ImgForm({ onPolish, polishing }: Props) {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const prompt = useImageGenStore((s) => s.prompt);
  const setPrompt = useImageGenStore((s) => s.setPrompt);
  const params = useImageGenStore((s) => s.params);
  const setParams = useImageGenStore((s) => s.setParams);
  const referenceImage = useImageGenStore((s) => s.referenceImage);
  const referenceImagePreview = useImageGenStore((s) => s.referenceImagePreview);
  const setReferenceImage = useImageGenStore((s) => s.setReferenceImage);

  const modelLabels: Record<string, string> = {
    auto: igT.form.modelAuto,
    doubao_seedream: igT.form.modelDoubao,
    qwen_image: igT.form.modelQwen,
    dall_e_3: igT.form.modelDalle,
    sdxl: igT.form.modelSdxl,
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

      {/* 提示词 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-300">{igT.form.prompt}</label>
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
          placeholder={igT.form.placeholder.img2img}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
      </div>

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

      {/* 尺寸 + 数量 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">{igT.form.size}</label>
          <select
            value={params.size}
            onChange={(e) => setParams({ size: e.target.value as any })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            {SIZE_KEYS.map((k) => (
              <option key={k} value={k}>{igT.size[k]}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">{igT.form.count}</label>
          <select
            value={params.n}
            onChange={(e) => setParams({ n: Number(e.target.value) })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            {[1, 2, 3, 4].map((n) => (
              <option key={n} value={n}>{igT.form.countItem.replace('{n}', String(n))}</option>
            ))}
          </select>
        </div>
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