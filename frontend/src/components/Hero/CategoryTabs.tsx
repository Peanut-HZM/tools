import { CategoryTabsProps } from '../../types';

export default function CategoryTabs({ categories, activeCategory, onCategoryChange }: CategoryTabsProps) {

  // 当只有一个分类（"全部工具"）时，不显示分类筛选区域
  if (categories.length <= 1) {
    return null;
  }

  return (
    <div className="flex flex-wrap justify-center gap-3 mb-12">
      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onCategoryChange(category)}
          className={`category-tab bg-surface-2 hover:bg-surface-3 text-ink-muted px-4 py-2 rounded-lg transition-colors border border-border ${
            activeCategory === category ? 'active' : ''
          }`}
        >
          {category}
        </button>
      ))}
    </div>
  );
}
