/**
 * ImageGeneration — 图像生成主页面
 *
 * 单列布局：顶部操作栏 → Tab + 表单 → 历史抽屉
 * 生成结果由各表单组件内联展示
 */
import { useImageGenStore } from '../../../stores/imageGenerationStore';
import { useAuth } from '../../../stores/authStore';
import { useI18n } from '../../../i18n';
import RequireAuthNotice from '../../Common/RequireAuthNotice';

// 表单组件
import Text2ImgForm from './forms/Text2ImgForm';
import Img2ImgForm from './forms/Img2ImgForm';
import InpaintForm from './forms/InpaintForm';
import UploadEditForm from './forms/UploadEditForm';

// 公共组件
import QuotaBadge from './components/QuotaBadge';
import ResultPanel from './components/ResultPanel';
import HistoryDrawer from './components/HistoryDrawer';
import BackendSwitch from './BackendSwitch';

import type { Operation } from '../../../api/imageGenerationApi';

const TABS: { key: Operation; icon: string }[] = [
  { key: 'text2img', icon: '✍️' },
  { key: 'img2img', icon: '🖼️' },
  { key: 'inpaint', icon: '🎯' },
  { key: 'upload_edit', icon: '🔧' },
];

export default function ImageGeneration() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const tabLabels: Record<Operation, string> = {
    text2img: igT.tabs.text2img,
    img2img: igT.tabs.img2img,
    inpaint: igT.tabs.inpaint,
    upload_edit: igT.tabs.uploadEdit,
  };
  const tabs = TABS.map((tab) => ({ ...tab, label: tabLabels[tab.key] }));

  const { isAuthenticated } = useAuth();
  const operation = useImageGenStore((s) => s.operation);
  const setOperation = useImageGenStore((s) => s.setOperation);
  const setHistoryDrawerOpen = useImageGenStore((s) => s.setHistoryDrawerOpen);
  const reset = useImageGenStore((s) => s.reset);
  const currentResult = useImageGenStore((s) => s.currentResult);
  const loading = useImageGenStore((s) => s.loading);

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-6 py-8">
        <RequireAuthNotice />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 max-w-7xl">
      {/* 顶部：后端切换 + 配额 + 操作 */}
      <div className="flex items-center justify-between mb-4">
        <BackendSwitch />
        <div className="flex items-center gap-3">
          <QuotaBadge />
          <button
            onClick={() => setHistoryDrawerOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {igT.history.title}
          </button>
          <button
            onClick={reset}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {igT.form.reset}
          </button>
        </div>
      </div>

      {/* 主体：Tab + 表单 */}
      <div className="space-y-3">
        {/* Tab 栏 */}
        <div className="flex gap-1 p-1 bg-slate-800 rounded-xl">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setOperation(tab.key)}
              className={`
                flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm font-medium rounded-lg transition-all
                ${operation === tab.key
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                }
              `}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* 表单 */}
        <div className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl">
          {operation === 'text2img' && <Text2ImgForm />}
          {operation === 'img2img' && <Img2ImgForm />}
          {operation === 'inpaint' && <InpaintForm />}
          {operation === 'upload_edit' && <UploadEditForm />}
        </div>
      </div>

      {/* 生成结果：仅在有结果或加载中时显示 */}
      {(loading || currentResult) && (
        <div className="mt-3 p-3 bg-slate-800/50 border border-slate-700/50 rounded-xl">
          <ResultPanel />
        </div>
      )}

      {/* 历史抽屉 */}
      <HistoryDrawer />
    </div>
  );
}