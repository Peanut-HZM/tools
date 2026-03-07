/**
 * 我的课程页面
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CourseCard from '../components/Courses/CourseCard';
import { getMyCourses, type Course } from '../services/coursePlatform';

interface MyCourse {
  course: Course;
  enrollment: {
    id: number;
    status: string;
    progress_percent: number;
    enrolled_at: string;
  };
  completed_chapters: number;
  total_chapters: number;
}

const MyCoursesPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [courses, setCourses] = useState<MyCourse[]>([]);
  const [filter, setFilter] = useState<'all' | 'in-progress' | 'completed'>('all');

  useEffect(() => {
    loadMyCourses();
  }, []);

  const loadMyCourses = async () => {
    setLoading(true);
    try {
      const data = await getMyCourses();
      setCourses(data.courses || []);
    } catch (error) {
      console.error('加载我的课程失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCourseClick = (course: { id: number; slug: string }) => {
    navigate(`/courses/${course.slug}`);
  };

  const handleContinueLearning = (course: { id: number; slug: string }) => {
    navigate(`/courses/${course.slug}/learn`);
  };

  // 筛选课程
  const filteredCourses = courses.filter((item) => {
    if (filter === 'all') return true;
    if (filter === 'in-progress') return item.enrollment.status === 'active';
    if (filter === 'completed') return item.enrollment.status === 'completed';
    return true;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* 顶部 Header */}
      <div className="bg-slate-800/50 border-b border-slate-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            <i className="fas fa-book-reader text-cyan-400 mr-3"></i>
            我的课程
          </h1>
          <p className="text-slate-400">
            继续学习，不断进步
          </p>
        </div>
      </div>

      {/* 主要内容 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 筛选 Tabs */}
        <div className="flex items-center space-x-2 mb-6">
          <button
            onClick={() => setFilter('all')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              filter === 'all'
                ? 'bg-cyan-500 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            全部 ({courses.length})
          </button>
          <button
            onClick={() => setFilter('in-progress')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              filter === 'in-progress'
                ? 'bg-cyan-500 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            学习中
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              filter === 'completed'
                ? 'bg-cyan-500 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            已完成
          </button>
        </div>

        {/* 加载中 */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="bg-slate-800/50 rounded-2xl overflow-hidden border border-slate-700/50 animate-pulse"
              >
                <div className="aspect-video bg-slate-700/50"></div>
                <div className="p-5 space-y-3">
                  <div className="h-6 bg-slate-700/50 rounded"></div>
                  <div className="h-4 bg-slate-700/50 rounded w-3/4"></div>
                  <div className="h-4 bg-slate-700/50 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        ) : filteredCourses.length === 0 ? (
          /* 空状态 */
          <div className="text-center py-20">
            <i className="fas fa-inbox text-6xl text-slate-600 mb-4"></i>
            <p className="text-slate-400 text-lg">
              {filter === 'all' ? '还没有报名任何课程' : '没有符合条件的课程'}
            </p>
            {filter === 'all' && (
              <button
                onClick={() => navigate('/courses')}
                className="mt-4 px-6 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors"
              >
                去浏览课程
              </button>
            )}
          </div>
        ) : (
          /* 课程网格 */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCourses.map((item) => (
              <div key={item.enrollment.id} className="relative">
                <CourseCard
                  id={item.course.id}
                  slug={item.course.slug}
                  title={item.course.title}
                  description={item.course.description}
                  cover_image={item.course.cover_image}
                  category={item.course.category}
                  statistics={item.course.statistics}
                  progress={{
                    completed_chapters: item.completed_chapters,
                    total_chapters: item.total_chapters,
                    percent: item.enrollment.progress_percent,
                  }}
                  onClick={handleCourseClick}
                />
                {/* 继续学习按钮 */}
                <button
                  onClick={() => handleContinueLearning(item.course)}
                  className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold rounded-xl opacity-0 group-hover:opacity-100 transition-all duration-300 shadow-lg"
                >
                  <i className="fas fa-play mr-2"></i>
                  继续学习
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyCoursesPage;
