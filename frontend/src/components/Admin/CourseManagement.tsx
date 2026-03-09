/**
 * 课程管理主页面 - 课程列表（卡片展示、搜索、分页）
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCourseAdminStore } from '../../stores/courseAdminStore';
import CourseEditor from './CourseManagement/CourseEditor';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../MarkdownEditor/Toast/Toast';

const CourseManagement: React.FC = () => {
  const navigate = useNavigate();
  const { toasts, addToast, removeToast, error, success } = useToast();
  const {
    fetchCourses,
    courses,
    total,
    page,
    limit,
    statusFilter,
    searchKeyword,
    loading,
    deleteCourse,
    setPage,
    setLimit,
    setStatusFilter,
    setSearchKeyword,
  } = useCourseAdminStore();

  const [showCourseEditor, setShowCourseEditor] = useState(false);
  const [editingCourseId, setEditingCourseId] = useState<number | null>(null);

  useEffect(() => {
    fetchCourses({
      status: statusFilter !== 'all' ? statusFilter : undefined,
      search: searchKeyword || undefined,
      page,
      limit,
    });
  }, [page, limit, statusFilter]);

  const handleCreateCourse = () => {
    setEditingCourseId(null);
    setShowCourseEditor(true);
  };

  const handleEditCourse = (courseId: number) => {
    setEditingCourseId(courseId);
    setShowCourseEditor(true);
  };

  const handleCloseCourseEditor = () => {
    setShowCourseEditor(false);
    setEditingCourseId(null);
  };

  // 搜索
  const handleSearch = () => {
    setPage(1);
    fetchCourses({
      status: statusFilter !== 'all' ? statusFilter : undefined,
      search: searchKeyword || undefined,
      page: 1,
      limit,
    });
  };

  // 删除课程
  const handleDeleteCourse = async (courseId: number) => {
    if (!window.confirm('确定要删除此课程吗？删除后将无法恢复（会级联删除所有章节、测验和资源）')) {
      return;
    }

    try {
      await deleteCourse(courseId);
      success('课程删除成功');
      // 重新获取课程列表
      fetchCourses({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        search: searchKeyword || undefined,
        page,
        limit,
      });
    } catch (err) {
      error('删除课程失败');
    }
  };

  // 进入课程详情页
  const handleViewCourseDetail = (courseId: number) => {
    navigate(`/admin/course/${courseId}`);
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="h-full flex flex-col">
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center">
            <i className="fas fa-graduation-cap text-cyan-400 mr-3"></i>
            课程管理
          </h1>
          <p className="text-slate-400 text-sm mt-1">管理课程内容和章节</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleCreateCourse}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white rounded-xl transition-all duration-200 font-medium shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 hover:-translate-y-0.5 flex items-center"
          >
            <i className="fas fa-plus mr-2"></i>
            新增课程
          </button>
        </div>
      </div>

      {/* 筛选和操作栏 */}
      <div className="bg-slate-800 rounded-lg p-4 mb-6 border border-slate-700">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* 状态筛选 */}
          <div className="flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 cursor-pointer"
            >
              <option value="all">全部</option>
              <option value="published">已发布</option>
              <option value="draft">草稿</option>
              <option value="archived">已归档</option>
            </select>

            {/* 关键词搜索 */}
            <div className="relative">
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                placeholder="搜索课程或章节内容..."
                className="px-4 py-2 pl-10 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 w-72"
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
            </div>
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors cursor-pointer text-sm"
            >
              <i className="fas fa-search mr-1"></i> 搜索
            </button>
          </div>

          {/* 每页数量 */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">每页:</span>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(1);
              }}
              className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 cursor-pointer"
            >
              <option value={9}>9</option>
              <option value={15}>15</option>
              <option value={30}>30</option>
            </select>
          </div>
        </div>
      </div>

      {/* Course List */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white mb-3">课程列表</h2>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500"></div>
          </div>
        ) : courses.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <i className="fas fa-inbox text-4xl mb-4"></i>
            <p>暂无课程</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {courses.map((course) => (
              <div
                key={course.id}
                className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 hover:border-cyan-500/50 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3
                      className="text-white font-semibold mb-2 group-hover:text-cyan-400 transition-colors cursor-pointer"
                      onClick={() => handleViewCourseDetail(course.id)}
                    >
                      {course.title}
                    </h3>
                    <p className="text-slate-400 text-sm line-clamp-2 mb-3">
                      {course.description}
                    </p>
                  </div>
                  {course.cover_image && (
                    <img
                      src={course.cover_image}
                      alt={course.title}
                      className="w-16 h-16 object-cover rounded-lg ml-3"
                    />
                  )}
                </div>
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-1 rounded-full ${
                        course.status === 'published'
                          ? 'bg-green-500/20 text-green-400'
                          : course.status === 'draft'
                          ? 'bg-slate-600/20 text-slate-400'
                          : 'bg-orange-500/20 text-orange-400'
                      }`}
                    >
                      {course.status === 'published' ? '已发布' : course.status === 'draft' ? '草稿' : '已归档'}
                    </span>
                    <span className="text-slate-500">
                      <i className="fas fa-users mr-1"></i>
                      {course.statistics?.enroll_count || 0} 人学习
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditCourse(course.id);
                      }}
                      className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                      title="编辑课程"
                    >
                      <i className="fas fa-edit text-slate-400 hover:text-cyan-400"></i>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewCourseDetail(course.id);
                      }}
                      className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                      title="管理章节"
                    >
                      <i className="fas fa-list text-slate-400 hover:text-blue-400"></i>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteCourse(course.id);
                      }}
                      className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                      title="删除课程"
                    >
                      <i className="fas fa-trash text-slate-400 hover:text-red-400"></i>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 mb-6">
          <p className="text-slate-400 text-sm">
            共 {total} 条，第 {page} 页 / 共 {totalPages} 页
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded cursor-pointer transition-colors disabled:cursor-not-allowed"
            >
              <i className="fas fa-chevron-left mr-1"></i>上一页
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded cursor-pointer transition-colors disabled:cursor-not-allowed"
            >
              下一页<i className="fas fa-chevron-right ml-1"></i>
            </button>
          </div>
        </div>
      )}

      {/* Course Editor Modal */}
      {showCourseEditor && (
        <CourseEditor
          courseId={editingCourseId || undefined}
          onClose={handleCloseCourseEditor}
        />
      )}
    </div>
  );
};

export default CourseManagement;
