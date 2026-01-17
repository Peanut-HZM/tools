/**
 * SettingsDialog Component - Editor configuration
 */
import { useCallback } from 'react';
import type { EditorConfig } from '../../../types/markdownEditor';

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
  config: EditorConfig;
  onConfigChange: (updates: Partial<EditorConfig>) => void;
  onSave: () => void;
}

export default function SettingsDialog({
  open,
  onClose,
  config,
  onConfigChange,
  onSave
}: SettingsDialogProps) {
  const handleSave = useCallback(() => {
    onSave();
    onClose();
  }, [onSave, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-md">
        {/* Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">设置</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 max-h-[60vh] overflow-auto">
          {/* Theme */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              主题
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => onConfigChange({ theme: 'light' })}
                className={`flex-1 py-2 rounded text-sm cursor-pointer ${
                  config.theme === 'light'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                亮色
              </button>
              <button
                onClick={() => onConfigChange({ theme: 'dark' })}
                className={`flex-1 py-2 rounded text-sm cursor-pointer ${
                  config.theme === 'dark'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                暗色
              </button>
            </div>
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              语言
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => onConfigChange({ language: 'zh-CN' })}
                className={`flex-1 py-2 rounded text-sm cursor-pointer ${
                  config.language === 'zh-CN'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                中文
              </button>
              <button
                onClick={() => onConfigChange({ language: 'en-US' })}
                className={`flex-1 py-2 rounded text-sm cursor-pointer ${
                  config.language === 'en-US'
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                English
              </button>
            </div>
          </div>

          {/* Font Size */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              字体大小: {config.fontSize}px
            </label>
            <input
              type="range"
              min="8"
              max="32"
              value={config.fontSize}
              onChange={(e) => onConfigChange({ fontSize: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>

          {/* Tab Size */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Tab 大小: {config.tabSize}
            </label>
            <input
              type="range"
              min="1"
              max="8"
              value={config.tabSize}
              onChange={(e) => onConfigChange({ tabSize: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>

          {/* Auto Save Interval */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              自动保存间隔: {config.autoSaveInterval}秒
            </label>
            <input
              type="range"
              min="5"
              max="300"
              step="5"
              value={config.autoSaveInterval}
              onChange={(e) => onConfigChange({ autoSaveInterval: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>

          {/* Toggles */}
          <div className="space-y-3">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-slate-300">显示行号</span>
              <input
                type="checkbox"
                checked={config.showLineNumbers}
                onChange={(e) => onConfigChange({ showLineNumbers: e.target.checked })}
                className="rounded"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-slate-300">使用空格缩进</span>
              <input
                type="checkbox"
                checked={config.useSpaces}
                onChange={(e) => onConfigChange({ useSpaces: e.target.checked })}
                className="rounded"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-slate-300">自动换行</span>
              <input
                type="checkbox"
                checked={config.wordWrap ?? true}
                onChange={(e) => onConfigChange({ wordWrap: e.target.checked })}
                className="rounded"
              />
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-400 hover:text-white cursor-pointer"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm bg-cyan-500 hover:bg-cyan-600 text-white rounded cursor-pointer"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
}
