/**
 * Text2ImgForm — 文生图表单
 * prompt + size + n + style + model_preference + 润色按钮
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useI18n } from '../../../../i18n';

const SIZE_KEYS = ['1024x1024', '1024x1792', '1792x1024', '512x512', '768x768'] as const;

const MODEL_KEYS = [
  'auto',
  'doubao_seedream',
  'qwen_image',
  'dall_e_3',
  'sdxl',
] as const;

const STYLE_KEYS = [
  '',
  'photographic',
  'anime',
  'digital-art',
  'comic-book',
  'fantasy-art',
  'line-art',
  '3d-model',
] as const;

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function Text2ImgForm({ onPolish, polishing }: Props) {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const prompt = useImageGenStore((s) => s.prompt);
  const setPrompt = useImageGenStore((s) => s.setPrompt);
  const params = useImageGenStore((s) => s.params);
  const setParams = useImageGenStore((s) => s.setParams);

  const modelLabels: Record<string, string> = {
    auto: igT.form.modelAuto,
    doubao_seedream: igT.form.modelDoubao,
    qwen_image: igT.form.modelQwen,
    dall_e_3: igT.form.modelDalle,
    sdxl: igT.form.modelSdxl,
  };

  return (
    <div className="space-y-4">
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
            {polishing ? igT.form.polishing : `✨ ${igT.form.polishPrompt}`}
          </button>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          placeholder={igT.form.placeholder.text2img}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 resize-none"
        />
      </div>

      {/* 尺寸 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">{igT.form.size}</label>
          <select
            value={params.size}
            onChange={(e) => setParams({ size: e.target.value as any })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            {SIZE_KEYS.map((k) => (
              <option key={k} value={k}>{igT.sizeLabel[k]}</option>
            ))}
          </select>
        </div>

        {/* 生成数量 */}
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

      {/* 风格 */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">{igT.form.style}</label>
        <select
          value={params.style}
          onChange={(e) => setParams({ style: e.target.value })}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {STYLE_KEYS.map((k) => (
            <option key={k} value={k}>{k === '' ? igT.form.styleDefault : igT.styleLabel[k as keyof typeof igT.styleLabel] ?? k}</option>
          ))}
        </select>
      </div>

      {/* 模型偏好 */}
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