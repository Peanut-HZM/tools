> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复网页图片下载器无法从彼岸图网提取高清原图的问题。

**Architecture:** 扩展后端 `ImageDownloaderService.extract_images` 的图片 URL 提取逻辑，优先读取 `data-pic`、`data-original`、`data-src`、`src`，并检查父级 `<a>` 标签的 `data-pic`；`download_image` 根据目标域名自动添加 `Referer` 绕过防盗链。前端在图片卡片增加尺寸显示。

**Tech Stack:** Python 3.10+, FastAPI, BeautifulSoup4, requests, React 18, TypeScript, Tailwind CSS

---

# 图片下载器原图提取修复 — 实现计划

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/image_downloader_service.py` | 修改 | 核心：扩展图片 URL 提取、自动推断 Referer |
| `frontend/src/components/Tools/ImageDownloader.tsx` | 修改 | 在图片卡片显示 width × height |

---

## Task 1: 后端图片 URL 提取逻辑改造

**Files:**
- Modify: `backend/app/services/image_downloader_service.py:149-205`

- [ ] **Step 1: 新增 `_get_img_url` 辅助方法**

在 `ImageDownloaderService` 类中、紧随 `__init__` 之后的位置，添加以下方法：

```python
    def _get_img_url(self, img_tag, page_url: str) -> Optional[str]:
        """从 img 标签及其父级 a 标签中提取最佳图片 URL"""
        candidates = [
            img_tag.get('data-pic'),
            img_tag.get('data-original'),
            img_tag.get('data-src'),
            img_tag.get('src'),
        ]

        # 如果 img 自身没有 data-pic，检查父级 a 标签
        parent_a = img_tag.find_parent('a')
        if parent_a:
            parent_data_pic = parent_a.get('data-pic')
            if parent_data_pic:
                candidates.insert(0, parent_data_pic)

        img_url = next((url for url in candidates if url), None)
        if not img_url:
            return None

        return urljoin(page_url, img_url.strip())
```

- [ ] **Step 2: 重构 `extract_images` 使用新辅助方法**

将 `extract_images` 方法中的这段代码：

```python
            for index, img in enumerate(img_tags):
                img_url = img.get('src') or img.get('data-src') or img.get('data-original')

                if not img_url:
                    continue

                absolute_url = urljoin(url, img_url)
```

替换为：

```python
            for index, img in enumerate(img_tags):
                absolute_url = self._get_img_url(img, url)

                if not absolute_url:
                    continue
```

- [ ] **Step 3: 本地语法检查**

Run: `cd backend && python -m py_compile app/services/image_downloader_service.py`
Expected: 无输出（表示语法正确）

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/image_downloader_service.py
git commit -m "feat: 图片下载支持 data-pic 与父级 a 标签原图提取"
```

---

## Task 2: 后端下载代理增加防盗链 Referer

**Files:**
- Modify: `backend/app/services/image_downloader_service.py:60-62 和 414-422`

- [ ] **Step 1: 在 `ImageDownloaderService` 类顶部添加 Referer 映射**

在 `class ImageDownloaderService:` 之后、`def __init__` 之前，添加：

```python
    # 针对需要 Referer 绕过防盗链的站点
    REFERER_MAP = {
        'pic.netbian.com': 'https://pic.netbian.com',
    }
```

- [ ] **Step 2: 新增 `_get_referer` 辅助方法**

在 `_get_img_url` 方法之后，添加：

```python
    def _get_referer(self, url: str) -> Optional[str]:
        """根据 URL 域名返回合适的 Referer，帮助绕过防盗链"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return self.REFERER_MAP.get(domain)
```

- [ ] **Step 3: 修改 `download_image` 添加 Referer 头**

找到 `download_image` 方法中的 headers 定义：

```python
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
```

替换为：

```python
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            referer = self._get_referer(url)
            if referer:
                headers['Referer'] = referer
```

- [ ] **Step 4: 本地语法检查**

