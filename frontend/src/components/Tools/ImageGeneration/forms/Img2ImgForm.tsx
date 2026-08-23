/**
 * Img2ImgForm — 图生图表单
 * prompt + ImageUploader + strength slider + size + n + model
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import ImageUploader from '../components/ImageUploader';

const SIZES = [
  { value: '1024x1024', label: '1024×1024' },
  { value: '1024x1792', label: '1024×1792' },
  { value: '1792x1024', label: '1792×1024' },
  { value: '512x512', label: '512×512' },
  { value: '768x768', label: '768×768' },
];

const MODELS = [
  { value: 'auto', label: '自动选择' },
  { value: 'doubao_seedream', label: '豆包 Seedream' },
  { value: 'qwen_image', label: '通义万相' },
  { value: 'dall_e_3', label: 'DALL·E 3' },
  { value: 'sdxl', label: 'Stable Diffusion XL' },
];

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function Img2ImgForm({ onPolish, polishing }: Props) {
  const prompt = useImageGenStore((s) => s.prompt);
  const setPrompt = useImageGenStore((s) => s.setPrompt);
  const params = useImageGenStore((s) => s.params);
  const setParams = useImageGenStore((s) => s.setParams);
  const referenceImage = useImageGenStore((s) => s.referenceImage);
  const referenceImagePreview = useImageGenStore((s) => s.referenceImagePreview);
  const setReferenceImage = useImageGenStore((s) => s.setReferenceImage);

  return (
    <div className="space-y-4">
      {/* 参考图 */}
      <ImageUploader
        label="参考图片"
        file={referenceImage}
        preview={referenceImagePreview}
        onChange={setReferenceImage}
      />

      {/* 提示词 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-300">提示词</label>
          <button
            type="button"
            onClick={onPolish}
            disabled={polishing}
            className="px-2.5 py-1 text-xs bg-purple-600/20 text-purple-400 hover:bg-purple-600/30 rounded transition-colors disabled:opacity-50"
          >
            {polishing ? '润色中...' : '✨ 润色'}
          </button>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          placeholder="描述你希望的修改效果..."
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
      </div>

      {/* 强度滑块 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-300">变换强度</label>
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
          <span>保持原图</span>
          <span>大幅修改</span>
        </div>
      </div>

      {/* 尺寸 + 数量 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">图片尺寸</label>
          <select
            value={params.size}
            onChange={(e) => setParams({ size: e.target.value as any })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            {SIZES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">生成数量</label>
          <select
            value={params.n}
            onChange={(e) => setParams({ n: Number(e.target.value) })}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            {[1, 2, 3, 4].map((n) => (
              <option key={n} value={n}>{n} 张</option>
            ))}
          </select>
        </div>
      </div>

      {/* 模型 */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">模型偏好</label>
        <select
          value={params.model_preference}
          onChange={(e) => setParams({ model_preference: e.target.value as any })}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {MODELS.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
