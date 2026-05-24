import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Image } from '@tarojs/components';
import { techContentsApi } from '../../services/techContents';
import type { TechContent, ContentType } from '../../services/techContents';
import { formatApiError } from '../../utils/mobileTool';
import Loading from '../../components/Loading';
import './index.scss';

type PageState = 'loading' | 'error' | 'success';

export default function TechContentsPage() {
  const [pageState, setPageState] = useState<PageState>('loading');
  const [contents, setContents] = useState<TechContent[]>([]);
  const [types, setTypes] = useState<ContentType[]>([]);
  const [activeType, setActiveType] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchContents = async (reset = false) => {
    const currentPage = reset ? 1 : page;
    try {
      const res = await techContentsApi.getContents({
        content_type: activeType || undefined,
        page: currentPage,
        limit: 12,
      });
      if (reset) {
        setContents(res.contents);
        setPage(2);
      } else {
        setContents(prev => [...prev, ...res.contents]);
        setPage(currentPage + 1);
      }
      setHasMore(res.contents.length === 12);
      setPageState('success');
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  useEffect(() => {
    Promise.all([
      techContentsApi.getContentTypes().then(r => setTypes(r.types)),
      fetchContents(true),
    ]).catch(() => setPageState('error'));
  }, []);

  useEffect(() => {
    fetchContents(true);
  }, [activeType]);

  const handleContentClick = (slug: string) => {
    Taro.navigateTo({ url: `/package-learning/pages/tech-contents/detail/index?slug=${slug}` });
  };

  return (
    <View className="tech-contents-page">
      <ScrollView className="type-bar" scrollX>
        <View
          className={`type-item ${activeType === '' ? 'active' : ''}`}
          onClick={() => setActiveType('')}
        >
          <Text>全部</Text>
        </View>
        {types.map(t => (
          <View
            key={t.value}
            className={`type-item ${activeType === t.value ? 'active' : ''}`}
            onClick={() => setActiveType(t.value)}
          >
            <Text>{t.label}</Text>
          </View>
        ))}
      </ScrollView>

      {pageState === 'loading' && <Loading text="加载中..." />}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Text className="retry-text" onClick={() => fetchContents(true)}>点击重试</Text>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="content-list" scrollY onScrollToLower={() => hasMore && fetchContents()}>
          {contents.length === 0 ? (
            <View className="empty-state"><Text>暂无内容</Text></View>
          ) : (
            contents.map(item => (
              <View key={item.id} className="content-card" onClick={() => handleContentClick(item.slug)}>
                {item.cover_image && <Image className="cover" src={item.cover_image} mode="aspectFill" lazyLoad />}
                <View className="info">
                  <Text className="type-tag">{item.content_type_label}</Text>
                  <Text className="title">{item.title}</Text>
                  <Text className="desc">{item.description || item.excerpt || ''}</Text>
                  <View className="meta">
                    {item.author && <Text className="author">{item.author}</Text>}
                    {item.reading_time && <Text className="time">{item.reading_time}分钟阅读</Text>}
                  </View>
                </View>
              </View>
            ))
          )}
        </ScrollView>
      )}
    </View>
  );
}
