/**
 * Text2ImgForm — 文生图表单
 * prompt + size + n + style + model_preference + 润色按钮
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';

const SIZES = [
  { value: '1024x1024', label: '1024×1024（正方形）' },
  { value: '1024x1792', label: '1024×1792（竖版）' },
  { value: '1792x1024', label: '1792×1024（横版）' },
  { value: '512x512', label: '512×512（小正方形）' },
  { value: '768x768', label: '768×768（中正方形）' },
];

const MODELS = [
  { value: 'auto', label: '自动选择' },
  { value: 'doubao_seedream', label: '豆包 Seedream' },
  { value: 'qwen_image', label: '通义万相' },
  { value: 'dall_e_3', label: 'DALL·E 3' },
  { value: 'sdxl', label: 'Stable Diffusion XL' },
];

const STYLES = [
  { value: '', label: '默认' },
  { value: 'photographic', label: '摄影' },
  { value: 'anime', label: '动漫' },
  { value: 'digital-art', label: '数字艺术' },
  { value: 'comic-book', label: '漫画' },
  { value: 'fantasy-art', label: '奇幻' },
  { value: 'line-art', label: '线稿' },
  { value: '3d-model', label: '3D 模型' },
];

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function Text2ImgForm({ onPolish, polishing }: Props) {
  const prompt = useImageGenStore((s) => s.prompt);
  const setPrompt = useImageGenStore((s) => s.setPrompt);
  const params = useImageGenStore((s) => s.params);
  const setParams = useImageGenStore((s) => s.setParams);

  return (
    <div className="space-y-4">
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
            {polishing ? '润色中...' : '✨ 润色提示词'}
          </button>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          placeholder="描述你想生成的图像内容..."
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 resize-none"
        />
      </div>

      {/* 尺寸 */}
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

        {/* 生成数量 */}
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

      {/* 风格 */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">图片风格</label>
        <select
          value={params.style}
          onChange={(e) => setParams({ style: e.target.value })}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {STYLES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      {/* 模型偏好 */}
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
