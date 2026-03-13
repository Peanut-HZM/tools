# Cursor 历史工具 P2/P3 阶段实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成 Cursor 对话历史工具的高级功能，包括标签系统、批量操作、主题切换和布局优化。

**Architecture:**
- 前端：基于现有 CursorHistory.tsx 组件扩展，增加标签管理、批量选择、主题切换功能
- 后端：新增标签表支持，扩展现有 API 支持批量操作，添加主题配置存储
- 数据流：前端状态管理 → API 调用 → 后端服务 → SQLite 存储

**Tech Stack:**
- 前端：React 18, TypeScript, Tailwind CSS, Zustand, react-window
- 后端：FastAPI, SQLAlchemy, SQLite
- 新增依赖：flexsearch（搜索优化），jszip（批量导出）

---

## P2 阶段 - 高级功能

### Task 1: 标签系统 - 后端数据模型

**Files:**
- Modify: `backend/app/models/cursor_history_models.py:190-191`
- Create: `backend/app/models/cursor_tag.py`
- Modify: `backend/app/routes/cursor_history.py`
- Test: 手动测试 API 端点

**Step 1: 创建标签数据模型**

创建 `backend/app/models/cursor_tag.py`:
```python
"""Cursor 标签数据模型"""
from pydantic import BaseModel
from typing import Optional, List


class CursorTag(BaseModel):
    """标签信息"""
    id: Optional[int] = None
    composer_id: str
    tag_name: str
    created_at: Optional[str] = None


class TagAddRequest(BaseModel):
    """添加标签请求"""
    composer_id: str
    tag_name: str


class TagRemoveRequest(BaseModel):
    """移除标签请求"""
    composer_id: str
    tag_name: str


class TagListResponse(BaseModel):
    """标签列表响应"""
    tags: List[CursorTag]
    total: int


class TagBulkRequest(BaseModel):
    """批量操作请求"""
    composer_ids: List[str]
    tag_name: Optional[str] = None
```

**Step 2: 运行类型检查验证模型定义**

```bash
cd backend
python -c "from app.models.cursor_tag import CursorTag, TagAddRequest; print('OK')"
```
预期输出：`OK`

**Step 3: 添加标签服务层**

创建 `backend/app/services/cursor_tag_service.py`:
```python
"""Cursor 标签服务"""
import sqlite3
import logging
from typing import List, Optional
from app.models.cursor_tag import CursorTag

logger = logging.getLogger(__name__)
DB_PATH = "cursor_history.db"


class CursorTagService:
    """标签服务类"""

    @staticmethod
    def init_db():
        """初始化标签表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursor_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composer_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(composer_id, tag_name)
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def add_tag(composer_id: str, tag_name: str) -> bool:
        """添加标签"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO cursor_tags (composer_id, tag_name) VALUES (?, ?)",
                (composer_id, tag_name)
            )
            conn.commit()
            added = cursor.rowcount > 0
            conn.close()
            return added
        except Exception as e:
            logger.error(f"添加标签失败：{e}")
            return False

    @staticmethod
    def remove_tag(composer_id: str, tag_name: str) -> bool:
        """移除标签"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cursor_tags WHERE composer_id = ? AND tag_name = ?",
                (composer_id, tag_name)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except Exception as e:
            logger.error(f"移除标签失败：{e}")
            return False

    @staticmethod
    def get_tags(composer_id: str) -> List[CursorTag]:
        """获取会话的所有标签"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM cursor_tags WHERE composer_id = ? ORDER BY created_at DESC",
                (composer_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [CursorTag(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"获取标签失败：{e}")
            return []

    @staticmethod
    def get_all_tags() -> List[str]:
        """获取所有不重复的标签名"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT tag_name FROM cursor_tags ORDER BY tag_name")
            rows = cursor.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取所有标签失败：{e}")
            return []

    @staticmethod
    def search_by_tag(tag_name: str) -> List[str]:
        """根据标签搜索会话 ID 列表"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT composer_id FROM cursor_tags WHERE tag_name = ?",
                (tag_name,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"按标签搜索失败：{e}")
            return []

# 初始化表
CursorTagService.init_db()
```

