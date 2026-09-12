import { CategoryTabsProps } from '../../types';
import { cn } from '@/lib/cn';

/**
 * 首页分类切换：玻璃胶囊容器 + 单个胶囊 Tab
 * - 容器：glass-card 玻璃质感圆角胶囊，小视口下横向滚动（不换行）
 * - 激活态：品牌渐变底 + 发光阴影；非激活态：弱化文字色，hover 增强
 */
export default function CategoryTabs({ categories, activeCategory, onCategoryChange }: CategoryTabsProps) {

  // 当只有一个分类（"全部工具"）时，不显示分类筛选区域
  if (categories.length <= 1) {
    return null;
  }

  return (
    <div className="glass-card rounded-full p-1 inline-flex overflow-x-auto flex-nowrap max-w-full">
      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onCategoryChange(category)}
          className={cn(
            // 公共胶囊样式：不换行 + 过渡动画
            'rounded-full px-4 py-1.5 text-sm whitespace-nowrap transition-all duration-200',
            activeCategory === category
              ? // 激活态：品牌渐变底 + 品牌色发光阴影
                'text-white bg-[image:var(--gradient-brand)] shadow-[0_4px_14px_rgba(120,90,250,0.35)]'
              : // 非激活态：弱化文字色，hover 增强
                'text-ink-muted hover:text-ink'
          )}
        >
          {category}
        </button>
      ))}
    </div>
  );
}
