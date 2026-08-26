/**
 * 标签筛选组件
 * 用于按标签筛选会话
 */
import { useState, useEffect } from 'react';
import { Tag, Filter } from 'lucide-react';
import { API_BASE_URL } from '../../../config/api';

interface TagFilterProps {
  onTagSelect?: (tag: string | null) => void;
}

export default function TagFilter({ onTagSelect }: TagFilterProps) {
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTags();
  }, []);

  const loadTags = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags`);
      const data = await response.json();
      setTags(data.tags || []);
    } catch (error) {
      console.error('加载标签失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTagClick = (tag: string | null) => {
    setSelectedTag(tag);
    onTagSelect?.(tag);
  };

  if (tags.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="flex items-center gap-1 text-xs text-ink-muted">
        <Filter className="w-3 h-3" />
        标签筛选:
      </div>

      <button
        onClick={() => handleTagClick(null)}
        className={`px-2 py-1 rounded text-xs transition-colors ${
          !selectedTag
            ? 'bg-accent text-ink-inverse'
            : 'bg-surface-2 hover:bg-surface-3 text-ink-inverse'
        }`}
      >
        全部
      </button>

      {tags.map((tag) => (
        <button
          key={tag}
          onClick={() => handleTagClick(tag)}
          className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
            selectedTag === tag
              ? 'bg-accent text-ink-inverse'
              : 'bg-surface-2 hover:bg-surface-3 text-ink-inverse'
          }`}
        >
          <Tag className="w-3 h-3" />
          {tag}
        </button>
      ))}
    </div>
  );
}
