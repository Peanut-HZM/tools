/**
 * UploadEditForm — 上传编辑表单
 * ImageUploader + edit_type select + 可选 prompt
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import ImageUploader from '../components/ImageUploader';

const EDIT_TYPES = [
  { value: 'upscale', label: '超分辨率放大' },
  { value: 'denoise', label: '降噪增强' },
  { value: 'relight', label: '重新打光' },
  { value: 'style_transfer', label: '风格迁移' },
  { value: 'background_remove', label: '去除背景' },
];

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function UploadEditForm({ onPolish, polishing }: Props) {
  const prompt = useImageGenStore((s) => s.prompt);
  const setPrompt = useImageGenStore((s) => s.setPrompt);
  const params = useImageGenStore((s) => s.params);
  const setParams = useImageGenStore((s) => s.setParams);
  const referenceImage = useImageGenStore((s) => s.referenceImage);
  const referenceImagePreview = useImageGenStore((s) => s.referenceImagePreview);
  const setReferenceImage = useImageGenStore((s) => s.setReferenceImage);

  return (
    <div className="space-y-4">
      {/* 上传图片 */}
      <ImageUploader
        label="待编辑图片"
        file={referenceImage}
        preview={referenceImagePreview}
        onChange={setReferenceImage}
      />

      {/* 编辑类型 */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">编辑类型</label>
        <select
          value={params.edit_type}
          onChange={(e) => setParams({ edit_type: e.target.value as any })}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {EDIT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>

      {/* 可选提示词 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-300">补充描述（可选）</label>
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
          rows={2}
          placeholder="对编辑效果的额外描述..."
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
      </div>
    </div>
  );
}