**Step 4: 验证服务层代码**

```bash
cd backend
python -c "from app.services.cursor_tag_service import CursorTagService; CursorTagService.init_db(); print('DB initialized')"
```
预期输出：`DB initialized`

**Step 5: 添加标签 API 路由**

修改 `backend/app/routes/cursor_history.py`，在文件末尾添加:
```python
@router.post("/tags")
async def add_tag(request: TagAddRequest):
    """添加标签到会话"""
    logger.info(f"添加标签：{request.composer_id} - {request.tag_name}")
    try:
        success = CursorTagService.add_tag(request.composer_id, request.tag_name)
        return {"success": success, "message": "标签添加成功" if success else "标签已存在"}
    except Exception as e:
        logger.error(f"添加标签失败：{e}")
        raise HTTPException(status_code=500, detail=f"添加标签失败：{str(e)}")


@router.delete("/tags")
async def remove_tag(request: TagRemoveRequest):
    """移除会话标签"""
    logger.info(f"移除标签：{request.composer_id} - {request.tag_name}")
    try:
        success = CursorTagService.remove_tag(request.composer_id, request.tag_name)
        return {"success": success, "message": "标签移除成功" if success else "标签不存在"}
    except Exception as e:
        logger.error(f"移除标签失败：{e}")
        raise HTTPException(status_code=500, detail=f"移除标签失败：{str(e)}")


@router.get("/tags/{composer_id}")
async def get_tags(composer_id: str):
    """获取会话的所有标签"""
    logger.info(f"获取标签：{composer_id}")
    try:
        tags = CursorTagService.get_tags(composer_id)
        return TagListResponse(tags=tags, total=len(tags))
    except Exception as e:
        logger.error(f"获取标签失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取标签失败：{str(e)}")


@router.get("/tags")
async def get_all_tags():
    """获取所有标签"""
    logger.info("获取所有标签")
    try:
        all_tags = CursorTagService.get_all_tags()
        return {"tags": all_tags, "total": len(all_tags)}
    except Exception as e:
        logger.error(f"获取所有标签失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取所有标签失败：{str(e)}")


@router.get("/sessions/by-tag/{tag_name}")
async def get_sessions_by_tag(tag_name: str):
    """根据标签获取会话列表"""
    logger.info(f"按标签获取会话：{tag_name}")
    try:
        composer_ids = CursorTagService.search_by_tag(tag_name)
        return {"composer_ids": composer_ids, "total": len(composer_ids)}
    except Exception as e:
        logger.error(f"按标签获取会话失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")
```

**Step 6: 更新模型导入**

修改 `backend/app/models/cursor_history_models.py`，在文件末尾添加导入：
```python
# 在文件顶部添加
from .cursor_tag import CursorTag, TagAddRequest, TagRemoveRequest, TagListResponse, TagBulkRequest
```

**Step 7: 验证后端代码编译**

```bash
cd backend
python -m py_compile app/routes/cursor_history.py
```
预期输出：无错误

**Step 8: 重启后端服务并测试 API**

```bash
cd backend
uvicorn app.main:app --reload --port 19092
```
然后访问 `http://localhost:19092/docs` 验证新的标签 API 端点。

**Step 9: 提交**

```bash
git add backend/app/models/cursor_tag.py backend/app/services/cursor_tag_service.py backend/app/routes/cursor_history.py backend/app/models/cursor_history_models.py
git commit -m "feat: 添加 Cursor 标签系统后端支持"
```

---

### Task 2: 标签系统 - 前端 UI

**Files:**
- Modify: `frontend/src/components/Tools/CursorHistory/CursorHistory.tsx`
- Create: `frontend/src/components/Tools/CursorHistory/TagManager.tsx`
- Create: `frontend/src/components/Tools/CursorHistory/TagFilter.tsx`

**Step 1: 创建标签管理器组件**

