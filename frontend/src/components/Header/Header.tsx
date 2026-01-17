import Navigation from './Navigation';
import SearchBar from './SearchBar';
import LoginButton from './LoginButton';

interface HeaderProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
}

export default function Header({ searchValue, onSearchChange, onSearch }: HeaderProps) {
  return (
    <header className="bg-slate-800 border-b border-slate-700">
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-10">
          <div className="text-2xl font-['Pacifico'] text-primary">logo</div>
          <Navigation />
        </div>
        <div className="flex items-center space-x-4">
          <SearchBar 
            value={searchValue}
            onChange={onSearchChange}
            onSearch={onSearch}
          />
          <LoginButton />
        </div>
      </div>
    </header>
  );
}
