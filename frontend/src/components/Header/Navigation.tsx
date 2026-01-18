import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n';

export default function Navigation() {
  const { t } = useI18n();
  
  const navLinks = [
    { label: t.nav.home, href: '/' },
    { label: t.nav.tools, href: '/' },
    { label: t.nav.about, href: '#' },
    { label: t.nav.help, href: '#' },
    { label: t.nav.feedback, href: '#' }
  ];

  return (
    <nav className="hidden md:flex space-x-8">
      {navLinks.map((link) => (
        link.href.startsWith('/') ? (
          <Link
            key={link.label}
            to={link.href}
            className="text-slate-300 hover:text-white transition-colors"
          >
            {link.label}
          </Link>
        ) : (
          <a
            key={link.label}
            href={link.href}
            className="text-slate-300 hover:text-white transition-colors"
          >
            {link.label}
          </a>
        )
      ))}
    </nav>
  );
}
