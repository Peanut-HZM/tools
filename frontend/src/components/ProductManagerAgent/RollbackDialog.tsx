import React, { useState } from 'react';
import { PRDVersion } from '../../services/prdApi';

interface RollbackDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (targetVersion: number) => Promise<void>;
  targetVersion: PRDVersion | null;
  currentVersion: PRDVersion | null;
}

const RollbackDialog: React.FC<RollbackDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  targetVersion,
  currentVersion,
}) => {
  const [confirming, setConfirming] = useState(false);

  if (!isOpen || !targetVersion) return null;

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      await onConfirm(targetVersion.version_number);
      onClose();
    } catch (error) {
      console.error('回滚失败:', error);
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Background Overlay */}
      <div 
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />
      
      {/* Dialog */}
      <div className="relative bg-slate-800 rounded-xl shadow-2xl w-full max-w-md mx-4 border border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">回滚 PRD 版本</h2>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {/* Warning Icon */}
          <div className="flex items-center justify-center mb-4">
            <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>

          {/* Warning Message */}
          <div className="text-center mb-6">
            <p className="text-white font-medium mb-2">
              确定要回滚到版本 {targetVersion.version_number} 吗？
            </p>
            <p className="text-sm text-slate-400">
              回滚将创建一个新版本，内容基于选中的版本。当前版本 <strong>V{currentVersion?.version_number}</strong> 不会被删除。
            </p>
          </div>

          {/* Version Info */}
          <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-slate-400 text-sm">目标版本</span>
              <span className="text-white font-medium">V{targetVersion.version_number}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400 text-sm">创建时间</span>
              <span className="text-slate-300 text-sm">
                {new Date(targetVersion.created_at).toLocaleString('zh-CN')}
              </span>
            </div>
          </div>

          {/* Checkbox for Confirmation */}
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              id="confirm-rollback"
              className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500"
            />
            <span className="text-sm text-slate-300">
              我了解回滚将创建一个新的版本
            </span>
          </label>
        </div>

        {/* Footer Buttons */}
        <div className="flex items-center justify-end gap-3 p-5 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
            disabled={confirming}
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={confirming}
            className="px-6 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {confirming ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                回滚中...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                </svg>
                确认回滚
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RollbackDialog;
