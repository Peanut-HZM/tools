import { useState, useEffect } from 'react';
import Taro, { useRouter } from '@tarojs/taro';
import { View, Text, Image, ScrollView, Button } from '@tarojs/components';
import { coursePlatformApi } from '../../../../services/coursePlatform';
import type { CourseDetail, CourseChapter } from '../../../../services/coursePlatform';
import { formatApiError } from '../../../../utils/mobileTool';
import Markdown from '../../../../components/Markdown';
import Loading from '../../../../components/Loading';
import './index.scss';

/**
 * 玻璃光晕换肤（阶段⑧-⑨ Task 8）：
 * - 主按钮（立即报名）套 .btn-primary 品牌渐变（内部即 background-image: var(--gradient-brand)），
 *   按压反馈走 hover-class='btn-primary-hover'；
 * - 头部/章节列表/章节内容为全宽条形面板，走 surface-1 底 + 玻璃发丝线 token（不套 glass-card，保持通栏布局）；
 * - 章节选中态：序号徽标 accent-primary 实底 + 标题 accent 字色（原 #6366f1 语义对号）；
 * - 课程详情获取/报名逻辑不变。
 */

export default function CourseDetailPage() {
  const router = useRouter();
  const slug = router.params.slug || '';
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeChapter, setActiveChapter] = useState<CourseChapter | null>(null);

  useEffect(() => {
    if (!slug) {
      setError('课程 ID 缺失');
      setLoading(false);
      return;
    }
    coursePlatformApi.getCourseDetail(slug)
      .then(data => {
        setCourse(data);
        if (data.chapters?.length > 0) {
          setActiveChapter(data.chapters[0]);
        }
        setLoading(false);
      })
      .catch(err => {
        setError(formatApiError(err));
        setLoading(false);
      });
  }, [slug]);

  const handleEnroll = async () => {
    if (!course) return;
    try {
      Taro.showLoading({ title: '报名中...' });
      await coursePlatformApi.enroll(course.id);
      Taro.hideLoading();
      Taro.showToast({ title: '报名成功', icon: 'success' });
    } catch (err: any) {
      Taro.hideLoading();
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  if (loading) return <Loading text="加载课程..." />;
  if (error) return (
    <View className="error-state">
      <Text>{error}</Text>
    </View>
  );
  if (!course) return null;

  return (
    <View className="course-detail-page">
      {course.cover_image && (
        <Image className="cover" src={course.cover_image} mode="aspectFill" />
      )}
      <View className="header">
        <Text className="title">{course.title}</Text>
        <Text className="desc">{course.description}</Text>
        <Button className="enroll-btn btn-primary" hoverClass="btn-primary-hover" onClick={handleEnroll}>立即报名</Button>
      </View>

      <View className="chapter-list">
        <Text className="section-title">课程章节</Text>
        {course.chapters?.map((chapter, idx) => (
          <View
            key={chapter.id}
            className={`chapter-item ${activeChapter?.id === chapter.id ? 'active' : ''}`}
            onClick={() => setActiveChapter(chapter)}
          >
            <Text className="chapter-order">{idx + 1}</Text>
            <Text className="chapter-title">{chapter.title}</Text>
          </View>
        ))}
      </View>

      {activeChapter && (
        <ScrollView className="chapter-content" scrollY>
          <Text className="chapter-name">{activeChapter.title}</Text>
          {activeChapter.content ? (
            <Markdown content={activeChapter.content} />
          ) : (
            <Text className="no-content">本章暂无内容</Text>
          )}
        </ScrollView>
      )}
    </View>
  );
}
