import { useState } from 'react';
import Taro from '@tarojs/taro';
import { View, Input, Button, ScrollView, Image, Text } from '@tarojs/components';
import { imageDownloaderApi } from '../../services/imageDownloader';
import type { ImageInfo } from '../../services/imageDownloader';
import { copyText, openOrCopyUrl, formatApiError } from '../../utils/mobileTool';
import Loading from '../../components/Loading';
import './index.scss';

type PageState = 'idle' | 'loading' | 'empty' | 'error' | 'success';

export default function ImageDownloaderPage() {
  const [url, setUrl] = useState('');
  const [pageState, setPageState] = useState<PageState>('idle');
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [errorMsg, setErrorMsg] = useState('');

  const handleExtract = async () => {
    if (!url.trim()) {
      Taro.showToast({ title: '请输入网页链接', icon: 'none' });
      return;
    }
    setPageState('loading');
    try {
      const res = await imageDownloaderApi.extractImages(url.trim());
      if (res.images.length === 0) {
        setPageState('empty');
      } else {
        setImages(res.images);
        setPageState('success');
      }
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleDownload = async (image: ImageInfo) => {
    try {
      Taro.showLoading({ title: '下载中...' });
      const res = await imageDownloaderApi.downloadImage(image.url);
      Taro.hideLoading();
      if (res.oss_url) {
        await openOrCopyUrl(res.oss_url);
      } else {
        await copyText(res.url);
      }
    } catch (err: any) {
      Taro.hideLoading();
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  const handlePreview = (imageUrl: string) => {
    Taro.previewImage({
      urls: [imageUrl],
      current: imageUrl,
    });
  };

  return (
    <View className="image-downloader-page">
      <View className="input-section">
        <Input
          className="url-input"
          placeholder="输入网页链接，提取页面中的图片"
          value={url}
          onInput={(e) => setUrl(e.detail.value)}
          type="text"
        />
        <Button className="extract-btn" onClick={handleExtract} disabled={pageState === 'loading'}>
          {pageState === 'loading' ? '提取中...' : '提取图片'}
        </Button>
      </View>

      {pageState === 'loading' && <Loading text="正在提取图片..." />}

      {pageState === 'empty' && (
        <View className="empty-state">
          <Text>未检测到图片</Text>
          <Text className="hint">请检查链接是否有效</Text>
        </View>
      )}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Button className="retry-btn" onClick={handleExtract}>重试</Button>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="image-list" scrollY>
          <Text className="count-text">共提取 {images.length} 张图片</Text>
          {images.map((img, idx) => (
            <View key={idx} className="image-item">
              <Image
                className="thumbnail"
                src={img.thumbnail || img.url}
                mode="aspectFill"
                onClick={() => handlePreview(img.url)}
                lazyLoad
              />
              <View className="image-info">
                <Text className="format">{img.format || '未知格式'}</Text>
                {img.width && img.height && (
                  <Text className="size">{img.width} x {img.height}</Text>
                )}
              </View>
              <View className="actions">
                <Button className="action-btn" onClick={() => handlePreview(img.url)}>预览</Button>
                <Button className="action-btn primary" onClick={() => handleDownload(img)}>下载</Button>
              </View>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}
