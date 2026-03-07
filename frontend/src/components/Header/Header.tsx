import { Link } from 'react-router-dom';
import Navigation from './Navigation';
import SearchBar from './SearchBar';
import LoginButton from './LoginButton';
import { useI18n } from '../../i18n';

interface HeaderProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
}

export default function Header({ searchValue, onSearchChange, onSearch }: HeaderProps) {
  const { t, language, toggleLanguage } = useI18n();

  return (
    <header className="sticky top-0 z-50 bg-slate-800 border-b border-slate-700">
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-10">
          <Link to="/" className="text-2xl font-['Pacifico'] text-primary" key={language}>
            {t.common.logo}
          </Link>
          <Navigation />
        </div>
        <div className="flex items-center space-x-4">
          <SearchBar 
            value={searchValue}
            onChange={onSearchChange}
            onSearch={onSearch}
          />
          <button
            onClick={toggleLanguage}
            className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium transition-colors border border-slate-600 cursor-pointer"
            title={language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
          >
            {language === 'zh-CN' ? 'EN' : '中'}
          </button>
          <LoginButton />
        </div>
      </div>
    </header>
  );
}
