import { useState, useEffect } from 'react';
import Taro, { useRouter } from '@tarojs/taro';
import { View, Text, Image, ScrollView, Button } from '@tarojs/components';
import { coursePlatformApi } from '../../../../services/coursePlatform';
import type { CourseDetail, CourseChapter } from '../../../../services/coursePlatform';
import { formatApiError } from '../../../../utils/mobileTool';
import Markdown from '../../../../components/Markdown';
import Loading from '../../../../components/Loading';
import './index.scss';

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
        <Button className="enroll-btn" onClick={handleEnroll}>立即报名</Button>
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
