# 下载目录修改说明

## 📝 修改内容

将视频下载的默认目录从系统临时目录修改为项目根目录下的 `downloads` 文件夹。

## 🔧 修改的文件

### 1. backend/app/services/ytdlp_service.py
**修改前**:
```python
TEMP_DIR = "/tmp/ytdlp_downloads"
```

**修改后**:
```python
# 使用项目根目录下的downloads文件夹
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEMP_DIR = str(PROJECT_ROOT / "downloads")
```

### 2. backend/app/services/download_manager.py
**修改前**:
```python
TEMP_DIR = "/tmp/ytdlp_downloads"
```

**修改后**:
```python
# 使用项目根目录下的downloads文件夹
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEMP_DIR = str(PROJECT_ROOT / "downloads")
```

### 3. 创建downloads目录
```bash
mkdir -p downloads
```

### 4. 添加到.gitignore
```bash
echo "downloads/" >> .gitignore
```

## 📂 目录结构

```
项目根目录/
├── backend/
│   └── app/
│       └── services/
│           ├── ytdlp_service.py      # 修改了TEMP_DIR
│           └── download_manager.py   # 修改了TEMP_DIR
├── frontend/
├── downloads/                         # ✨ 新建的下载目录
│   └── jNQXAC9IVRw.mp4              # 下载的视频文件
├── .gitignore                        # 添加了downloads/
└── ...
```

## ✅ 测试结果

### 测试下载
```bash
# 创建下载任务
curl -X POST http://localhost:8000/api/tools/download-video-ytdlp \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=jNQXAC9IVRw", "quality": "worst"}'

# 响应
{
    "task_id": "4aacc5e6-a289-4181-aa5c-21e449125a1e",
    "status": "pending",
    "message": "下载任务已创建，正在排队中..."
}

# 查询任务状态
curl http://localhost:8000/api/tools/download-task/4aacc5e6-a289-4181-aa5c-21e449125a1e

# 响应
{
    "task_id": "4aacc5e6-a289-4181-aa5c-21e449125a1e",
    "status": "completed",
    "progress": 100.0
}
```

### 验证文件位置
```bash
ls -lh downloads/

# 输出
total 624
-rw-r--r--  1 user  staff   309K Dec 28 15:52 jNQXAC9IVRw.mp4
```

✅ **测试通过**: 文件成功下载到 `downloads/` 目录

## 🎯 优势

### 修改前（/tmp/ytdlp_downloads）
- ❌ 文件在系统临时目录
- ❌ 可能被系统自动清理
- ❌ 不方便用户查找
- ❌ 不同操作系统路径不同

### 修改后（项目/downloads）
- ✅ 文件在项目目录下
- ✅ 用户容易找到
- ✅ 统一的路径
- ✅ 可以自己管理清理
- ✅ 不会被系统自动删除

## 📋 功能说明

### 自动清理机制
下载的文件会在以下情况被清理：
1. **任务完成1小时后**: 自动删除文件和任务记录
2. **手动清理**: 用户可以手动删除downloads目录中的文件

### 文件命名
- 格式: `{video_id}.{ext}`
- 示例: `jNQXAC9IVRw.mp4`
- video_id: 视频的唯一标识符
- ext: 文件扩展名（通常是mp4）

### 并发下载
- 最多同时下载5个视频
- 文件都保存在downloads目录
- 不会冲突（使用唯一的video_id）

## 🔒 安全性

### .gitignore
downloads目录已添加到.gitignore，确保：
- ✅ 下载的视频不会被提交到Git
- ✅ 保护用户隐私
- ✅ 减小仓库大小

### 文件权限
- 文件权限: 644 (rw-r--r--)
- 目录权限: 755 (rwxr-xr-x)
- 只有运行服务的用户可以写入

## 📊 磁盘空间管理

### 自动清理
- **清理间隔**: 每1小时
- **任务过期**: 1小时后删除
- **文件大小限制**: 单个文件最大500MB

### 手动清理
```bash
# 查看downloads目录大小
du -sh downloads/

# 清理所有下载文件
rm -rf downloads/*

# 清理特定文件
rm downloads/jNQXAC9IVRw.mp4
```

### 监控建议
```bash
# 定期检查目录大小
watch -n 60 'du -sh downloads/'

# 如果超过5GB，考虑清理
if [ $(du -s downloads/ | cut -f1) -gt 5242880 ]; then
    echo "⚠️ downloads目录超过5GB，建议清理"
fi
```

## 🚀 用户体验

### 下载流程
1. 用户在前端点击"服务器下载"
2. 后端创建下载任务
3. 视频下载到 `downloads/` 目录
4. 前端自动触发文件下载
5. 用户获得视频文件
6. 1小时后服务器自动清理

### 查找下载文件
如果用户想要查看服务器上的文件：
```bash
# 进入项目目录
cd /path/to/project

# 查看下载的文件
ls -lh downloads/

# 播放视频（macOS）
open downloads/jNQXAC9IVRw.mp4

# 播放视频（Linux）
vlc downloads/jNQXAC9IVRw.mp4
```

## 📝 配置说明

### 修改下载目录
如果需要修改下载目录，编辑以下文件：

**backend/app/services/ytdlp_service.py**:
```python
# 修改这一行
TEMP_DIR = str(PROJECT_ROOT / "downloads")

# 改为你想要的目录，例如：
TEMP_DIR = "/path/to/your/download/directory"
```

**backend/app/services/download_manager.py**:
```python
# 同样修改这一行
TEMP_DIR = str(PROJECT_ROOT / "downloads")
```

### 修改清理时间
**backend/app/services/download_manager.py**:
```python
# 修改清理间隔（秒）
CLEANUP_INTERVAL = 3600  # 1小时

# 修改任务过期时间（秒）
TASK_EXPIRY = 3600  # 1小时
```

## 🔄 兼容性

### 操作系统
- ✅ macOS
- ✅ Linux
- ✅ Windows

### 路径处理
使用 `pathlib.Path` 确保跨平台兼容：
```python
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEMP_DIR = str(PROJECT_ROOT / "downloads")
```

## ⚠️ 注意事项

1. **磁盘空间**: 确保有足够的磁盘空间
2. **权限**: 确保应用有写入downloads目录的权限
3. **备份**: downloads目录不会被Git跟踪，注意备份重要文件
4. **清理**: 定期检查并清理downloads目录

## 📚 相关文档

- `YTDLP_INTEGRATION_PROGRESS.md` - yt-dlp集成进度
- `FRONTEND_YTDLP_INTEGRATION.md` - 前端集成说明
- `QUICK_START_YTDLP.md` - 快速开始指南

## ✨ 总结

成功将下载目录从 `/tmp/ytdlp_downloads` 修改为项目根目录下的 `downloads/` 文件夹：

- ✅ 修改了ytdlp_service.py
- ✅ 修改了download_manager.py
- ✅ 创建了downloads目录
- ✅ 添加到.gitignore
- ✅ 测试通过

用户现在可以在项目的 `downloads/` 目录中找到下载的视频文件！

---

**修改时间**: 2024-12-28  
**状态**: ✅ 完成  
**测试**: ✅ 通过  
**影响**: 所有视频下载功能
