import { Category, Tool } from '../../types';
import CategoryTabs from './CategoryTabs';
import ToolGrid from './ToolGrid';

interface HeroProps {
  activeCategory: Category;
  onCategoryChange: (category: Category) => void;
  tools: Tool[];
  onToolClick?: (toolId: string) => void;
}

export default function Hero({ activeCategory, onCategoryChange, tools, onToolClick }: HeroProps) {
  const categories: Category[] = [
    "全部工具",
    "文本工具",
    "转换工具",
    "计算工具",
    "设计工具",
    "实用工具"
  ];

  return (
    <section className="mb-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">工具箱</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto">
          一站式实用工具集合，提升工作效率，简化日常任务。从文本处理到格式转换，从计算辅助到设计工具，应有尽有。
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