创建 `frontend/src/components/Tools/CursorHistory/TagManager.tsx`:
```tsx
/**
 * 标签管理器组件
 * 用于为会话添加/移除标签
 */
import { useState, useEffect } from 'react';
import { Tag, X, Plus } from 'lucide-react';
import { API_BASE_URL } from '../../../config/api';
import { useToast } from '../../../hooks/useToast';

interface TagManagerProps {
  composerId: string;
  onUpdate?: () => void;
}

interface TagItem {
  id: number;
  composer_id: string;
  tag_name: string;
  created_at: string;
}

const PRESET_TAGS = [
  'Bug 修复',
  '功能设计',
  '代码生成',
  '概念解释',
  '性能优化',
  '重构',
  '测试',
  '文档',
  '其他'
];

export default function TagManager({ composerId, onUpdate }: TagManagerProps) {
  const { toast } = useToast();
  const [tags, setTags] = useState<TagItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [customTag, setCustomTag] = useState('');

  // 加载标签
  useEffect(() => {
    loadTags();
  }, [composerId]);

  const loadTags = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags/${composerId}`);
      const data = await response.json();
      setTags(data.tags || []);
    } catch (error) {
      console.error('加载标签失败:', error);
    }
  };

  const addTag = async (tagName: string) => {
    if (!tagName.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ composer_id: composerId, tag_name: tagName.trim() }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: '标签已添加',
          description: `已添加标签：${tagName}`,
        });
        await loadTags();
        onUpdate?.();
      } else {
        toast({
          title: '添加失败',
          description: result.message || '标签可能已存在',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('添加标签失败:', error);
      toast({
        title: '添加失败',
        description: '请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
      setShowAddPanel(false);
      setCustomTag('');
    }
  };

  const removeTag = async (tagName: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ composer_id: composerId, tag_name: tagName }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: '标签已移除',
          description: `已移除标签：${tagName}`,
        });
        await loadTags();
        onUpdate?.();
      }
    } catch (error) {
      console.error('移除标签失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-1">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded text-xs"
          >
            <Tag className="w-3 h-3" />
            {tag.tag_name}
            <button
              onClick={() => removeTag(tag.tag_name)}
              className="hover:bg-blue-200 dark:hover:bg-blue-800 rounded p-0.5"
              disabled={loading}
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}

        <button
          onClick={() => setShowAddPanel(!showAddPanel)}
          className="inline-flex items-center gap-1 px-2 py-0.5 border border-dashed border-gray-300 dark:border-gray-600 rounded text-xs text-gray-500 hover:border-blue-400 hover:text-blue-500 transition-colors"
          disabled={loading}
        >
          <Plus className="w-3 h-3" />
          添加标签
        </button>
      </div>

      {showAddPanel && (
        <div className="absolute top-full left-0 mt-1 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 w-64">
          <div className="text-xs text-gray-500 mb-2">选择预设标签或输入自定义标签</div>

          <div className="flex flex-wrap gap-1 mb-3">
            {PRESET_TAGS.map((presetTag) => (
              <button
                key={presetTag}
                onClick={() => addTag(presetTag)}
                className="px-2 py-1 bg-gray-100 dark:bg-gray-700 hover:bg-blue-100 dark:hover:bg-blue-900 rounded text-xs transition-colors"
                disabled={loading || tags.some(t => t.tag_name === presetTag)}
              >
                {presetTag}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={customTag}
              onChange={(e) => setCustomTag(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addTag(customTag)}
              placeholder="自定义标签..."
              className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-xs bg-transparent"
              autoFocus
            />
            <button
              onClick={() => addTag(customTag)}
              className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
              disabled={!customTag.trim() || loading}
            >
              添加
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Step 2: 创建标签筛选组件**

创建 `frontend/src/components/Tools/CursorHistory/TagFilter.tsx`:
```tsx
/**
 * 标签筛选组件
 * 用于按标签筛选会话
 */
import { useState, useEffect } from 'react';
import { Tag, Filter } from 'lucide-react';
import { API_BASE_URL } from '../../../config/api';

interface TagFilterProps {
  onTagSelect?: (tag: string | null) => void;
}

export default function TagFilter({ onTagSelect }: TagFilterProps) {
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTags();
  }, []);

  const loadTags = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/tags`);
      const data = await response.json();
      setTags(data.tags || []);
    } catch (error) {
      console.error('加载标签失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTagClick = (tag: string | null) => {
    setSelectedTag(tag);
    onTagSelect?.(tag);
  };

  if (tags.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="flex items-center gap-1 text-xs text-gray-500">
        <Filter className="w-3 h-3" />
        标签筛选:
      </div>

      <button
        onClick={() => handleTagClick(null)}
        className={`px-2 py-1 rounded text-xs transition-colors ${
          !selectedTag
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
        }`}
      >
        全部
      </button>

      {tags.map((tag) => (
        <button
          key={tag}
          onClick={() => handleTagClick(tag)}
          className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
            selectedTag === tag
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <Tag className="w-3 h-3" />
          {tag}
        </button>
      ))}
    </div>
  );
}
```

**Step 3: 集成标签组件到主组件**

修改 `frontend/src/components/Tools/CursorHistory/CursorHistory.tsx`:

在 imports 部分添加:
```tsx
import TagManager from './TagManager';
import TagFilter from './TagFilter';
```

在状态部分添加:
```tsx
const [selectedFilterTag, setSelectedFilterTag] = useState<string | null>(null);
```

在会话列表区域添加标签显示和筛选:
```tsx
// 在会话列表每一项中添加
<div className="flex items-center justify-between">
  <div className="font-medium truncate">{session.name || '未命名会话'}</div>
  <TagManager composerId={session.composer_id} />
</div>
```

在工具栏区域添加标签筛选:
```tsx
<TagFilter onTagSelect={(tag) => {
  setSelectedFilterTag(tag);
  // 触体会话列表刷新
}} />
```

**Step 4: 验证前端编译**

```bash
cd frontend
npm run build
```
预期输出：构建成功，无错误

**Step 5: 提交**

```bash
git add frontend/src/components/Tools/CursorHistory/TagManager.tsx frontend/src/components/Tools/CursorHistory/TagFilter.tsx frontend/src/components/Tools/CursorHistory/CursorHistory.tsx
git commit -m "feat: 添加标签管理前端组件"
```

---

### Task 3: 批量操作功能

**Files:**
- Modify: `backend/app/routes/cursor_history.py`
- Modify: `frontend/src/components/Tools/CursorHistory/CursorHistory.tsx`
- Create: `frontend/src/components/Tools/CursorHistory/BatchActions.tsx`

**Step 1: 添加批量操作后端 API**

修改 `backend/app/routes/cursor_history.py`，添加批量操作端点:
```python
@router.post("/batch/export")
async def batch_export(request: TagBulkRequest):
    """批量导出会话"""
    logger.info(f"批量导出 {len(request.composer_ids)} 个会话")
    try:
        from app.services.cursor_history_service import CursorHistoryService
        import zipfile
        import io
        import json

        # 创建 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for composer_id in request.composer_ids:
                try:
                    content, filename = CursorHistoryService.export_session(
                        composer_id=composer_id,
                        export_format='markdown',
                        include_code_blocks=True,
                        include_timestamps=True,
                        include_avatars=False,
                    )
                    # 清理文件名
                    safe_filename = "".join(c if c.isalnum() or c in '-_' else '_' for c in filename)
                    zf.writestr(f"{safe_filename}.md", content)
                except Exception as e:
                    logger.error(f"导出会话 {composer_id} 失败：{e}")
                    continue

        zip_buffer.seek(0)
        import base64
        zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')

        return {
            "success": True,
            "data": zip_data,
            "filename": "cursor_sessions_export.zip",
        }
    except Exception as e:
        logger.error(f"批量导出失败：{e}")
        raise HTTPException(status_code=500, detail=f"批量导出失败：{str(e)}")


@router.post("/batch/tags")
async def batch_add_tags(request: TagBulkRequest):
    """批量添加标签"""
    logger.info(f"批量添加标签 {request.tag_name} 到 {len(request.composer_ids)} 个会话")
    try:
        from app.services.cursor_tag_service import CursorTagService

        success_count = 0
        for composer_id in request.composer_ids:
            if CursorTagService.add_tag(composer_id, request.tag_name):
                success_count += 1

        return {
            "success": True,
            "message": f"已为 {success_count} 个会话添加标签",
        }
    except Exception as e:
        logger.error(f"批量添加标签失败：{e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败：{str(e)}")


@router.delete("/batch/favorites")
async def batch_remove_favorites(request: TagBulkRequest):
    """批量移除收藏"""
    logger.info(f"批量移除 {len(request.composer_ids)} 个收藏")
    try:
        import sqlite3
        db_path = "cursor_favorites.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        placeholders = ','.join(['?' for _ in request.composer_ids])
        cursor.execute(f"DELETE FROM cursor_favorites WHERE composer_id IN ({placeholders})", request.composer_ids)

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"已移除 {deleted} 个收藏",
        }
    except Exception as e:
        logger.error(f"批量移除收藏失败：{e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败：{str(e)}")
```

**Step 2: 创建批量操作组件**

创建 `frontend/src/components/Tools/CursorHistory/BatchActions.tsx`:
```tsx
/**
 * 批量操作组件
 */
import { useState } from 'react';
import { Download, Tag, Trash2, X, Check } from 'lucide-react';
import { API_BASE_URL } from '../../../config/api';
import { useToast } from '../../../hooks/useToast';

interface BatchActionsProps {
  selectedIds: string[];
  onClearSelection: () => void;
  onRefresh?: () => void;
}

export default function BatchActions({ selectedIds, onClearSelection, onRefresh }: BatchActionsProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [showTagModal, setShowTagModal] = useState(false);
  const [tagName, setTagName] = useState('');

  const handleExport = async () => {
    if (selectedIds.length === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/batch/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ composer_ids: selectedIds }),
      });

      const result = await response.json();

      if (result.success) {
        // 下载 ZIP 文件
        const link = document.createElement('a');
        link.href = `data:application/zip;base64,${result.data}`;
        link.download = result.filename || 'cursor_sessions.zip';
        link.click();

        toast({
          title: '导出成功',
          description: `已导出 ${selectedIds.length} 个会话`,
        });
        onClearSelection();
      }
    } catch (error) {
      console.error('批量导出失败:', error);
      toast({
        title: '导出失败',
        description: '请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async () => {
    if (!tagName.trim() || selectedIds.length === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/cursor-history/batch/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          composer_ids: selectedIds,
          tag_name: tagName.trim()
        }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: '添加成功',
          description: result.message,
        });
        setShowTagModal(false);
        setTagName('');
        onClearSelection();
        onRefresh?.();
      }
    } catch (error) {
      console.error('批量添加标签失败:', error);
      toast({
        title: '添加失败',
        description: '请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  if (selectedIds.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-4 z-50">
      <span className="text-sm font-medium">
        已选择 {selectedIds.length} 个会话
      </span>

      <div className="flex items-center gap-2">
        <button
          onClick={handleExport}
          className="p-2 hover:bg-gray-700 rounded transition-colors"
          title="批量导出"
          disabled={loading}
        >
          <Download className="w-4 h-4" />
        </button>

        <button
          onClick={() => setShowTagModal(true)}
          className="p-2 hover:bg-gray-700 rounded transition-colors"
          title="批量添加标签"
          disabled={loading}
        >
          <Tag className="w-4 h-4" />
        </button>

        <button
          onClick={onClearSelection}
          className="p-2 hover:bg-gray-700 rounded transition-colors"
          title="取消选择"
          disabled={loading}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {showTagModal && (
        <div className="absolute bottom-full left-0 mb-2 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">输入标签名称</div>
          <div className="flex gap-2">
            <input
              type="text"
              value={tagName}
              onChange={(e) => setTagName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
              placeholder="标签名称..."
              className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm bg-transparent"
              autoFocus
            />
            <button
              onClick={handleAddTag}
              className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
              disabled={!tagName.trim()}
            >
              确定
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Step 3: 集成批量选择功能**

修改 `CursorHistory.tsx`，在会话列表中添加多选框:
```tsx
// 添加状态
const [selectedSessionIds, setSelectedSessionIds] = useState<string[]>([]);
const [selectMode, setSelectMode] = useState(false);

// 切换选择模式
const toggleSelectMode = () => {
  setSelectMode(!selectMode);
  setSelectedSessionIds([]);
};

// 切换单个会话选择
const toggleSessionSelect = (composerId: string) => {
  setSelectedSessionIds(prev =>
    prev.includes(composerId)
      ? prev.filter(id => id !== composerId)
      : [...prev, composerId]
  );
};

// 全选
const selectAll = () => {
  setSelectedSessionIds(sessions.map(s => s.composer_id));
};
```

**Step 4: 验证编译**

```bash
cd frontend
npm run build
```

**Step 5: 提交**

```bash
git add backend/app/routes/cursor_history.py frontend/src/components/Tools/CursorHistory/BatchActions.tsx frontend/src/components/Tools/CursorHistory/CursorHistory.tsx
git commit -m "feat: 添加批量操作功能"
```

---

## P3 阶段 - 个性化功能

### Task 4: 主题切换功能

**Files:**
- Modify: `frontend/src/index.css` (或主样式文件)
- Modify: `frontend/src/components/Tools/CursorHistory/CursorHistory.tsx`
- Create: `frontend/src/themes/cursorThemes.ts`

**Step 1: 创建主题配置**

创建 `frontend/src/themes/cursorThemes.ts`:
```tsx
/**
 * Cursor 历史工具主题配置
 */

export interface Theme {
  id: string;
  name: string;
  colors: {
    primary: string;
    primaryLight: string;
    primaryDark: string;
    background: string;
    surface: string;
    surfaceElevated: string;
    text: string;
    textSecondary: string;
    border: string;
    userMessageBg: string;
    aiMessageBg: string;
    accent: string;
  };
}

export const themes: Theme[] = [
  {
    id: 'deep-space',
    name: '深空紫',
    colors: {
      primary: '#8B5CF6',
      primaryLight: '#A78BFA',
      primaryDark: '#7C3AED',
      background: '#0F0A1F',
      surface: '#1A142D',
      surfaceElevated: '#251E3A',
      text: '#F5F3FF',
      textSecondary: '#C4B5FD',
      border: '#4C1D95',
      userMessageBg: '#7C3AED',
      aiMessageBg: '#1A142D',
      accent: '#F472B6',
    },
  },
  {
    id: 'ocean-blue',
    name: '海洋蓝',
    colors: {
      primary: '#0EA5E9',
      primaryLight: '#38BDF8',
      primaryDark: '#0284C7',
      background: '#082F49',
      surface: '#0C4A6E',
      surfaceElevated: '#155E75',
      text: '#F0F9FF',
      textSecondary: '#BAE6FD',
      border: '#075985',
      userMessageBg: '#0284C7',
      aiMessageBg: '#0C4A6E',
      accent: '#2DD4BF',
    },
  },
  {
    id: 'forest-green',
    name: '森林绿',
    colors: {
      primary: '#22C55E',
      primaryLight: '#4ADE80',
      primaryDark: '#16A34A',
      background: '#052E16',
      surface: '#14532D',
      surfaceElevated: '#166534',
      text: '#F0FDF4',
      textSecondary: '#BBF7D0',
      border: '#15803D',
      userMessageBg: '#16A34A',
      aiMessageBg: '#14532D',
      accent: '#EAB308',
    },
  },
];

export const defaultTheme = themes[0];

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const colors = theme.colors;

  root.style.setProperty('--theme-primary', colors.primary);
  root.style.setProperty('--theme-primary-light', colors.primaryLight);
  root.style.setProperty('--theme-primary-dark', colors.primaryDark);
  root.style.setProperty('--theme-background', colors.background);
  root.style.setProperty('--theme-surface', colors.surface);
  root.style.setProperty('--theme-surface-elevated', colors.surfaceElevated);
  root.style.setProperty('--theme-text', colors.text);
  root.style.setProperty('--theme-text-secondary', colors.textSecondary);
  root.style.setProperty('--theme-border', colors.border);
  root.style.setProperty('--theme-user-message-bg', colors.userMessageBg);
  root.style.setProperty('--theme-ai-message-bg', colors.aiMessageBg);
  root.style.setProperty('--theme-accent', colors.accent);
}

export function getSavedTheme(): Theme | null {
  const savedThemeId = localStorage.getItem('cursor-theme');
  if (savedThemeId) {
    return themes.find(t => t.id === savedThemeId) || null;
  }
  return null;
}

export function saveTheme(themeId: string) {
  localStorage.setItem('cursor-theme', themeId);
}
```

**Step 2: 添加 CSS 变量**

修改 `frontend/src/index.css`，在 `:root` 中添加:
```css
:root {
  /* 主题变量 */
  --theme-primary: #8B5CF6;
  --theme-primary-light: #A78BFA;
  --theme-primary-dark: #7C3AED;
  --theme-background: #0F0A1F;
  --theme-surface: #1A142D;
  --theme-surface-elevated: #251E3A;
  --theme-text: #F5F3FF;
  --theme-text-secondary: #C4B5FD;
  --theme-border: #4C1D95;
  --theme-user-message-bg: #7C3AED;
  --theme-ai-message-bg: #1A142D;
  --theme-accent: #F472B6;
}
```

**Step 3: 创建主题切换组件**

创建 `frontend/src/components/Tools/CursorHistory/ThemeSwitcher.tsx`:
```tsx
/**
 * 主题切换组件
 */
import { useState, useEffect } from 'react';
import { Palette, Check } from 'lucide-react';
import { themes, applyTheme, getSavedTheme, saveTheme } from '../../../themes/cursorThemes';

export default function ThemeSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(() => getSavedTheme()?.id || 'deep-space');

  useEffect(() => {
    const savedTheme = getSavedTheme();
    if (savedTheme) {
      applyTheme(savedTheme);
      setCurrentTheme(savedTheme.id);
    }
  }, []);

  const handleThemeChange = (themeId: string) => {
    const theme = themes.find(t => t.id === themeId);
    if (theme) {
      applyTheme(theme);
      saveTheme(themeId);
      setCurrentTheme(themeId);
      setIsOpen(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
        title="切换主题"
      >
        <Palette className="w-4 h-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 w-48">
          <div className="text-xs text-gray-500 mb-2">选择主题</div>

          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => handleThemeChange(theme.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded text-sm mb-1 transition-colors ${
                currentTheme === theme.id
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <span>{theme.name}</span>
              {currentTheme === theme.id && <Check className="w-4 h-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 4: 集成主题切换器**

修改 `CursorHistory.tsx`，在工具栏中添加:
```tsx
import ThemeSwitcher from './ThemeSwitcher';

// 在工具栏中添加
<ThemeSwitcher />
```

**Step 5: 验证编译**

```bash
cd frontend
npm run build
```

**Step 6: 提交**

```bash
git add frontend/src/themes/cursorThemes.ts frontend/src/components/Tools/CursorHistory/ThemeSwitcher.tsx frontend/src/components/Tools/CursorHistory/CursorHistory.tsx frontend/src/index.css
git commit -m "feat: 添加主题切换功能"
```

---

### Task 5: 布局优化 - 可调节侧边栏

**Files:**
- Modify: `frontend/src/components/Tools/CursorHistory/CursorHistory.tsx`
- Create: `frontend/src/components/Tools/CursorHistory/ResizablePanel.tsx`

**Step 1: 创建可调节面板组件**

创建 `frontend/src/components/Tools/CursorHistory/ResizablePanel.tsx`:
```tsx
/**
 * 可调节宽度面板组件
 */
import { useState, useCallback, useRef } from 'react';

interface ResizablePanelProps {
  children: React.ReactNode;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  storageKey?: string;
}

export default function ResizablePanel({
  children,
  defaultWidth = 280,
  minWidth = 200,
  maxWidth = 500,
  storageKey,
}: ResizablePanelProps) {
  const [width, setWidth] = useState(() => {
    if (storageKey) {
      const saved = localStorage.getItem(storageKey);
      if (saved) return parseInt(saved, 10);
    }
    return defaultWidth;
  });

  const isResizing = useRef(false);

  const startResize = useCallback((e: React.MouseEvent) => {
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const startX = e.clientX;
    const startWidth = width;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!isResizing.current) return;

      const delta = moveEvent.clientX - startX;
      const newWidth = Math.min(Math.max(startWidth + delta, minWidth), maxWidth);
      setWidth(newWidth);

      if (storageKey) {
        localStorage.setItem(storageKey, newWidth.toString());
      }
    };

    const handleMouseUp = () => {
      isResizing.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [width, minWidth, maxWidth, storageKey]);

  return (
    <div className="flex h-full">
      <div style={{ width, flexShrink: 0 }} className="h-full">
        {children}
      </div>
      <div
        onMouseDown={startResize}
        className="w-1 hover:bg-blue-400 cursor-col-resize transition-colors flex items-center justify-center"
      >
        <div className="h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
      </div>
    </div>
  );
}
```

**Step 2: 应用可调节面板**

修改 `CursorHistory.tsx`，将侧边栏包裹在 `ResizablePanel` 中:
```tsx
import ResizablePanel from './ResizablePanel';

// 替换原有的固定宽度侧边栏
<ResizablePanel defaultWidth={280} minWidth={220} maxWidth={450} storageKey="cursor-projects-width">
  {/* 项目列表内容 */}
</ResizablePanel>

<ResizablePanel defaultWidth={300} minWidth={250} maxWidth={500} storageKey="cursor-sessions-width">
  {/* 会话列表内容 */}
</ResizablePanel>
```

**Step 3: 添加全屏模式**

在 `CursorHistory.tsx` 中添加全屏切换功能:
```tsx
const [isFullscreen, setIsFullscreen] = useState(false);

const toggleFullscreen = async () => {
  try {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      await document.exitFullscreen();
      setIsFullscreen(false);
    }
  } catch (error) {
    console.error('全屏切换失败:', error);
  }
};

// 监听全屏状态变化
useEffect(() => {
  const handleFullscreenChange = () => {
    setIsFullscreen(!!document.fullscreenElement);
  };
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
}, []);
```

**Step 4: 在工具栏中添加全屏按钮**

```tsx
<button
  onClick={toggleFullscreen}
  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
  title={isFullscreen ? '退出全屏' : '全屏模式'}
>
  {isFullscreen ? (
    <Minimize className="w-4 h-4" />
  ) : (
    <Maximize className="w-4 h-4" />
  )}
</button>
```

需要从 `lucide-react` 导入 `Maximize` 和 `Minimize` 图标。

**Step 5: 验证编译**

```bash
cd frontend
npm run build
```

**Step 6: 提交**

```bash
git add frontend/src/components/Tools/CursorHistory/ResizablePanel.tsx frontend/src/components/Tools/CursorHistory/CursorHistory.tsx
git commit -m "feat: 添加可调节侧边栏和全屏模式"
```

---

## 验收标准

### P2 阶段验收
- [ ] 标签系统完整可用（添加/移除/筛选）
- [ ] 批量导出功能正常（生成 ZIP 文件）
- [ ] 批量添加标签功能正常
- [ ] 多选 UI 清晰直观

### P3 阶段验收
- [ ] 三种主题切换正常，颜色符合设计
- [ ] 主题保存在本地，刷新后保持
- [ ] 侧边栏可调节宽度，范围 200-500px
- [ ] 全屏模式正常工作
- [ ] 布局设置保存在本地

### 性能指标
- [ ] 标签筛选响应时间 < 200ms
- [ ] 批量导出 10 个会话时间 < 5 秒
- [ ] 主题切换无闪烁
- [ ] 拖拽调节流畅（>30fps）

---

## 注意事项

1. **数据库迁移**: 首次运行标签功能时需要初始化 `cursor_tags` 表
2. **向后兼容**: 所有新功能需要保持与现有功能的兼容
3. **错误处理**: 所有 API 调用需要有完善的错误处理
4. **类型安全**: 前端 TypeScript 类型定义需要完整
5. **样式隔离**: 主题变量使用 CSS custom properties，避免全局污染
