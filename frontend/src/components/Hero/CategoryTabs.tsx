import { CategoryTabsProps } from '../../types';
import { cn } from '@/lib/cn';

export default function CategoryTabs({ categories, activeCategory, onCategoryChange }: CategoryTabsProps) {

  // 当只有一个分类（"全部工具"）时，不显示分类筛选区域
  if (categories.length <= 1) {
    return null;
  }

  return (
    <div className="inline-flex max-w-full flex-nowrap gap-1 overflow-x-auto">
      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onCategoryChange(category)}
          className={cn(
            'min-h-8 whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-canvas',
            activeCategory === category
              ? 'bg-[image:var(--gradient-brand)] text-white shadow-sm'
              : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
          )}
        >
          {category}
        </button>
      ))}
    </div>
  );
}
