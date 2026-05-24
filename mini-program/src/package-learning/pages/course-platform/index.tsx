import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Image } from '@tarojs/components';
import { coursePlatformApi } from '../../../services/coursePlatform';
import type { Course, CourseCategory } from '../../../services/coursePlatform';
import { formatApiError } from '../../../utils/mobileTool';
import Loading from '../../../components/Loading';
import SearchBar from '../../../components/SearchBar';
import './index.scss';

type PageState = 'loading' | 'error' | 'success';

export default function CoursePlatformPage() {
  const [pageState, setPageState] = useState<PageState>('loading');
  const [courses, setCourses] = useState<Course[]>([]);
  const [categories, setCategories] = useState<CourseCategory[]>([]);
  const [activeCategory, setActiveCategory] = useState('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchCourses = async (reset = false) => {
    const currentPage = reset ? 1 : page;
    try {
      const res = await coursePlatformApi.getCourses({
        category: activeCategory || undefined,
        search: searchKeyword || undefined,
        page: currentPage,
        limit: 12,
      });
      if (reset) {
        setCourses(res.courses);
        setPage(2);
      } else {
        setCourses(prev => [...prev, ...res.courses]);
        setPage(currentPage + 1);
      }
      setHasMore(res.courses.length === 12);
      setPageState('success');
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  useEffect(() => {
    setPageState('loading');
    Promise.all([
      coursePlatformApi.getCategories().then(r => setCategories(r.categories)),
      fetchCourses(true),
    ]).catch(() => {
      setPageState('error');
    });
  }, []);

  useEffect(() => {
    fetchCourses(true);
  }, [activeCategory, searchKeyword]);

  const handleCourseClick = (slug: string) => {
    Taro.navigateTo({ url: `/package-learning/pages/course-platform/detail/index?slug=${slug}` });
  };

  const handleLoadMore = () => {
    if (hasMore && pageState !== 'loading') {
      fetchCourses();
    }
  };

  return (
    <View className="course-platform-page">
      <SearchBar
        placeholder="搜索课程..."
        value={searchKeyword}
        onChange={setSearchKeyword}
        onSearch={() => fetchCourses(true)}
      />

      <ScrollView className="category-bar" scrollX>
        <View
          className={`category-item ${activeCategory === '' ? 'active' : ''}`}
          onClick={() => setActiveCategory('')}
        >
          <Text>全部</Text>
        </View>
        {categories.map(cat => (
          <View
            key={cat.id}
            className={`category-item ${activeCategory === cat.slug ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat.slug)}
          >
            <Text>{cat.name}</Text>
          </View>
        ))}
      </ScrollView>

      {pageState === 'loading' && <Loading text="加载中..." />}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Text className="retry-text" onClick={() => fetchCourses(true)}>点击重试</Text>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="course-list" scrollY onScrollToLower={handleLoadMore}>
          {courses.length === 0 ? (
            <View className="empty-state">
              <Text>暂无课程</Text>
            </View>
          ) : (
            courses.map(course => (
              <View key={course.id} className="course-card" onClick={() => handleCourseClick(course.slug)}>
                {course.cover_image && (
                  <Image className="cover" src={course.cover_image} mode="aspectFill" lazyLoad />
                )}
                <View className="info">
                  <Text className="title">{course.title}</Text>
                  <Text className="desc">{course.description}</Text>
                  {course.price > 0 && (
                    <Text className="price">¥{course.price}</Text>
                  )}
                </View>
              </View>
            ))
          )}
          {hasMore && <Text className="load-more">加载更多...</Text>}
        </ScrollView>
      )}
    </View>
  );
}
