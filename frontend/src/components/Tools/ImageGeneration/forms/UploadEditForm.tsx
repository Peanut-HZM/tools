/**
 * UploadEditForm — 上传编辑表单
 * ImageUploader + edit_type select + 可选 prompt
 */
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import ImageUploader from '../components/ImageUploader';
import { useI18n } from '../../../../i18n';

const EDIT_TYPE_KEYS = [
  'upscale',
  'denoise',
  'relight',
  'style_transfer',
  'background_remove',
] as const;

const EDIT_TYPE_LABELS: Record<string, string> = {
  upscale: 'editTypeUpscale',
  denoise: 'editTypeDenoise',
  relight: 'editTypeRelight',
  style_transfer: 'editTypeStyleTransfer',
  background_remove: 'editTypeBackgroundRemove',
};

interface Props {
  onPolish: () => void;
  polishing?: boolean;
}

export default function UploadEditForm({ onPolish, polishing }: Props) {
  const { t } = useI18n();
  const igT = t.imageGeneration;
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
        label={igT.form.editImage}
        file={referenceImage}
        preview={referenceImagePreview}
        onChange={setReferenceImage}
      />

      {/* 编辑类型 */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-300">{igT.form.editType}</label>
        <select
          value={params.edit_type}
          onChange={(e) => setParams({ edit_type: e.target.value as any })}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {EDIT_TYPE_KEYS.map((k) => (
            <option key={k} value={k}>
              {igT.form[EDIT_TYPE_LABELS[k] as keyof typeof igT.form] as string}
            </option>
          ))}
        </select>
      </div>

      {/* 可选提示词 */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-300">{igT.form.uploadEditPrompt}</label>
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
          rows={2}
          placeholder={igT.form.placeholder.uploadEdit}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
      </div>
    </div>
  );
}