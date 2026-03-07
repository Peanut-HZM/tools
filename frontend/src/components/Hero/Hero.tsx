import { Category, Tool } from '../../types';
import CategoryTabs from './CategoryTabs';
import ToolGrid from './ToolGrid';
import { useI18n } from '../../i18n';

interface HeroProps {
  activeCategory: Category;
  onCategoryChange: (category: Category) => void;
  tools: Tool[];
  onToolClick?: (toolId: string) => void;
  categories: Category[];
}

export default function Hero({ activeCategory, onCategoryChange, tools, onToolClick, categories }: HeroProps) {
  const { t } = useI18n();

  return (
    <section className="mb-16">
      <CategoryTabs
        categories={categories}
        activeCategory={activeCategory}
        onCategoryChange={onCategoryChange}
      />

      <ToolGrid tools={tools} onToolClick={onToolClick} />
    </section>
  );
}
