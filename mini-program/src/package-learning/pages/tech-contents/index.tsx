import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Image } from '@tarojs/components';
import { techContentsApi } from '../../../services/techContents';
import type { TechContent, ContentType } from '../../../services/techContents';
import { formatApiError } from '../../../utils/mobileTool';
import Loading from '../../../components/Loading';
import './index.scss';

/**
 * 玻璃光晕换肤（阶段⑧-⑨ Task 8）：
 * - 内容卡套全局 .glass-card（半透明底+发丝描边+磨砂模糊+投影，见 styles/_glass.scss），
 *   本地样式只保留布局/圆角，勿重复定义背景以免击穿玻璃质感；
 * - 类型条为全宽条形面板：surface-1 底 + 玻璃发丝线；类型 chip 常态玻璃描边、选中态 accent 实底；
 * - 类型标签由 #6366f1 实底改 accent-primary 语义对号（文字近白 ink token）；
 * - 分页/类型筛选逻辑不变。
 */

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
              <View key={item.id} className="content-card glass-card" onClick={() => handleContentClick(item.slug)}>
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
