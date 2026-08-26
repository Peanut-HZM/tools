import { Search } from 'lucide-react';
import { SearchBarProps } from '../../types';

export default function SearchBar({ value, onChange, onSearch }: SearchBarProps) {
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  return (
    <div className="relative">
      <input
        type="text"
        placeholder="搜索工具..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={handleKeyPress}
        className="search-input bg-surface-2 text-white px-4 py-2 pl-10 rounded-lg border border-border focus:border-primary w-64"
      />
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-ink-muted w-4 h-4" />
    </div>
  );
}
