import { Category, Tool } from '../../types';
import CategoryTabs from './CategoryTabs';
import ToolGrid from './ToolGrid';
import DeployTimeIndicator from './DeployTimeIndicator';
import { useI18n } from '../../i18n';
import { OPEN_COMMAND_PALETTE_EVENT } from '../../lib/navigation';

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
      {/* 大标题主视觉：徽标 + 渐变标题 + 副标题 + 搜索 CTA（点击打开 ⌘K 命令面板） */}
      <div className="text-center pt-10 pb-10">
        <span className="inline-block text-xs px-3 py-1 rounded-full mb-5 text-accent bg-glass-bg border border-glass-border">
          {t.home.heroBadge}
        </span>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-ink mb-4">
          {t.home.heroTitle}
          <span className="gradient-text">{t.home.heroTitleAccent}</span>
        </h1>
        <p className="text-ink-muted text-base mb-8">{t.home.heroSubtitle}</p>
        <div className="flex items-center justify-center gap-4">
          {/* CTA 复用全局命令面板：派发命令面板打开事件（事件名见 lib/navigation.ts 常量，CommandPalette 已监听） */}
          <button
            onClick={() => window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT))}
            className="btn-primary rounded-full px-6 h-11 text-sm font-medium inline-flex items-center gap-2"
          >
            {t.home.heroCta}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-center mb-8">
        <CategoryTabs
          categories={categories}
          activeCategory={activeCategory}
          onCategoryChange={onCategoryChange}
        />
        <DeployTimeIndicator />
      </div>

      <ToolGrid tools={tools} onToolClick={onToolClick} />
    </section>
  );
}
