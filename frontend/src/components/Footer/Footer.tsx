import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n';
import { NAV_ROUTES } from '../../lib/navigation';

export default function Footer() {
  const { t } = useI18n();

  return (
    <footer className="border-t border-glass-border bg-surface-1/50 backdrop-blur-md">
      <div className="container mx-auto px-6 py-10">
        {/* 三栏布局：移动端单列纵向堆叠（space-y-6），md 起三等分横排（md:gap-x-8 提供栏间距） */}
        <div className="grid grid-cols-1 space-y-6 md:grid-cols-3 md:space-y-0 md:gap-x-8">
          {/* 栏1：品牌区（渐变 Logo + 一句话简介） */}
          <div>
            {/* 品牌名取 hero.title（工具箱/Toolbox），中英文均适合作品牌文案 */}
            <div className="text-xl font-extrabold gradient-text">{t.hero.title}</div>
            <p className="mt-2 text-sm text-ink-muted">{t.footer.desc}</p>
          </div>

          {/* 栏2：页面导航（路由单一来源 lib/navigation.ts 的 NAV_ROUTES，match 字段此处不使用） */}
          <nav>
            <ul className="space-y-2">
              {NAV_ROUTES.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className="text-sm text-ink-muted transition-colors hover:text-ink"
                  >
                    {t.nav[item.key]}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* 栏3：说明区（版权 + 产品说明） */}
          <div className="text-sm text-ink-muted">
            <p>{t.footer.copyright}</p>
            <p className="mt-2">{t.footer.tagline}</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
