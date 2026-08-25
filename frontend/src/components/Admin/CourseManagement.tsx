/**
 * 课程管理主页面 - 课程列表（卡片展示、搜索、分页）
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCourseAdminStore } from '../../stores/courseAdminStore';
import CourseEditor from './CourseManagement/CourseEditor';
import { useToast } from '../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
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
    <div className="h-full flex flex-col">      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-ink-inverse flex items-center">
            <i className="fas fa-graduation-cap text-accent mr-3"></i>
            课程管理
          </h1>
          <p className="text-ink-muted text-sm mt-1">管理课程内容和章节</p>
        </div>
        <div className="flex items-center space-x-3">
          <Button
            onClick={handleCreateCourse}
            className="px-6 py-3 bg-gradient-to-r from-accent-secondary to-accent-secondary-hover hover:from-accent-secondary-hover hover:to-accent-secondary-hover shadow-lg shadow-accent-secondary/20 hover:shadow-accent-secondary/30 hover:-translate-y-0.5"
          >
            <i className="fas fa-plus mr-2"></i>
            新增课程
          </Button>
        </div>
      </div>

      {/* 筛选和操作栏 */}
      <Card className="p-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* 状态筛选 */}
          <div className="flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink-inverse text-sm focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer"
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
                className="px-4 py-2 pl-10 bg-surface-2 border border-border rounded-lg text-ink-inverse text-sm focus:outline-none focus:ring-2 focus:ring-accent w-72"
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"></i>
            </div>
            <Button onClick={handleSearch} size="sm" className="cursor-pointer">
              <i className="fas fa-search mr-1"></i> 搜索
            </Button>
          </div>

          {/* 每页数量 */}
          <div className="flex items-center gap-2">
            <span className="text-ink-muted text-sm">每页:</span>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(1);
              }}
              className="px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink-inverse text-sm focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer"
            >
              <option value={9}>9</option>
              <option value={15}>15</option>
              <option value={30}>30</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Course List */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-ink-inverse mb-3">课程列表</h2>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent"></div>
          </div>
        ) : courses.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-ink-muted">
            <i className="fas fa-inbox text-4xl mb-4"></i>
            <p>暂无课程</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
            {courses.map((course) => (
              <div
                key={course.id}
                className="bg-surface-1/50 rounded-xl border border-border/50 p-4 hover:border-accent/50 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3
                      className="text-ink-inverse font-semibold mb-2 group-hover:text-accent transition-colors cursor-pointer"
                      onClick={() => handleViewCourseDetail(course.id)}
                    >
                      {course.title}
                    </h3>
                    <p className="text-ink-muted text-sm line-clamp-2 mb-3">
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
                          ? 'bg-surface-3/20 text-ink-muted'
                          : 'bg-orange-500/20 text-orange-400'
                      }`}
                    >
                      {course.status === 'published' ? '已发布' : course.status === 'draft' ? '草稿' : '已归档'}
                    </span>
                    <span className="text-ink-faint">
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
                      className="p-2 hover:bg-surface-2 rounded-lg transition-colors"
                      title="编辑课程"
                    >
                      <i className="fas fa-edit text-ink-muted hover:text-accent"></i>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewCourseDetail(course.id);
                      }}
                      className="p-2 hover:bg-surface-2 rounded-lg transition-colors"
                      title="管理章节"
                    >
                      <i className="fas fa-list text-ink-muted hover:text-accent-info"></i>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteCourse(course.id);
                      }}
                      className="p-2 hover:bg-surface-2 rounded-lg transition-colors"
                      title="删除课程"
                    >
                      <i className="fas fa-trash text-ink-muted hover:text-danger"></i>
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
          <p className="text-ink-muted text-sm">
            共 {total} 条，第 {page} 页 / 共 {totalPages} 页
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
            >
              <i className="fas fa-chevron-left mr-1"></i>上一页
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage(page + 1)}
              disabled={page === totalPages}
            >
              下一页<i className="fas fa-chevron-right ml-1"></i>
            </Button>
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
