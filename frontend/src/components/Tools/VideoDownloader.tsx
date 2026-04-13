import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../../config/api';

interface VideoInfo {
  url: string;
  type: string;
  source: string;
  index: number;
  duration: number;
}

interface DownloadTask {
  task_id: string;
  status: string;
  progress: number;
  file_size?: string;
  speed?: string;
  eta?: string;
  error?: string;
}

export default function VideoDownloader() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [downloadTasks, setDownloadTasks] = useState<Map<number, DownloadTask>>(new Map());
  const [selectedQuality, setSelectedQuality] = useState<string>('best');

  const extractVideos = async () => {
    if (!url.trim()) {
      setError('请输入网页URL');
      return;
    }

    // 验证URL格式
    try {
      new URL(url);
    } catch {
      setError('请输入有效的URL地址');
      return;
    }

    setLoading(true);
    setError(null);
    setVideos([]);

    try {
      const response = await fetch(`${API_BASE_URL}/tools/extract-videos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error('获取视频失败');
      }

      const data = await response.json();
      
      // 只过滤掉iframe视频中的无效项，保留所有其他视频（包括短视频和GIF）
      const validVideos = data.videos.filter((video: VideoInfo) => {
        // iframe视频保留
        if (video.source === 'iframe') return true;
        // 所有其他视频都保留（包括短视频和GIF）
        return true;
      });
      
      setVideos(validVideos);
      
      if (validVideos.length === 0) {
        setError('该网页没有找到有效的视频资源');
      }
    } catch (err) {
      setError('获取视频失败，请检查URL是否正确或网络连接');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'video':
        return 'bg-blue-500';
      case 'source':
        return 'bg-green-500';
      case 'iframe':
        return 'bg-purple-500';
      case 'script':
        return 'bg-orange-500';
      case 'html':
        return 'bg-yellow-500';
      case 'data-attribute':
        return 'bg-pink-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'video':
        return 'Video标签';
      case 'source':
        return 'Source标签';
      case 'iframe':
        return '嵌入视频';
      case 'script':
        return '脚本提取';
      case 'html':
        return 'HTML内容';
      case 'data-attribute':
        return 'Data属性';
      default:
        return '未知';
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('链接已复制到剪贴板！');
    });
  };

  const downloadVideo = async (videoUrl: string, index: number) => {
    try {
      // 检查是否是HLS视频
      if (videoUrl.includes('.m3u8') || videoUrl.includes('/hls/') || videoUrl.includes('.ts')) {
        // 先尝试获取错误信息
        const response = await fetch(`${API_BASE_URL}/tools/download-video?url=${encodeURIComponent(videoUrl)}`);
        if (!response.ok) {
          const errorData = await response.json();
          alert(errorData.detail || '这是HLS流媒体视频，需要使用专业工具下载');
          return;
        }
      }
      
      // 使用后端代理下载
      const proxyUrl = `${API_BASE_URL}/tools/download-video?url=${encodeURIComponent(videoUrl)}`;
      
      const link = document.createElement('a');
      link.href = proxyUrl;
      link.download = `video-${index + 1}`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('下载失败:', err);
      // 备用方案 - 在新窗口打开
      window.open(videoUrl, '_blank');
    }
  };

  const isHLSVideo = (video: VideoInfo) => {
    return video.url.includes('.m3u8') || video.url.includes('/hls/') || video.url.includes('.ts');
  };

  const canPreview = (video: VideoInfo) => {
    // 只有非iframe的视频才能预览
    if (video.source === 'iframe') return false;
    
    // 检查是否是可以直接播放的格式
    const playableTypes = ['video/mp4', 'video/webm', 'video/ogg'];
    return playableTypes.includes(video.type) || video.url.match(/\.(mp4|webm|ogg)(\?|$)/i);
  };

  const formatDuration = (seconds: number) => {
    if (seconds <= 0) return '未知';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
  };

  // yt-dlp 服务器下载功能
  const downloadWithYtdlp = async (videoUrl: string, videoIndex: number) => {
    try {
      // 创建下载任务
      const response = await fetch(`${API_BASE_URL}/tools/download-video-ytdlp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: videoUrl,
          quality: selectedQuality,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '创建下载任务失败');
      }

      const data = await response.json();
      const taskId = data.task_id;

      // 初始化任务状态
      const newTask: DownloadTask = {
        task_id: taskId,
        status: 'pending',
        progress: 0,
      };
      
      setDownloadTasks(prev => new Map(prev).set(videoIndex, newTask));

      // 开始轮询任务状态
      pollTaskStatus(taskId, videoIndex);

    } catch (err) {
      console.error('下载失败:', err);
      alert(`下载失败: ${err instanceof Error ? err.message : '未知错误'}`);
    }
  };

  const pollTaskStatus = async (taskId: string, videoIndex: number) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tools/download-task/${taskId}`);
        
        if (!response.ok) {
          throw new Error('查询任务状态失败');
        }

        const task: DownloadTask = await response.json();
        
        // 更新任务状态
        setDownloadTasks(prev => new Map(prev).set(videoIndex, task));

        // 如果任务完成，停止轮询并下载文件
        if (task.status === 'completed') {
          clearInterval(pollInterval);
          await downloadCompletedFile(taskId, videoIndex);
        }

        // 如果任务失败或取消，停止轮询
        if (task.status === 'failed' || task.status === 'cancelled') {
          clearInterval(pollInterval);
          if (task.error) {
            alert(`下载失败: ${task.error}`);
          }
        }

      } catch (err) {
        console.error('轮询任务状态失败:', err);
        clearInterval(pollInterval);
      }
    }, 1000); // 每秒轮询一次
  };

  const downloadCompletedFile = async (taskId: string, videoIndex: number) => {
    try {
      const downloadUrl = `${API_BASE_URL}/tools/download-file/${taskId}`;
      
      // 获取文件
      const response = await fetch(downloadUrl);
      
      if (!response.ok) {
        throw new Error('下载文件失败');
      }

      // 获取文件 Blob
      const blob = await response.blob();
      
      // 创建 Blob URL
      const blobUrl = URL.createObjectURL(blob);
      
      // 创建下载链接
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `video-${videoIndex + 1}.mp4`;
      
      // 触发下载
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // 释放 Blob URL
      setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
      
      // 清除任务状态
      setTimeout(() => {
        setDownloadTasks(prev => {
          const newMap = new Map(prev);
          newMap.delete(videoIndex);
          return newMap;
        });
      }, 3000);
    } catch (err) {
      console.error('下载文件失败:', err);
      alert(`下载文件失败: ${err instanceof Error ? err.message : '未知错误'}`);
    }
  };

  const cancelDownload = async (taskId: string, videoIndex: number) => {
    try {
      const response = await fetch(`http://localhost:8000/api/tools/download-task/${taskId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('取消任务失败');
      }

      // 清除任务状态
      setDownloadTasks(prev => {
        const newMap = new Map(prev);
        newMap.delete(videoIndex);
        return newMap;
      });

    } catch (err) {
      console.error('取消任务失败:', err);
    }
  };

  return (
    <div className="text-slate-100 py-8">
      <div className="container mx-auto px-6">
        {/* 返回按钮 */}
        <button
          onClick={() => navigate('/')}
          className="mb-6 text-slate-400 hover:text-white transition-colors flex items-center gap-2"
        >
          <i className="fas fa-arrow-left"></i>
          返回首页
        </button>

        {/* 标题 */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="fas fa-video text-white text-2xl"></i>
          </div>
          <h1 className="text-4xl font-bold mb-4">网页视频下载器</h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            粘贴网页URL，自动提取并下载视频资源，支持MP4、WebM、M3U8等多种格式
          </p>
        </div>

        {/* 输入区域 */}
        <div className="max-w-3xl mx-auto mb-8">
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
            <label className="block text-sm font-medium mb-2">网页URL</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && extractVideos()}
                placeholder="https://example.com"
                className="flex-1 bg-slate-700 text-white px-4 py-3 rounded-lg border border-slate-600 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
              <button
                onClick={extractVideos}
                disabled={loading}
                className="bg-primary hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    提取中...
                  </>
                ) : (
                  <>
                    <i className="fas fa-search mr-2"></i>
                    提取视频
                  </>
                )}
              </button>
            </div>
            
            {/* 使用说明 */}
            <div className="mt-4 text-sm text-slate-400">
              <p className="mb-2">💡 使用提示：</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>输入完整的网页URL（包含 http:// 或 https://）</li>
                <li>支持提取 MP4、WebM、OGG、M3U8、MKV 等12种格式</li>
                <li>支持提取 YouTube、Vimeo、Bilibili、TikTok 等14+平台的嵌入视频</li>
                <li>某些视频可能需要特殊工具下载（如YouTube）</li>
                <li>复制链接后可使用专业下载工具（如IDM、you-get等）</li>
              </ul>
              
              <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
                <p className="text-yellow-400 font-medium mb-1">⚠️ 检测限制：</p>
                <p className="text-xs">1. 动态加载的视频（需要JavaScript执行）可能无法检测</p>
                <p className="text-xs">2. 需要登录才能访问的视频无法提取</p>
                <p className="text-xs">3. 使用特殊加密的视频链接可能无法检测</p>
                <p className="text-xs mt-2 text-yellow-300">💡 如果检测不到：打开浏览器开发者工具（F12）→ 网络 → 媒体，播放视频查看实际URL</p>
              </div>
            </div>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="max-w-3xl mx-auto mb-8">
            <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded-lg">
              <i className="fas fa-exclamation-circle mr-2"></i>
              {error}
            </div>
          </div>
        )}

        {/* 视频列表 */}
        {videos.length > 0 && (
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">
                找到 {videos.length} 个视频资源
              </h2>
              
              {/* 质量选择器 */}
              <div className="flex items-center gap-3">
                <label className="text-sm text-slate-400">下载质量:</label>
                <select
                  value={selectedQuality}
                  onChange={(e) => setSelectedQuality(e.target.value)}
                  className="bg-slate-800 text-white px-4 py-2 rounded-lg border border-slate-600 focus:border-primary focus:outline-none"
                >
                  <option value="best">最佳质量</option>
                  <option value="1080p">1080p</option>
                  <option value="720p">720p</option>
                  <option value="480p">480p</option>
                  <option value="360p">360p</option>
                  <option value="worst">最低质量</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {videos.map((video, index) => (
                <div
                  key={index}
                  className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden hover:border-primary transition-all"
                >
                  {/* 视频预览区域 */}
                  <div className="aspect-video bg-slate-900 flex items-center justify-center overflow-hidden">
                    {canPreview(video) ? (
                      <video
                        src={video.url}
                        controls
                        className="w-full h-full"
                        preload="metadata"
                        onError={(e) => {
                          // 如果视频加载失败，显示占位符
                          (e.target as HTMLVideoElement).style.display = 'none';
                          const parent = (e.target as HTMLVideoElement).parentElement;
                          if (parent) {
                            parent.innerHTML = '<div class="flex flex-col items-center justify-center h-full text-slate-500"><i class="fas fa-video text-4xl mb-2"></i><p class="text-sm">无法预览</p></div>';
                          }
                        }}
                      >
                        您的浏览器不支持视频播放
                      </video>
                    ) : video.source === 'iframe' ? (
                      <div className="flex flex-col items-center justify-center h-full text-slate-400">
                        <i className="fas fa-play-circle text-5xl mb-3"></i>
                        <p className="text-sm">嵌入式视频</p>
                        <p className="text-xs text-slate-500 mt-1">点击下方按钮观看</p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-slate-500">
                        <i className="fas fa-video text-4xl mb-2"></i>
                        <p className="text-sm">{video.type}</p>
                        <p className="text-xs text-slate-600 mt-1">不支持预览</p>
                      </div>
                    )}
                  </div>

                  {/* 视频信息 */}
                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-3 flex-wrap">
                      <span className={`${getSourceBadgeColor(video.source)} text-white text-xs px-2 py-1 rounded`}>
                        {getSourceLabel(video.source)}
                      </span>
                      <span className="bg-slate-700 text-slate-300 text-xs px-2 py-1 rounded">
                        {video.type}
                      </span>
                      {isHLSVideo(video) && (
                        <span className="bg-red-500 text-white text-xs px-2 py-1 rounded">
                          <i className="fas fa-exclamation-triangle mr-1"></i>
                          HLS流媒体
                        </span>
                      )}
                      {video.duration > 0 && (
                        <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded">
                          <i className="fas fa-clock mr-1"></i>
                          {formatDuration(video.duration)}
                        </span>
                      )}
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex flex-col gap-2">
                      {/* 下载任务进度 */}
                      {downloadTasks.has(index) && (
                        <div className="bg-slate-700 rounded-lg p-3 mb-2">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs text-slate-300">
                              {downloadTasks.get(index)?.status === 'pending' && '等待中...'}
                              {downloadTasks.get(index)?.status === 'downloading' && '下载中...'}
                              {downloadTasks.get(index)?.status === 'completed' && '✅ 完成'}
                              {downloadTasks.get(index)?.status === 'failed' && '❌ 失败'}
                            </span>
                            {downloadTasks.get(index)?.status === 'downloading' && (
                              <button
                                onClick={() => cancelDownload(downloadTasks.get(index)!.task_id, index)}
                                className="text-xs text-red-400 hover:text-red-300"
                              >
                                取消
                              </button>
                            )}
                          </div>
                          
                          {/* 进度条 */}
                          <div className="w-full bg-slate-600 rounded-full h-2 mb-2">
                            <div
                              className="bg-green-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${downloadTasks.get(index)?.progress || 0}%` }}
                            />
                          </div>
                          
                          {/* 下载信息 */}
                          <div className="flex items-center justify-between text-xs text-slate-400">
                            <span>{downloadTasks.get(index)?.progress?.toFixed(1)}%</span>
                            <div className="flex gap-3">
                              {downloadTasks.get(index)?.speed && (
                                <span>
                                  <i className="fas fa-tachometer-alt mr-1"></i>
                                  {downloadTasks.get(index)?.speed}
                                </span>
                              )}
                              {downloadTasks.get(index)?.eta && (
                                <span>
                                  <i className="fas fa-clock mr-1"></i>
                                  {downloadTasks.get(index)?.eta}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* HLS视频 - 服务器下载 */}
                      {isHLSVideo(video) && !downloadTasks.has(index) && (
                        <button
                          onClick={() => downloadWithYtdlp(video.url, index)}
                          className="bg-green-500 hover:bg-green-600 text-white py-2 rounded-lg transition-colors text-sm w-full"
                        >
                          <i className="fas fa-server mr-2"></i>
                          服务器下载 (支持HLS)
                        </button>
                      )}
                      
                      {/* 普通视频 - 直接下载 */}
                      {video.source !== 'iframe' && canPreview(video) && !isHLSVideo(video) && !downloadTasks.has(index) && (
                        <>
                          <button
                            onClick={() => downloadVideo(video.url, index)}
                            className="bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg transition-colors text-sm w-full"
                          >
                            <i className="fas fa-download mr-2"></i>
                            直接下载
                          </button>
                          <button
                            onClick={() => downloadWithYtdlp(video.url, index)}
                            className="bg-green-500 hover:bg-green-600 text-white py-2 rounded-lg transition-colors text-sm w-full"
                          >
                            <i className="fas fa-server mr-2"></i>
                            服务器下载
                          </button>
                        </>
                      )}
                      
                      {/* HLS视频 - 查看下载方法（备用） */}
                      {isHLSVideo(video) && !downloadTasks.has(index) && (
                        <button
                          onClick={() => downloadVideo(video.url, index)}
                          className="bg-yellow-500 hover:bg-yellow-600 text-white py-2 rounded-lg transition-colors text-sm w-full"
                        >
                          <i className="fas fa-info-circle mr-2"></i>
                          查看手动下载方法
                        </button>
                      )}
                      
                      {/* iframe视频 */}
                      {video.source === 'iframe' && !downloadTasks.has(index) && (
                        <>
                          <a
                            href={video.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-purple-500 hover:bg-purple-600 text-white py-2 rounded-lg transition-colors text-sm text-center"
                          >
                            <i className="fas fa-play mr-2"></i>
                            观看视频
                          </a>
                          <button
                            onClick={() => downloadWithYtdlp(video.url, index)}
                            className="bg-green-500 hover:bg-green-600 text-white py-2 rounded-lg transition-colors text-sm w-full"
                          >
                            <i className="fas fa-server mr-2"></i>
                            服务器下载
                          </button>
                        </>
                      )}
                      
                      <div className="flex gap-2">
                        <button
                          onClick={() => copyToClipboard(video.url)}
                          className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg transition-colors text-sm"
                        >
                          <i className="fas fa-copy mr-2"></i>
                          复制链接
                        </button>
                        
                        <a
                          href={video.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg transition-colors text-sm text-center"
                        >
                          <i className="fas fa-external-link-alt mr-2"></i>
                          打开
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 下载提示 */}
            <div className="mt-8 bg-blue-500/10 border border-blue-500 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <i className="fas fa-info-circle text-blue-500"></i>
                下载说明
              </h3>
              <div className="text-sm text-slate-300 space-y-2">
                <p>• <strong>🚀 服务器下载（推荐）</strong>：使用 yt-dlp 在服务器端下载，支持所有格式包括 HLS 流媒体</p>
                <div className="ml-6 space-y-1 text-xs bg-green-500/10 p-3 rounded">
                  <p className="text-green-400">✨ 新功能特点：</p>
                  <p>• 支持 YouTube、Vimeo、Bilibili 等1000+网站</p>
                  <p>• 自动处理 HLS/M3U8 流媒体视频</p>
                  <p>• 可选择视频质量（最佳、1080p、720p、480p等）</p>
                  <p>• 实时显示下载进度和速度</p>
                  <p>• 自动合并视频和音频（使用 ffmpeg）</p>
                  <p>• 下载完成后自动保存到本地</p>
                </div>
                <p>• <strong>直接下载</strong>：适用于简单的 MP4/WebM 视频，点击即可下载</p>
                <p>• <strong>HLS流媒体视频</strong>：推荐使用"服务器下载"功能，自动处理 .m3u8 和 .ts 文件</p>
                <p>• <strong>嵌入视频</strong>：YouTube等平台视频使用"服务器下载"功能</p>
                <p>• <strong>手动下载方法</strong>：如果自动下载失败，可以查看手动下载说明</p>
              </div>
            </div>
          </div>
        )}

        {/* 空状态 */}
        {!loading && videos.length === 0 && !error && (
          <div className="max-w-3xl mx-auto text-center py-16">
            <i className="fas fa-video text-slate-600 text-6xl mb-4"></i>
            <p className="text-slate-400 text-lg">
              输入网页URL开始提取视频
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
