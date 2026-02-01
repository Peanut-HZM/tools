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
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">{t.hero.title}</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">
          {t.hero.subtitle}
        </p>
      </div>

      <CategoryTabs
        categories={categories}
        activeCategory={activeCategory}
        onCategoryChange={onCategoryChange}
      />

      <ToolGrid tools={tools} onToolClick={onToolClick} />
    </section>
  );
}
