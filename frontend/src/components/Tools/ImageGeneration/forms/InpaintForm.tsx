/**
 * InpaintForm — 局部重绘表单
 * prompt + ImageUploader (参考图) + MaskUploader (蒙版)
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import ImageUploader from '../components/ImageUploader';
import MaskUploader from '../components/MaskUploader';

const MODELS = [
  { value: 'auto', label: '自动选择' },
  { value: 'doubao_seedream', label: '豆包 Seedream' },
  { value: 'qwen_image', label: '通义万相' },
  { value: 'sdxl', label: 'Stable Diffusion XL' },
];

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function InpaintForm({ onPolish, polishing }: Props) {
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

  return (
    <div className="space-y-4">
      {/* 参考图 */}
      <ImageUploader
        label="原图"
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
          <label className="text-sm font-medium text-slate-300">重绘内容描述</label>
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
          placeholder="描述蒙版区域要生成的内容..."
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
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
