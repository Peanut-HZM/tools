/**
 * 课程列表页面
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, Search, Inbox, ChevronLeft, ChevronRight } from 'lucide-react';
import CourseCard from '../components/Courses/CourseCard';
import FilterSidebar from '../components/Courses/FilterSidebar';
import { getCourseList, getCourseCategories, type Course } from '../services/coursePlatform';

const CoursesPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [courses, setCourses] = useState<Course[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(12);

  // 筛选状态
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedSort, setSelectedSort] = useState('latest');
  const [searchKeyword, setSearchKeyword] = useState('');

  // 加载课程列表
  const loadCourses = async () => {
    setLoading(true);
    try {
      const data = await getCourseList({
        category: selectedCategory || undefined,
        sort: selectedSort,
        page,
        limit,
      });
      setCourses(data.courses);
      setTotal(data.total);
    } catch (error) {
      console.error('加载课程列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCourses();
  }, [selectedCategory, selectedSort, page]);

  // 处理课程点击
  const handleCourseClick = (course: { id: number; slug: string }) => {
    navigate(`/courses/${course.slug}`);
  };

  // 重置筛选
  const handleReset = () => {
    setSelectedCategory('');
    setSelectedSort('latest');
    setSearchKeyword('');
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-canvas">
      {/* 顶部 Header */}
      <div className="bg-surface-1/50 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-ink-inverse mb-2">
                <GraduationCap className="w-8 h-8 text-accent mr-3 inline" />
                课程中心
              </h1>
              <p className="text-ink-muted">
                探索优质课程，提升专业技能
              </p>
            </div>

            {/* 搜索框 */}
            <div className="relative">
              <input
                type="text"
                placeholder="搜索课程..."
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && loadCourses()}
                className="w-80 px-5 py-3 pl-12 bg-surface-2/50 border border-border rounded-xl text-ink-inverse placeholder-slate-400 focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
              <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-ink-muted" />
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-6">
          {/* 侧边栏筛选 */}
          <FilterSidebar
            selectedCategory={selectedCategory}
            selectedSort={selectedSort}
            onCategoryChange={setSelectedCategory}
            onSortChange={setSelectedSort}
            onReset={handleReset}
          />

          {/* 课程列表 */}
          <div className="flex-1">
            {/* 结果统计 */}
            <div className="mb-6 flex items-center justify-between">
              <p className="text-ink-muted">
                找到 <span className="text-accent font-semibold">{total}</span> 门课程
              </p>
            </div>

            {/* 加载中 */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[...Array(6)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-surface-1/50 rounded-2xl overflow-hidden border border-border/50 animate-pulse"
                  >
                    <div className="aspect-video bg-surface-2/50"></div>
                    <div className="p-5 space-y-3">
                      <div className="h-6 bg-surface-2/50 rounded"></div>
                      <div className="h-4 bg-surface-2/50 rounded w-3/4"></div>
                      <div className="h-4 bg-surface-2/50 rounded w-1/2"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : courses.length === 0 ? (
              /* 空状态 */
              <div className="text-center py-20">
                <Inbox className="w-12 h-12 text-ink-faint mb-4 mx-auto" />
                <p className="text-ink-muted text-lg">暂无课程</p>
                <button
                  onClick={handleReset}
                  className="mt-4 px-6 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
                >
                  重置筛选
                </button>
              </div>
            ) : (
              /* 课程网格 */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {courses.map((course) => (
                  <CourseCard
                    key={course.id}
                    id={course.id}
                    slug={course.slug}
                    title={course.title}
                    description={course.description}
                    cover_image={course.cover_image}
                    category={course.category}
                    statistics={course.statistics}
                    onClick={handleCourseClick}
                  />
                ))}
              </div>
            )}

            {/* 分页 */}
            {!loading && courses.length > 0 && (
              <div className="mt-8 flex items-center justify-center space-x-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-surface-1 border border-border rounded-lg text-ink-muted disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface-2 hover:text-ink-inverse transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-4 py-2 bg-accent text-white rounded-lg font-medium">
                  {page}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * limit >= total}
                  className="px-4 py-2 bg-surface-1 border border-border rounded-lg text-ink-muted disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface-2 hover:text-ink-inverse transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoursesPage;
