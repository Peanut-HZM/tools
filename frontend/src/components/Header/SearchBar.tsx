import { Search } from 'lucide-react';
import { SearchBarProps } from '../../types';

export default function SearchBar({ value, onChange, onSearch }: SearchBarProps) {
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  return (
    <div className="relative w-full md:w-72">
      <div className="rounded-lg border border-border bg-canvas transition-colors focus-within:border-accent">
        <input
          type="text"
          placeholder="搜索工具..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyPress}
          className="search-input h-8 w-full rounded-lg bg-transparent py-1.5 pl-9 pr-3 text-xs text-ink placeholder:text-ink-faint"
        />
        <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" />
      </div>
    </div>
  );
}
