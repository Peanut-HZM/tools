import { CategoryTabsProps } from '../../types';
import { Button } from "@/components/ui/Button";

export default function CategoryTabs({ categories, activeCategory, onCategoryChange }: CategoryTabsProps) {

  // 当只有一个分类（"全部工具"）时，不显示分类筛选区域
  if (categories.length <= 1) {
    return null;
  }

  return (
    <div className="flex flex-wrap justify-center gap-3 mb-12">
      {categories.map((category) => (
        <Button
          key={category}
          onClick={() => onCategoryChange(category)}
          variant="outline"
          className={`category-tab ${activeCategory === category ? 'active' : ''}`}
        >
          {category}
        </Button>
      ))}
    </div>
  );
}