Run: `cd backend && python -m py_compile app/services/image_downloader_service.py`
Expected: 无输出

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_downloader_service.py
git commit -m "feat: 图片下载根据域名自动添加 Referer 绕过防盗链"
```

---

## Task 3: 前端图片卡片显示尺寸

**Files:**
- Modify: `frontend/src/components/Tools/ImageDownloader.tsx:286-289`

- [ ] **Step 1: 修改图片标题区域展示 width × height**

找到以下 JSX：

```tsx
                    <p className="text-sm text-slate-400 mb-3 truncate" title={image.alt || `图片 ${index + 1}`}>
                      {image.alt || `图片 ${index + 1}`}
                    </p>
```

替换为：

```tsx
                    <p className="text-sm text-slate-400 mb-3 truncate" title={image.alt || `图片 ${index + 1}`}>
                      {image.alt || `图片 ${index + 1}`}
                      {(image.width && image.height) && (
                        <span className="ml-2 text-xs text-slate-500">
                          {image.width} × {image.height}
                        </span>
                      )}
                    </p>
```

- [ ] **Step 2: 检查 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误（项目若无类型错误则通过）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Tools/ImageDownloader.tsx
git commit -m "feat: 图片下载器卡片显示图片尺寸"
```

---

## Task 4: 本地服务重启与浏览器验证

**Files:**
- 无代码变更

- [ ] **Step 1: 重启前后端服务**

Run: `python dev_services.py restart`
Expected: 服务成功重启，终端显示前后端启动成功

- [ ] **Step 2: 使用 agent-browser 打开图片下载器**

使用 `agent-browser` skill 或 Playwright 工具打开：

```
http://localhost:5178/tools/image-downloader
```

- [ ] **Step 3: 输入目标 URL 并提取**

在输入框中填入：

```
https://pic.netbian.com/tupian/43254.html
```

点击"提取图片"按钮。

- [ ] **Step 4: 验证提取结果**

Expected:
- 页面显示"找到 N 张图片"，N > 0
- 图片 URL 以 `-1.jpg` 结尾（高清原图标识）
- 图片卡片显示尺寸信息（如 `1920 × 1080`）
- 浏览器 Console 无错误

- [ ] **Step 5: 验证下载/查看原图**

Expected:
- 点击"查看原图"能在新标签页打开完整尺寸图片
- 点击"下载原图"能触发浏览器下载
- 批量下载"下载全部原图"至少成功一张

- [ ] **Step 6: 提交验证结果记录（可选）**

若验证通过，无需额外提交；若有截图或日志需要记录，可追加到设计文档。

---

## 自我审查

### 1. Spec 覆盖检查

| Spec 要求 | 对应任务 |
|-----------|----------|
| 提取 `data-pic` 属性 | Task 1 Step 1 |
| 检查父级 `<a>` 的 `data-pic` | Task 1 Step 1 |
| 自动拼接相对路径 | Task 1 Step 1（`urljoin`） |
| 下载代理自动添加 Referer | Task 2 |
| 前端显示图片尺寸 | Task 3 |
| 浏览器验证 | Task 4 |

### 2. Placeholder 扫描

- [x] 无 "TBD" / "TODO"
- [x] 无 "Add appropriate error handling" 等模糊描述
- [x] 每个步骤包含具体代码或命令
- [x] 文件路径使用绝对项目内路径

### 3. 类型一致性检查

- `ImageInfo` 中的 `width` / `height` 为 `Optional[int]`，前端条件渲染使用 `image.width && image.height`，一致。
- `_get_img_url` 返回 `Optional[str]`，与 `extract_images` 中的 `if not absolute_url: continue` 一致。
- `_get_referer` 返回 `Optional[str]`，与 `if referer: headers['Referer'] = referer` 一致。

---

## 执行方式选择

Plan complete and saved to `docs/superpowers/plans/2026-06-27-image-downloader-original-plan.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - 每个 Task 派发独立子代理执行，中间 review，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 批量执行任务并设置检查点

Which approach would you like?
