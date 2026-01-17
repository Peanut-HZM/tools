import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface ImageInfo {
  url: string;
  alt: string;
  index: number;
}

export default function ImageDownloader() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const viewOriginalImage = (imageUrl: string) => {
    // 使用后端代理查看原图，避免防盗链问题
    const proxyUrl = `http://localhost:8000/api/tools/download-image?url=${encodeURIComponent(imageUrl)}`;
    window.open(proxyUrl, '_blank');
  };

  const extractImages = async () => {
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
    setImages([]);

    try {
      const response = await fetch(`http://localhost:8000/api/tools/extract-images`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error('获取图片失败');
      }

      const data = await response.json();
      setImages(data.images);
      
      if (data.images.length === 0) {
        setError('该网页没有找到图片');
      }
    } catch (err) {
      setError('获取图片失败，请检查URL是否正确或网络连接');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const downloadImage = async (imageUrl: string, index: number) => {
    try {
      // 使用后端代理下载，确保图片质量
      const proxyUrl = `http://localhost:8000/api/tools/download-image?url=${encodeURIComponent(imageUrl)}`;
      
      // 获取图片数据
      const response = await fetch(proxyUrl);
      
      if (!response.ok) {
        throw new Error('下载失败');
      }
      
      // 获取图片 Blob
      const blob = await response.blob();
      
      // 从 URL 中提取文件扩展名
      const urlObj = new URL(imageUrl);
      const pathname = urlObj.pathname;
      const ext = pathname.substring(pathname.lastIndexOf('.')) || '.jpg';
      
      // 创建 Blob URL
      const blobUrl = URL.createObjectURL(blob);
      
      // 创建下载链接
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `image-${index + 1}${ext}`;
      
      // 触发下载
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // 释放 Blob URL
      setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
      
      console.log(`图片 ${index + 1} 下载成功`);
    } catch (err) {
      console.error('下载失败:', err);
      throw err; // 抛出错误以便批量下载时统计
    }
  };

  const downloadAllImages = async () => {
    if (images.length === 0) return;
    
    setDownloading(true);
    
    // 提示用户
    const message = `准备下载 ${images.length} 张图片。\n\n下载过程中请不要关闭页面。\n\n是否继续？`;
    
    const confirmed = window.confirm(message);
    if (!confirmed) {
      setDownloading(false);
      return;
    }
    
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < images.length; i++) {
      try {
        await downloadImage(images[i].url, i);
        successCount++;
        // 添加延迟避免浏览器阻止多个下载
        await new Promise(resolve => setTimeout(resolve, 500));
      } catch (err) {
        failCount++;
        console.error(`图片 ${i + 1} 下载失败:`, err);
      }
    }
    
    setDownloading(false);
    
    if (failCount === 0) {
      alert(`✅ 全部下载完成！\n\n成功下载 ${successCount} 张图片。`);
    } else {
      alert(`⚠️ 下载完成！\n\n成功: ${successCount} 张\n失败: ${failCount} 张\n\n失败的图片请手动右键另存为。`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 py-8">
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
          <div className="w-16 h-16 bg-cyan-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="fas fa-download text-white text-2xl"></i>
          </div>
          <h1 className="text-4xl font-bold mb-4">网页图片下载器</h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            粘贴网页URL，自动提取并下载该网页的所有图片，支持所有格式，保证原图质量
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
                onKeyDown={(e) => e.key === 'Enter' && extractImages()}
                placeholder="https://example.com"
                className="flex-1 bg-slate-700 text-white px-4 py-3 rounded-lg border border-slate-600 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
              <button
                onClick={extractImages}
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
                    提取图片
                  </>
                )}
              </button>
            </div>
            
            {/* 使用说明 */}
            <div className="mt-4 text-sm text-slate-400">
              <p className="mb-2">💡 使用提示：</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>输入完整的网页URL（包含 http:// 或 https://）</li>
                <li>支持提取所有格式的图片（JPG、PNG、GIF、WebP等）</li>
                <li>点击"下载原图"按钮会自动下载完整质量的图片</li>
                <li>点击图片可以在新窗口查看原图</li>
                <li>使用 Blob 下载方式，确保图片质量不失真</li>
              </ul>
              
              <div className="mt-3 p-3 bg-green-500/10 border border-green-500/30 rounded">
                <p className="text-green-400 font-medium mb-1">✨ 新功能：原图下载</p>
                <p className="text-xs">• 使用后端代理 + Blob 下载，保证原图质量</p>
                <p className="text-xs">• 不会出现图片失真或压缩的问题</p>
                <p className="text-xs">• 支持批量下载，自动保存到下载文件夹</p>
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

        {/* 图片列表 */}
        {images.length > 0 && (
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">
                找到 {images.length} 张图片
              </h2>
              <button
                onClick={downloadAllImages}
                disabled={downloading}
                className="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {downloading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    下载中...
                  </>
                ) : (
                  <>
                    <i className="fas fa-download mr-2"></i>
                    下载全部原图
                  </>
                )}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {images.map((image, index) => (
                <div
                  key={index}
                  className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden hover:border-primary transition-all group"
                >
                  <div className="aspect-square bg-slate-700 flex items-center justify-center overflow-hidden relative">
                    <img
                      src={image.url}
                      alt={image.alt || `图片 ${index + 1}`}
                      className="w-full h-full object-cover cursor-pointer hover:scale-105 transition-transform"
                      onClick={() => viewOriginalImage(image.url)}
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23334155" width="200" height="200"/%3E%3Ctext fill="%2394a3b8" font-family="sans-serif" font-size="14" x="50%25" y="50%25" text-anchor="middle" dominant-baseline="middle"%3E加载失败%3C/text%3E%3C/svg%3E';
                      }}
                    />
                    {/* 悬停提示 */}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
                      <span className="text-white text-sm">
                        <i className="fas fa-search-plus mr-2"></i>
                        点击查看原图
                      </span>
                    </div>
                  </div>
                  <div className="p-4">
                    <p className="text-sm text-slate-400 mb-3 truncate" title={image.alt || `图片 ${index + 1}`}>
                      {image.alt || `图片 ${index + 1}`}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => downloadImage(image.url, index)}
                        className="flex-1 bg-primary hover:bg-blue-700 text-white py-2 rounded-lg transition-colors text-sm font-medium"
                      >
                        <i className="fas fa-download mr-2"></i>
                        下载原图
                      </button>
                      <button
                        onClick={() => viewOriginalImage(image.url)}
                        className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg transition-colors text-sm"
                        title="在新窗口查看原图"
                      >
                        <i className="fas fa-external-link-alt mr-2"></i>
                        查看原图
                      </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-2 text-center">
                      💡 点击图片或"查看原图"按钮打开原图
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* 下载说明 */}
            <div className="mt-8 bg-blue-500/10 border border-blue-500 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <i className="fas fa-info-circle text-blue-500"></i>
                下载说明
              </h3>
              <div className="text-sm text-slate-300 space-y-2">
                <p>• <strong>原图质量</strong>：使用 Blob 下载方式，确保下载的是完整质量的原图，不会失真或压缩</p>
                <p>• <strong>自动下载</strong>：点击"下载原图"按钮，图片会自动保存到浏览器的下载文件夹</p>
                <p>• <strong>批量下载</strong>：点击"下载全部原图"可以一次性下载所有图片</p>
                <p>• <strong>查看原图</strong>：点击图片预览或"打开"按钮可以在新窗口查看完整尺寸的原图</p>
                <p>• <strong>备用方案</strong>：如果自动下载失败，可以右键点击图片选择"图片另存为"</p>
              </div>
            </div>
          </div>
        )}

        {/* 空状态 */}
        {!loading && images.length === 0 && !error && (
          <div className="max-w-3xl mx-auto text-center py-16">
            <i className="fas fa-image text-slate-600 text-6xl mb-4"></i>
            <p className="text-slate-400 text-lg">
              输入网页URL开始提取图片
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
