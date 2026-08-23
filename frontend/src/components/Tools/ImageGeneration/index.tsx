/**
 * ImageGeneration — 图像生成主页面
 *
 * 顶部 QuotaBadge，左侧操作 Tab + 表单，右侧结果面板
 * HistoryDrawer 从右侧滑出
 */
import { useState, useCallback } from 'react';
import { useImageGenStore } from '../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../hooks/useImageGenerate';
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

  const { generate, abort, loading, error, setError } = useImageGenerate();
  const [polishing, setPolishing] = useState(false);

  const handlePolish = useCallback(async () => {
    setPolishing(true);
    try {
      await useImageGenStore.getState().polishPrompt();
    } finally {
      setPolishing(false);
    }
  }, []);

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-6 py-8">
        <RequireAuthNotice />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* 顶部：标题 + 配额 + 操作 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-slate-100">{igT.title}</h1>
          <QuotaBadge />
        </div>
        <div className="flex items-center gap-2">
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

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center justify-between">
          <span className="text-sm text-red-400">{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* 主体：左表单 + 右结果 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧：Tab + 表单 */}
        <div className="space-y-4">
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
          <div className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl">
            {operation === 'text2img' && <Text2ImgForm onPolish={handlePolish} polishing={polishing} />}
            {operation === 'img2img' && <Img2ImgForm onPolish={handlePolish} polishing={polishing} />}
            {operation === 'inpaint' && <InpaintForm onPolish={handlePolish} polishing={polishing} />}
            {operation === 'upload_edit' && <UploadEditForm onPolish={handlePolish} polishing={polishing} />}
          </div>

          {/* 生成按钮 */}
          <div className="flex gap-3">
            {loading ? (
              <button
                onClick={abort}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-500 text-white font-medium rounded-xl transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
                {igT.form.cancel}
              </button>
            ) : (
              <button
                onClick={generate}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl transition-colors shadow-lg shadow-blue-600/20"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                {igT.form.generate}
              </button>
            )}
          </div>
        </div>

        {/* 右侧：结果面板 */}
        <div className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl">
          <ResultPanel />
        </div>
      </div>

      {/* 历史抽屉 */}
      <HistoryDrawer />
    </div>
  );
}