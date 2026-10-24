import { Category, Tool } from '../../types';
import CategoryTabs from './CategoryTabs';
import ToolGrid from './ToolGrid';
import DeployTimeIndicator from './DeployTimeIndicator';
import { useI18n } from '../../i18n';
import { OPEN_COMMAND_PALETTE_EVENT } from '../../lib/navigation';
import { Boxes, Code2, Database, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import HomeToolSidebar from './HomeToolSidebar';

interface HeroProps {
  activeCategory: Category;
  onCategoryChange: (category: Category) => void;
  tools: Tool[];
  navigationTools: Tool[];
  onToolClick?: (toolId: string) => void;
  categories: Category[];
}

export default function Hero({ activeCategory, onCategoryChange, tools, navigationTools, onToolClick, categories }: HeroProps) {
  const { t } = useI18n();

  return (
    <section className="flex min-h-0 flex-1">
      <HomeToolSidebar tools={navigationTools} onToolClick={onToolClick} />

      <div className="min-w-0 flex-1 px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-[1520px]">
          <div className="relative min-h-[176px] overflow-hidden rounded-xl border border-indigo-100 bg-gradient-to-r from-[#eef6ff] via-[#f5f8ff] to-[#f2ecff] px-4 sm:px-8 py-4 sm:py-6 dark:border-indigo-400/15 dark:from-[#17233b] dark:via-[#18213a] dark:to-[#251c45]">
            <div className="relative z-10 max-w-xl">
              <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-blue-600/10 px-2.5 py-1 text-[11px] font-medium text-blue-600 dark:text-blue-300">
                <Sparkles className="h-3 w-3" />
                {t.home.heroBadge}
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
                {t.home.heroTitle}{t.home.heroTitleAccent}
              </h1>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-300">{t.home.heroSubtitle}</p>
              <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500 dark:text-slate-300">
                <span className="inline-flex items-center gap-1.5"><Zap className="h-3.5 w-3.5 text-blue-500" />{t.home.instantAccess}</span>
                <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-indigo-500" />{t.home.permissionIsolation}</span>
                <button
                  onClick={() => window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT))}
                  className="inline-flex items-center gap-1.5 font-medium text-blue-600 hover:text-blue-700 dark:text-blue-300"
                >
                  <SearchShortcutIcon />
                  {t.home.heroCta}
                </button>
              </div>
            </div>

            <div aria-hidden="true" className="absolute inset-y-0 right-0 hidden w-[42%] items-center justify-center md:flex">
              <div className="absolute h-32 w-64 rounded-full bg-blue-400/20 blur-3xl" />
              <div className="relative h-28 w-40">
                <div className="absolute bottom-0 left-3 h-8 w-32 rotate-[-4deg] rounded-xl border border-white/70 bg-white/55 shadow-lg dark:border-white/10 dark:bg-white/10" />
                <div className="absolute bottom-5 left-8 h-12 w-28 rotate-[3deg] rounded-xl border border-white/80 bg-white/70 shadow-lg dark:border-white/10 dark:bg-white/10" />
                <div className="absolute bottom-10 left-[58px] grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 text-white shadow-xl shadow-blue-500/25">
                  <Boxes className="h-8 w-8" />
                </div>
                <div className="absolute -left-4 top-1 grid h-10 w-10 -rotate-6 place-items-center rounded-xl bg-white text-blue-600 shadow-md dark:bg-slate-800 dark:text-blue-300"><Database className="h-5 w-5" /></div>
                <div className="absolute -right-3 top-0 grid h-10 w-10 rotate-6 place-items-center rounded-xl bg-white text-violet-600 shadow-md dark:bg-slate-800 dark:text-violet-300"><Code2 className="h-5 w-5" /></div>
              </div>
            </div>
          </div>

          <div className="mt-3 flex min-w-0 items-center gap-3 overflow-hidden rounded-xl border border-border bg-surface-1 px-2 py-1.5">
            <CategoryTabs
              categories={categories}
              activeCategory={activeCategory}
              onCategoryChange={onCategoryChange}
            />
            <DeployTimeIndicator />
          </div>

          <div className="mt-3">
            <ToolGrid tools={tools} onToolClick={onToolClick} />
          </div>
        </div>
      </div>
    </section>
  );
}

function SearchShortcutIcon() {
  return <span className="grid h-4 min-w-4 place-items-center rounded border border-current px-0.5 text-[9px]">⌘K</span>;
}
