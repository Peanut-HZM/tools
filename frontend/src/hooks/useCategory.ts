import { useState } from 'react';
import { Category } from '../types';

export function useCategory(initialCategory: Category = "全部工具") {
  const [activeCategory, setActiveCategory] = useState<Category>(initialCategory);

  const handleCategoryChange = (category: Category) => {
    setActiveCategory(category);
  };

  return {
    activeCategory,
    handleCategoryChange
  };
}
