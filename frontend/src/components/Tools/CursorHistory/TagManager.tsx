/**
 * 标签管理器组件
 * 用于为会话添加/移除标签
 */
import { useState, useEffect } from 'react';
import { Tag, X, Plus } from 'lucide-react';
import { API_BASE_URL } from '../../../config/api';
import { useToast } from '../../../hooks/useToast';

interface TagManagerProps {
  composerId: string;
  onUpdate?: () => void;
}

interface TagItem {
  id: number;
  composer_id: string;
  tag_name: string;
  created_at: string;
}

const PRESET_TAGS = [
  'Bug 修复',
  '功能设计',
  '代码生成',
  '概念解释',
  '性能优化',
  '重构',
  '测试',
  '文档',
  '其他'
];

export default function TagManager({ composerId, onUpdate }: TagManagerProps) {
  const { toast } = useToast();
  const [tags, setTags] = useState<TagItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [customTag, setCustomTag] = useState('');

  // 加载标签
  useEffect(() => {
    loadTags();
  }, [composerId]);

  const loadTags = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags/${composerId}`);
      const data = await response.json();
      setTags(data.tags || []);
    } catch (error) {
      console.error('加载标签失败:', error);
    }
  };

  const addTag = async (tagName: string) => {
    if (!tagName.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ composer_id: composerId, tag_name: tagName.trim() }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: '标签已添加',
          description: `已添加标签：${tagName}`,
        });
        await loadTags();
        onUpdate?.();
      } else {
        toast({
          title: '添加失败',
          description: result.message || '标签可能已存在',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('添加标签失败:', error);
      toast({
        title: '添加失败',
        description: '请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
      setShowAddPanel(false);
      setCustomTag('');
    }
  };

  const removeTag = async (tagName: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ composer_id: composerId, tag_name: tagName }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: '标签已移除',
          description: `已移除标签：${tagName}`,
        });
        await loadTags();
        onUpdate?.();
      }
    } catch (error) {
      console.error('移除标签失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-1">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-accent/15 text-accent rounded text-xs"
          >
            <Tag className="w-3 h-3" />
            {tag.tag_name}
            <button
              onClick={() => removeTag(tag.tag_name)}
              className="hover:bg-accent/25 rounded p-0.5 transition-colors"
              disabled={loading}
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}

        <button
          onClick={() => setShowAddPanel(!showAddPanel)}
          className="inline-flex items-center gap-1 px-2 py-0.5 border border-dashed border-border-strong rounded text-xs text-ink-muted hover:border-accent-cyan hover:text-accent-cyan transition-colors"
          disabled={loading}
        >
          <Plus className="w-3 h-3" />
          添加标签
        </button>
      </div>

      {showAddPanel && (
        <div className="absolute top-full left-0 mt-1 p-3 bg-surface-1 border border-border rounded-lg shadow-lg z-50 w-64">
          <div className="text-xs text-ink-muted mb-2">选择预设标签或输入自定义标签</div>

          <div className="flex flex-wrap gap-1 mb-3">
            {PRESET_TAGS.map((presetTag) => (
              <button
                key={presetTag}
                onClick={() => addTag(presetTag)}
                className="px-2 py-1 bg-surface-2 hover:bg-accent/15 rounded text-xs text-ink transition-colors"
                disabled={loading || tags.some(t => t.tag_name === presetTag)}
              >
                {presetTag}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={customTag}
              onChange={(e) => setCustomTag(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addTag(customTag)}
              placeholder="自定义标签..."
              className="flex-1 px-2 py-1 border border-border rounded text-xs bg-transparent text-ink"
              autoFocus
            />
            <button
              onClick={() => addTag(customTag)}
              className="px-3 py-1 bg-accent text-ink-inverse rounded text-xs hover:bg-accent-hover transition-colors"
              disabled={!customTag.trim() || loading}
            >
              添加
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
