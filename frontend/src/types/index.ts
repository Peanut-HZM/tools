export type Category = 
  | "全部工具"
  | "文本工具"
  | "转换工具"
  | "计算工具"
  | "设计工具"
  | "实用工具";

export interface Tool {
  id: string;
  icon: string;
  iconColor: string;
  title: string;
  description: string;
  rating: number;
  usageCount: string;
  category: string;
}

export interface ToolCardProps {
  id: string;
  icon: string;
  iconColor: string;
  title: string;
  description: string;
  rating: number;
  usageCount: string;
  onClick: () => void;
}

export interface CategoryTabsProps {
  categories: Category[];
  activeCategory: Category;
  onCategoryChange: (category: Category) => void;
}

export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
}

export interface Feature {
  icon: string;
  iconColor: string;
  title: string;
  description: string;
}

export interface Statistic {
  value: string;
  label: string;
}

export interface Recommendation {
  icon: string;
  iconColor: string;
  title: string;
  description: string;
  action: string;
}
