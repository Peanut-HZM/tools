import { useState, useEffect } from 'react';
import Taro, { useRouter } from '@tarojs/taro';
import { View, Text, Image, ScrollView } from '@tarojs/components';
import { techContentsApi } from '../../../services/techContents';
import type { TechContentDetail } from '../../../services/techContents';
import { formatApiError } from '../../../utils/mobileTool';
import Markdown from '../../../components/Markdown';
import Loading from '../../../components/Loading';
import './index.scss';

export default function TechContentDetailPage() {
  const router = useRouter();
  const slug = router.params.slug || '';
  const [content, setContent] = useState<TechContentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!slug) {
      setError('内容 ID 缺失');
      setLoading(false);
      return;
    }
    techContentsApi.getContentDetail(slug)
      .then(data => {
        setContent(data);
        setLoading(false);
      })
      .catch(err => {
        setError(formatApiError(err));
        setLoading(false);
      });
  }, [slug]);

  if (loading) return <Loading text="加载中..." />;
  if (error) return <View className="error-state"><Text>{error}</Text></View>;
  if (!content) return null;

  return (
    <ScrollView className="tech-content-detail-page" scrollY>
      {content.cover_image && (
        <Image className="cover" src={content.cover_image} mode="aspectFill" />
      )}
      <View className="header">
        <Text className="type">{content.content_type_label}</Text>
        <Text className="title">{content.title}</Text>
        <View className="meta">
          {content.author && <Text className="author">{content.author}</Text>}
          {content.published_at && <Text className="date">{content.published_at.split('T')[0]}</Text>}
          <Text className="views">{content.view_count || content.views || 0} 阅读</Text>
        </View>
        {content.tags && content.tags.length > 0 && (
          <View className="tags">
            {content.tags.map(tag => (
              <Text key={tag} className="tag">{tag}</Text>
            ))}
          </View>
        )}
      </View>
      <View className="body">
        {content.content ? (
          <Markdown content={content.content} />
        ) : (
          <Text className="no-content">暂无正文内容</Text>
        )}
      </View>
    </ScrollView>
  );
}
