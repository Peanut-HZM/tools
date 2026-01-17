import { useState, useEffect } from 'react';

export function useSearch() {
  const [searchValue, setSearchValue] = useState('');
  const [debouncedValue, setDebouncedValue] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(searchValue);
    }, 300);

    return () => {
      clearTimeout(timer);
    };
  }, [searchValue]);

  const handleSearchChange = (value: string) => {
    setSearchValue(value);
  };

  const handleSearch = () => {
    setDebouncedValue(searchValue);
  };

  return {
    searchValue,
    debouncedValue,
    handleSearchChange,
    handleSearch
  };
}
