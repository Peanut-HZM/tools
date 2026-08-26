/**
 * 课程详情页面
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, AlertCircle, GraduationCap, Star, User, Eye, Book, MessagesSquare, Inbox } from 'lucide-react';
import { getCourseDetail, getCourseReviews, submitReview } from '../services/coursePlatform';
import type { CourseDetail, Review } from '../services/coursePlatform';

const CourseDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [activeTab, setActiveTab] = useState<'chapters'>('chapters');
  const [reviews, setReviews] = useState<Review[]>([]);
  const [newReview, setNewReview] = useState({ rating: 5, comment: '' });

  useEffect(() => {
    loadCourseDetail();
  }, [slug]);

  const loadCourseDetail = async () => {
    if (!slug) return;
    setLoading(true);
    try {
      const data = await getCourseDetail(slug);
      setCourse(data);
    } catch (error) {
      console.error('加载课程详情失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitReview = async () => {
    if (!course) return;
    try {
      const review = await submitReview(course.id, newReview.rating, newReview.comment);
      setReviews([review, ...reviews]);
      setNewReview({ rating: 5, comment: '' });
      alert('评价提交成功！');
    } catch (error) {
      console.error('提交评价失败:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent mb-4 mx-auto" />
          <p className="text-ink-muted">加载中...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-danger mb-4 mx-auto" />
          <p className="text-ink text-xl">课程不存在</p>
          <button
            onClick={() => navigate('/courses')}
            className="mt-4 px-6 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors"
          >
            返回课程列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas">
      {/* 课程封面 */}
      <div className="relative h-64 md:h-80 overflow-hidden">
        {course.cover_image ? (
          <img src={course.cover_image} alt={course.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-accent/20 to-accent-hover/20 flex items-center justify-center">
            <GraduationCap className="w-20 h-20 text-accent/50" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-canvas to-transparent"></div>
      </div>

      {/* 课程信息 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-32 relative z-10 pb-12">
        {/* 课程基本信息卡片 */}
        <div className="bg-surface-1/50 backdrop-blur-sm rounded-2xl border border-border/50 p-6 mb-6">
          <h1 className="text-3xl font-bold text-ink mb-4">{course.title}</h1>

          {/* 统计数据 */}
          <div className="flex items-center space-x-6 mb-6">
            <div className="flex items-center">
              <Star className="w-4 h-4 text-accent-warning mr-2" />
              <span className="text-ink font-semibold">
                {course.statistics?.avg_rating.toFixed(1) || '0.0'}
              </span>
              <span className="text-ink-muted text-sm ml-1">
                ({course.statistics?.review_count || 0}评价)
              </span>
            </div>
            <div className="flex items-center">
              <User className="w-4 h-4 text-accent mr-2" />
              <span className="text-ink">
                {course.statistics?.enroll_count || 0}
              </span>
              <span className="text-ink-muted text-sm ml-1">人在学</span>
            </div>
            <div className="flex items-center">
              <Eye className="w-4 h-4 text-ink-muted mr-2" />
              <span className="text-ink">
                {course.statistics?.view_count || 0}
              </span>
              <span className="text-ink-muted text-sm ml-1">次浏览</span>
            </div>
          </div>

          {/* 分类标签 */}
          {course.category && (
            <span className="inline-block px-4 py-2 bg-accent/10 text-accent rounded-full text-sm font-medium mb-4">
              {course.category.name}
            </span>
          )}

          {/* 课程描述 */}
          <div className="prose prose-invert max-w-none">
            <p className="text-ink-muted">{course.description}</p>
          </div>
        </div>

        {/* Tab 导航 */}
        <div className="bg-surface-1/50 backdrop-blur-sm rounded-2xl border border-border/50 overflow-hidden mb-6">
          <div className="flex border-b border-border/50">
            <button
              onClick={() => setActiveTab('chapters')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'chapters'
                  ? 'bg-accent/10 text-accent border-b-2 border-accent'
                  : 'text-ink-muted hover:text-ink hover:bg-surface-2/30'
              }`}
            >
              <Book className="w-4 h-4 mr-2" />
              课程章节
              <span className="ml-2 px-2 py-0.5 bg-surface-2 rounded-full text-xs">
                {course.chapters?.length || 0}
              </span>
            </button>
          </div>

          {/* Tab 内容 */}
          <div className="p-6">
            {activeTab === 'chapters' && (
              <div className="space-y-4">
                {course.chapters?.map((chapter, index) => (
                  <div
                    key={chapter.id}
                    className="flex items-center justify-between p-4 bg-surface-2/30 rounded-xl border border-border/30 hover:border-accent/30 transition-colors"
                  >
                    <div className="flex items-center">
                      <span className="w-8 h-8 bg-accent/20 text-accent rounded-full flex items-center justify-center font-semibold text-sm mr-4">
                        {index + 1}
                      </span>
                      <div>
                        <h4 className="text-ink font-medium">{chapter.title}</h4>
                        <p className="text-ink-muted text-sm">
                          {chapter.duration_minutes} 分钟 · {chapter.chapter_type}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate(`/courses/${slug}/learn?chapterId=${chapter.id}`)}
                      className="px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg text-sm transition-colors"
                    >
                      开始学习
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 学员评价 - 底部区域 */}
        <div className="bg-surface-1/50 backdrop-blur-sm rounded-2xl border border-border/50 p-6">
          <h3 className="text-xl font-semibold text-ink mb-6 flex items-center">
            <MessagesSquare className="w-4 h-4 text-accent mr-3" />
            学员评价
            <span className="ml-3 px-3 py-1 bg-surface-2 rounded-full text-sm text-ink-muted">
              {course.statistics?.review_count || 0}
            </span>
          </h3>

          {/* 提交评价 */}
          <div className="bg-surface-2/30 rounded-xl p-4 mb-6">
            <h4 className="text-ink font-medium mb-3">提交评价</h4>
            <div className="flex items-center space-x-2 mb-3">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setNewReview({ ...newReview, rating: star })}
                  className={`text-2xl ${star <= newReview.rating ? 'text-accent-warning' : 'text-ink-faint'}`}
                >
                  <Star className="w-6 h-6" />
                </button>
              ))}
            </div>
            <textarea
              value={newReview.comment}
              onChange={(e) => setNewReview({ ...newReview, comment: e.target.value })}
              placeholder="分享你的学习体验..."
              className="w-full px-4 py-3 bg-surface-1 border border-border rounded-lg text-ink placeholder-ink-muted focus:outline-none focus:border-accent"
              rows={3}
            />
            <button
              onClick={handleSubmitReview}
              className="mt-3 px-6 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors"
            >
              提交评价
            </button>
          </div>

          {/* 评价列表 */}
          {reviews.length > 0 ? (
            <div className="space-y-4">
              {reviews.map((review) => (
                <div key={review.id} className="bg-surface-2/20 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-gradient-to-br from-accent to-accent-hover rounded-full flex items-center justify-center text-ink-inverse font-semibold">
                        {review.user_id[0]?.toUpperCase()}
                      </div>
                      <div className="ml-3">
                        <p className="text-ink font-medium">学员{review.user_id.slice(-4)}</p>
                        <div className="flex items-center">
                          {[...Array(5)].map((_, i) => (
                            <Star
                              key={i}
                              className={`w-4 h-4 ${i < review.rating ? 'text-accent-warning' : 'text-ink-faint'}`}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                    <span className="text-ink-faint text-sm">
                      {new Date(review.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {review.comment && (
                    <p className="text-ink-muted">{review.comment}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-ink-muted">
              <Inbox className="w-8 h-8 mb-3 mx-auto" />
              <p>暂无评价，快来发表第一条评论吧！</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CourseDetailPage;
