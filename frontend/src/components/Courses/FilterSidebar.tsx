/**
 * 课程筛选侧边栏组件
 */
import React, { useState } from 'react';

interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

interface FilterSidebarProps {
  categories?: FilterOption[];
  sorts?: FilterOption[];
  selectedCategory?: string;
  selectedSort?: string;
  onCategoryChange?: (category: string) => void;
  onSortChange?: (sort: string) => void;
  onReset?: () => void;
}

const FilterSidebar: React.FC<FilterSidebarProps> = ({
  categories = [
    { value: '', label: '全部分类', count: 0 },
    { value: 'programming', label: '编程开发', count: 12 },
    { value: 'design', label: '产品设计', count: 8 },
    { value: 'ai', label: '人工智能', count: 15 },
    { value: 'data', label: '数据分析', count: 6 },
  ],
  sorts = [
    { value: 'latest', label: '最新发布' },
    { value: 'hot', label: '最热门' },
    { value: 'rating', label: '评分最高' },
  ],
  selectedCategory = '',
  selectedSort = 'latest',
  onCategoryChange,
  onSortChange,
  onReset,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* 移动端切换按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="lg:hidden mb-4 w-full px-4 py-3 bg-surface-1/50 border border-border/50 rounded-xl text-ink-inverse font-medium flex items-center justify-between"
      >
        <span>
          <i className="fas fa-filter mr-2"></i>
          筛选
        </span>
        <i className={`fas fa-chevron-${isOpen ? 'up' : 'down'}`}></i>
      </button>

      {/* 侧边栏 */}
      <aside
        className={`lg:block ${isOpen ? 'block' : 'hidden'} w-full lg:w-64 space-y-6`}
      >
        {/* 分类筛选 */}
        <div className="bg-surface-1/30 rounded-xl p-5 border border-border/50">
          <h3 className="text-ink-inverse font-semibold mb-4 flex items-center">
            <i className="fas fa-layer-group text-accent mr-2"></i>
            课程分类
          </h3>
          <div className="space-y-2">
            {categories.map((category) => (
              <label
                key={category.value}
                className="flex items-center justify-between cursor-pointer group"
              >
                <div className="flex items-center">
                  <input
                    type="radio"
                    name="category"
                    value={category.value}
                    checked={selectedCategory === category.value}
                    onChange={(e) => onCategoryChange?.(e.target.value)}
                    className="w-4 h-4 bg-accent bg-surface-2 border-border focus:ring-accent focus:ring-2"
                  />
                  <span
                    className={`ml-3 text-sm ${
                      selectedCategory === category.value
                        ? 'text-accent font-medium'
                        : 'text-ink-muted group-hover:text-ink-inverse'
                    }`}
                  >
                    {category.label}
                  </span>
                </div>
                {category.count !== undefined && category.count > 0 && (
                  <span className="text-xs text-ink-faint bg-surface-2/50 px-2 py-1 rounded-full">
                    {category.count}
                  </span>
                )}
              </label>
            ))}
          </div>
        </div>

        {/* 排序筛选 */}
        <div className="bg-surface-1/30 rounded-xl p-5 border border-border/50">
          <h3 className="text-ink-inverse font-semibold mb-4 flex items-center">
            <i className="fas fa-sort text-accent mr-2"></i>
            排序方式
          </h3>
          <div className="space-y-2">
            {sorts.map((sort) => (
              <label
                key={sort.value}
                className="flex items-center cursor-pointer group"
              >
                <input
                  type="radio"
                  name="sort"
                  value={sort.value}
                  checked={selectedSort === sort.value}
                  onChange={(e) => onSortChange?.(e.target.value)}
                  className="w-4 h-4 bg-accent bg-surface-2 border-border focus:ring-accent focus:ring-2"
                />
                <span
                  className={`ml-3 text-sm ${
                    selectedSort === sort.value
                      ? 'text-accent font-medium'
                      : 'text-ink-muted group-hover:text-ink-inverse'
                  }`}
                >
                  {sort.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* 重置按钮 */}
        <button
          onClick={onReset}
          className="w-full px-4 py-3 bg-surface-2/50 hover:bg-surface-3/50 text-ink-muted hover:text-ink-inverse rounded-xl transition-all duration-200 font-medium"
        >
          <i className="fas fa-undo mr-2"></i>
          重置筛选
        </button>
      </aside>
    </>
  );
};

export default FilterSidebar;
