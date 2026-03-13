/**
 * 批量操作组件
 */
import { useState } from 'react';
import { Download, Tag, X, CheckSquare } from 'lucide-react';
import { API_BASE_URL } from '../../../config/api';
import { useToast } from '../../../hooks/useToast';

interface BatchActionsProps {
  selectedIds: string[];
  onClearSelection: () => void;
  onRefresh?: () => void;
}

export default function BatchActions({ selectedIds, onClearSelection, onRefresh }: BatchActionsProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [showTagModal, setShowTagModal] = useState(false);
  const [tagName, setTagName] = useState('');

  const handleExport = async () => {
    if (selectedIds.length === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/batch/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ composer_ids: selectedIds }),
      });

      const result = await response.json();

      if (result.success) {
        // 下载 ZIP 文件
        const link = document.createElement('a');
        link.href = `data:application/zip;base64,${result.data}`;
        link.download = result.filename || 'cursor_sessions.zip';
        link.click();

        toast({
          title: '导出成功',
          description: `已导出 ${selectedIds.length} 个会话`,
        });
        onClearSelection();
      } else {
        toast({
          title: '导出失败',
          description: result.message || '请稍后重试',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('批量导出失败:', error);
      toast({
        title: '导出失败',
        description: '请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async () => {
    if (!tagName.trim() || selectedIds.length === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/batch/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          composer_ids: selectedIds,
          tag_name: tagName.trim()
        }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: '添加成功',
          description: result.message,
        });
        setShowTagModal(false);
        setTagName('');
        onClearSelection();
        onRefresh?.();
      } else {
        toast({
          title: '添加失败',
          description: result.message || '请稍后重试',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('批量添加标签失败:', error);
      toast({
        title: '添加失败',
        description: '请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  if (selectedIds.length === 0) {
    return null;
  }

  return (
    <>
      <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-gray-900 dark:bg-gray-800 text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-4 z-50 border border-gray-700">
        <span className="text-sm font-medium">
          已选择 {selectedIds.length} 个会话
        </span>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="批量导出"
            disabled={loading}
          >
            <Download className="w-4 h-4" />
          </button>

          <button
            onClick={() => setShowTagModal(true)}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="批量添加标签"
            disabled={loading}
          >
            <Tag className="w-4 h-4" />
          </button>

          <button
            onClick={onClearSelection}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="取消选择"
            disabled={loading}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {showTagModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowTagModal(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">批量添加标签</h3>
              <button onClick={() => setShowTagModal(false)} className="text-gray-500 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              将为 {selectedIds.length} 个会话添加标签
            </p>

            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">标签名称</label>
              <input
                type="text"
                value={tagName}
                onChange={(e) => setTagName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
                placeholder="输入标签名称..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-transparent"
                autoFocus
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowTagModal(false)}
                className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleAddTag}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 transition-colors"
                disabled={!tagName.trim() || loading}
              >
                确定
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
