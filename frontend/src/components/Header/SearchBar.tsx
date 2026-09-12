import { Search } from 'lucide-react';
import { SearchBarProps } from '../../types';

export default function SearchBar({ value, onChange, onSearch }: SearchBarProps) {
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  return (
    // 外层：响应式宽度（移动端撑满容器，桌面端固定 16rem）
    <div className="relative w-full md:w-64">
      {/* 内层：玻璃胶囊容器，聚焦时边框切换为品牌高亮色 */}
      <div className="bg-glass-bg border border-glass-border rounded-full focus-within:border-accent transition-colors">
        <input
          type="text"
          placeholder="搜索工具..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={handleKeyPress}
          className="search-input bg-transparent text-ink placeholder-ink-muted px-4 py-2 pl-10 rounded-full w-full"
        />
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-ink-muted w-4 h-4" />
      </div>
    </div>
  );
}
