---
author: Peanut
created_at: 2026-06-27
purpose: 修复网页图片下载器无法提取彼岸图网高清原图的问题
---

# 图片下载器原图提取修复设计

## 背景

当前图片下载器在提取 `https://pic.netbian.com/tupian/43254.html` 时无法找到图片。

### 问题根源

彼岸图网的列表页结构如下：

```html
<a href="/tupian/xxxxx.html" data-pic="/uploads/allimg/20251223/241429-1.jpg">
  <img src="/uploads/allimg/20251223/241429-2.jpg" alt="...">
</a>
```

- 缩略图地址在 `<img src>` 中
- **高清原图地址在父级 `<a>` 的 `data-pic` 属性中**

而后端 `extract_images` 只检查 `src`、`data-src`、`data-original`，未检查 `data-pic`，且未处理父级元素。

## 目标

1. 修复图片提取逻辑，使其能够正确提取彼岸图网的高清原图
2. 下载时自动处理防盗链（通过 Referer）
3. 前端保持现有交互，并增加图片尺寸显示

## 架构与数据流

```text
用户输入 URL
    ↓
前端 POST /tools/extract-images
    ↓
后端 requests 获取网页 HTML
    ↓
BeautifulSoup 解析图片
    ↓
提取优先级：data-pic → data-original → data-src → src
    ↓
若 <img> 自身无 data-pic，检查父级 <a> 的 data-pic
    ↓
相对路径自动拼接为绝对 URL
    ↓
返回图片列表给前端
    ↓
用户点击下载/查看
    ↓
前端请求 /tools/download-image?url=...
    ↓
后端自动根据目标域名添加 Referer 头下载
    ↓
上传 OSS 或直接透传 Blob
```

## 后端改造

### 修改文件

`backend/app/services/image_downloader_service.py`

### 1. 扩展图片 URL 提取逻辑

新增辅助方法：

```python
def _get_img_url(self, img_tag, page_url: str) -> Optional[str]:
    """从 img 标签及其父级 a 标签中提取最佳图片 URL"""
    candidates = [
        img_tag.get('data-pic'),
        img_tag.get('data-original'),
        img_tag.get('data-src'),
        img_tag.get('src'),
    ]

    parent_a = img_tag.find_parent('a')
    if parent_a and parent_a.get('data-pic'):
        candidates.insert(0, parent_a.get('data-pic'))

    img_url = next((url for url in candidates if url), None)
    if not img_url:
        return None

    return urljoin(page_url, img_url.strip())
```

### 2. 新增域名级 Referer 映射

```python
REFERER_MAP = {
    'pic.netbian.com': 'https://pic.netbian.com',
}

def _get_referer(self, url: str) -> Optional[str]:
    """根据 URL 域名返回合适的 Referer，帮助绕过防盗链"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    return self.REFERER_MAP.get(domain)
```

### 3. 下载代理增加 Referer

```python
def download_image(self, url: str, user_id: str, save_history: bool = True) -> DownloadedImage:
    headers = {
        'User-Agent': '...',
    }
    referer = self._get_referer(url)
    if referer:
        headers['Referer'] = referer

    response = requests.get(url, headers=headers, stream=True, timeout=30)
    ...
```

## 前端改造

### 修改文件

`frontend/src/components/Tools/ImageDownloader.tsx`

### 改动内容

在图片卡片的信息区域增加尺寸展示。后端返回的 `ImageInfo` 中已包含 `width` 和 `height`：

```tsx
<p className="text-sm text-slate-400 mb-3 truncate">
  {image.alt || `图片 ${index + 1}`}
  {(image.width && image.height) && (
    <span className="ml-2 text-xs text-slate-500">
      {image.width} × {image.height}
    </span>
  )}
</p>
```

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| `data-pic` 等属性均为空 | 跳过该图片 |
| 相对路径拼接失败 | 跳过 |
| 防盗链拒绝 | `download_image` 抛出异常，前端显示失败 |
| OSS 上传失败 | 抛出异常，不静默兜底 |
| 配额不足 | 批量下载时跳过并记录原因 |

## 测试验证

1. 本地启动前后端服务
2. 访问 `http://localhost:5178/tools/image-downloader`
3. 输入 `https://pic.netbian.com/tupian/43254.html`
4. 点击"提取图片"
5. 验证：
   - 能提取到多张图片
   - 图片 URL 以 `-1.jpg` 结尾（高清原图标识）
   - 图片卡片显示尺寸信息
   - 点击"查看原图"能正常打开高清大图
   - 点击"下载原图"能正常下载
   - 浏览器 Console 无任何错误

## 影响范围

- 仅修改 `ImageDownloaderService` 和 `ImageDownloader.tsx`
- 不改变 API 路由、Schema、数据库表结构
- 不影响其他工具模块

## 非目标

- 不引入通用规则引擎
- 不做批量并发下载优化
- 不新增配额或权限相关逻辑
