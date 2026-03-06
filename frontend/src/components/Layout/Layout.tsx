import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import Header from '../Header/Header';
import Footer from '../Footer/Footer';
import { useSearch } from '../../hooks/useSearch';

export default function Layout() {
  const { searchValue, debouncedValue, handleSearchChange, handleSearch } = useSearch();
  const navigate = useNavigate();
  const location = useLocation();
  const isToolPage = location.pathname.startsWith('/tools/');

  const onSearch = () => {
    handleSearch();
    if (location.pathname !== '/' && searchValue.trim()) {
      navigate(`/?q=${encodeURIComponent(searchValue)}`);
    }
  };

  // If user types in search bar while on another page, we might want to navigate to home immediately?
  // Or just wait for Enter? 
  // Current behavior in HomePage is live filtering (debounced).
  // If we want consistent behavior, maybe navigating to home on debounce is too aggressive.
  // Let's stick to explicit search (Enter) or just typing updates the state, 
  // but it won't affect the tool page.
  
  return (
    <div className="bg-slate-900 text-slate-100 min-h-screen flex flex-col">
      <Header
        searchValue={searchValue}
        onSearchChange={handleSearchChange}
        onSearch={onSearch}
      />
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <Outlet context={{ searchValue, debouncedValue, handleSearchChange, handleSearch }} />
      </main>
      {!isToolPage && <Footer />}
    </div>
  );
}
