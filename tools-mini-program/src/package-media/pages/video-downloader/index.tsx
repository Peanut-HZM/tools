import { useState, useRef } from 'react';
import Taro from '@tarojs/taro';
import { View, Input, Button, Text, ScrollView } from '@tarojs/components';
import { videoDownloaderApi } from '../../../services/videoDownloader';
import type { VideoInfo, TaskStatusResponse } from '../../../services/videoDownloader';
import { openOrCopyUrl, formatApiError, pollTask } from '../../../utils/mobileTool';
import Loading from '../../../components/Loading';
import './index.scss';

type PageState = 'idle' | 'extracting' | 'downloading' | 'error' | 'success' | 'task-running';

export default function VideoDownloaderPage() {
  const [url, setUrl] = useState('');
  const [pageState, setPageState] = useState<PageState>('idle');
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [taskStatus, setTaskStatus] = useState<TaskStatusResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const abortRef = useRef(false);

  const handleExtract = async () => {
    if (!url.trim()) {
      Taro.showToast({ title: '请输入视频链接', icon: 'none' });
      return;
    }
    abortRef.current = false;
    setPageState('extracting');
    try {
      const res = await videoDownloaderApi.extractVideos(url.trim());
      if (res.videos.length === 0) {
        setPageState('idle');
        Taro.showToast({ title: '未检测到视频', icon: 'none' });
      } else {
        setVideos(res.videos);
        setPageState('success');
      }
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleDownload = async (videoUrl: string) => {
    abortRef.current = false;
    setPageState('downloading');
    try {
      const task = await videoDownloaderApi.createDownloadTask(videoUrl);
      setPageState('task-running');

      const finalStatus = await pollTask(
        () => videoDownloaderApi.getTaskStatus(task.task_id),
        (status) => status.status === 'completed' || status.status === 'failed',
        { interval: 3000, maxAttempts: 100, timeout: 300000 }
      );

      if (abortRef.current) return;

      setTaskStatus(finalStatus);
      if (finalStatus.status === 'completed' && finalStatus.download_url) {
        await openOrCopyUrl(finalStatus.download_url);
      } else if (finalStatus.status === 'failed') {
        setErrorMsg(finalStatus.error || '下载失败');
        setPageState('error');
      }
    } catch (err: any) {
      if (abortRef.current) return;
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleCancel = () => {
    abortRef.current = true;
    setPageState('idle');
    setTaskStatus(null);
  };

  return (
    <View className="video-downloader-page">
      <View className="input-section">
        <Input
          className="url-input"
          placeholder="输入视频页面链接"
          value={url}
          onInput={(e) => setUrl(e.detail.value)}
          type="text"
        />
        <Button
          className="extract-btn"
          onClick={handleExtract}
          disabled={pageState === 'extracting' || pageState === 'downloading'}
        >
          {pageState === 'extracting' ? '提取中...' : '提取视频'}
        </Button>
      </View>

      {(pageState === 'extracting' || pageState === 'downloading') && (
        <Loading text={pageState === 'extracting' ? '正在提取视频...' : '正在创建下载任务...'} />
      )}

      {pageState === 'task-running' && taskStatus && (
        <View className="task-status">
          <Text className="status-text">
            {taskStatus.status === 'pending' ? '排队中' :
             taskStatus.status === 'downloading' ? `下载中 ${taskStatus.progress}%` :
             taskStatus.status === 'completed' ? '下载完成' : '下载失败'}
          </Text>
          {taskStatus.speed && <Text className="speed">{taskStatus.speed}</Text>}
          {taskStatus.eta && <Text className="eta">预计剩余: {taskStatus.eta}</Text>}
          <Button className="cancel-btn" onClick={handleCancel}>取消</Button>
        </View>
      )}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Button className="retry-btn" onClick={handleExtract}>重试</Button>
        </View>
      )}

      {pageState === 'success' && (
        <ScrollView className="video-list" scrollY>
          <Text className="count-text">共提取 {videos.length} 个视频</Text>
          {videos.map((video, idx) => (
            <View key={idx} className="video-item">
              <View className="video-info">
                <Text className="title">{video.title || '未命名视频'}</Text>
                {video.duration && (
                  <Text className="meta">时长: {Math.floor(video.duration / 60)}:{(video.duration % 60).toString().padStart(2, '0')}</Text>
                )}
                {video.quality && <Text className="meta">质量: {video.quality}</Text>}
              </View>
              <Button
                className="download-btn"
                onClick={() => handleDownload(video.url)}
                disabled={pageState === 'downloading' || pageState === 'task-running'}
              >
                下载
              </Button>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}
