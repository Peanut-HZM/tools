import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n';
import { useAuth } from '../../stores/authStore';

export default function Navigation() {
  const { t } = useI18n();
  const { user } = useAuth();
  
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
      
      {user?.role === 'admin' && (
        <Link
          to="/admin"
          className="text-cyan-400 hover:text-cyan-300 transition-colors font-semibold"
        >
          后台管理
        </Link>
      )}
    </nav>
  );
}
