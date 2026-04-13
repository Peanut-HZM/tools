# 工具管理增强 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 后台管理工具管理增加行编辑、分页搜索、图标管理功能；PC 端和移动端根据开关控制展示，图标支持自定义上传。

**Architecture:** 数据库新增 3 字段 → 后端 Service 层增删改查 + 分页搜索 → 新增路由（PUT 编辑、图标上传、分页查询）→ 管理后台弹窗编辑器 + 分页组件 → 前端首页和小程序按 platform 过滤 + 图标优先用自定义。

**Tech Stack:** Python FastAPI, PostgreSQL, Aliyun OSS, React + TypeScript (Tailwind CSS), Taro + React (小程序)

---

### Task 1: 数据库 — 新增字段

**Files:**
- Modify: `backend/app/services/tools_service.py`（第 45-58 行，建表 SQL 新增字段）

**Step 1: 修改建表 SQL**

在 `tools` 表建表语句中，`created_at` 之前新增 3 个字段：

```python
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tools (
                        id VARCHAR(50) PRIMARY KEY,
                        title VARCHAR(100) NOT NULL,
                        description TEXT,
                        icon VARCHAR(50),
                        icon_color VARCHAR(50),
                        category VARCHAR(50),
                        status VARCHAR(20) DEFAULT 'online',
                        usage_count INTEGER DEFAULT 0,
                        rating FLOAT DEFAULT 5.0,
                        sort_order INT DEFAULT 0,
                        custom_icon_url VARCHAR(500) DEFAULT NULL,
                        show_pc BOOLEAN DEFAULT TRUE,
                        show_mobile BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
```

注意：`CREATE TABLE IF NOT EXISTS` 对已存在的表不会新增列。需要在 `_init_db` 方法末尾（`conn.commit()` 之前）添加迁移逻辑：

```python
                # 迁移：为已有 tools 表新增字段
                cur.execute("""
                    ALTER TABLE tools
                    ADD COLUMN IF NOT EXISTS custom_icon_url VARCHAR(500) DEFAULT NULL
                """)
                cur.execute("""
                    ALTER TABLE tools
                    ADD COLUMN IF NOT EXISTS show_pc BOOLEAN DEFAULT TRUE
                """)
                cur.execute("""
                    ALTER TABLE tools
                    ADD COLUMN IF NOT EXISTS show_mobile BOOLEAN DEFAULT TRUE
                """)
```

**Step 2: 修改 Seed 逻辑**

在第 102-122 行的 seed `INSERT` 语句中，新增 3 个字段的默认值（但 ON CONFLICT 不更新它们）：

将第 103-111 行的 SQL 替换为：

```python
                    cur.execute(
                        """
                        INSERT INTO tools (id, title, description, icon, icon_color, category, usage_count, rating, custom_icon_url, show_pc, show_mobile)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, TRUE, TRUE)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            icon = EXCLUDED.icon,
                            icon_color = EXCLUDED.icon_color,
                            category = EXCLUDED.category,
                            rating = EXCLUDED.rating
                    """,
```

**Step 3: 修改 `_row_to_tool` 方法**

第 442-459 行，新增字段映射：

```python
        return Tool(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            icon=row["icon"],
            iconColor=row["icon_color"],
            category=row["category"],
            usageCount=str(row["usage_count"]),
            rating=row["rating"],
            status=row.get("status", "online"),
            custom_icon_url=row.get("custom_icon_url"),
            show_pc=row.get("show_pc", True),
            show_mobile=row.get("show_mobile", True),
        )
```

**Step 4: 验证语法**

Run: `cd backend && python -m py_compile app/services/tools_service.py`
Expected: 无输出

**Step 5: 提交**

```bash
git add backend/app/services/tools_service.py
git commit -m "feat(tool-mgmt): 数据库新增 custom_icon_url, show_pc, show_mobile 字段"
```

---

### Task 2: 后端模型 — 更新 Pydantic 模式

**Files:**
- Modify: `backend/app/models/tool_models.py`

**Step 1: 更新 Tool 模型**

```python
class Tool(BaseModel):
    id: str
    icon: str
    iconColor: str
    title: str
    description: str
    rating: float
    usageCount: str
    category: str
    status: str = "online"
    sort_order: int = 0
    custom_icon_url: Optional[str] = None
    show_pc: bool = True
    show_mobile: bool = True
    created_at: Optional[str] = None
```

**Step 2: 新增 ToolUpdateRequest 模型**

```python
class ToolUpdateRequest(BaseModel):
    """行编辑更新请求，所有字段可选"""
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    iconColor: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    show_pc: Optional[bool] = None
    show_mobile: Optional[bool] = None
```

**Step 3: 新增分页响应模型**

```python
class ToolsPaginatedResponse(BaseModel):
    tools: List[Tool]
    total: int
    page: int
    page_size: int
    total_pages: int
```

**Step 3b: 更新 `__init__.py` 导出**

在 `backend/app/models/__init__.py` 第 9 行（`CategoryResponse`）之后新增：

```python
from app.models.tool_models import (
    Tool,
    Category,
    ToolCreateRequest,
    CategoryCreateRequest,
    ToolsResponse,
    SearchResponse,
    CategoryResponse,
    ToolUpdateRequest,        # 新增
    ToolsPaginatedResponse,   # 新增
)
```

**Step 4: 验证语法**

Run: `cd backend && python -m py_compile app/models/tool_models.py`
Expected: 无输出

**Step 5: 提交**

```bash
git add backend/app/models/tool_models.py
git commit -m "feat(tool-mgmt): 更新 Tool 模型，新增 ToolUpdateRequest 和分页响应"
```

---

### Task 3: 后端服务 — 增删改查 + 分页搜索 + 图标上传

**Files:**
- Modify: `backend/app/services/tools_service.py`

**Step 1: 新增 `update_tool` 方法（完整更新）**

在 `update_tool_status` 方法之后新增：

```python
    def update_tool(self, tool_id: str, data: dict) -> Optional[Tool]:
        """完整更新工具信息（行编辑）"""
        conn = None
        try:
            # 校验分类是否存在（如果提供了新分类）
            if "category" in data and data["category"]:
                cat_conn = get_db_connection()
                try:
                    with cat_conn.cursor() as cur:
                        cur.execute("SELECT id FROM tool_categories WHERE name = %s AND deleted = FALSE", (data["category"],))
                        if not cur.fetchone():
                            raise ValueError(f"分类不存在: {data['category']}")
                finally:
                    cat_conn.close()

            # 构建动态 UPDATE 语句
            updates = []
            params = []
            for field in ["title", "description", "icon", "icon_color", "category", "status", "sort_order"]:
                if field in data:
                    updates.append(f"{field} = %s")
                    params.append(data[field])

            # Boolean 字段特殊处理
            if "show_pc" in data:
                updates.append("show_pc = %s")
                params.append(data["show_pc"])
            if "show_mobile" in data:
                updates.append("show_mobile = %s")
                params.append(data["show_mobile"])
            if "custom_icon_url" in data:
                updates.append("custom_icon_url = %s")
                params.append(data["custom_icon_url"])

            if not updates:
                return None

            params.append(tool_id)

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE tools SET {', '.join(updates)} WHERE id = %s RETURNING *",
                    params
                )
                row = cur.fetchone()
                conn.commit()
                if row:
                    return self._row_to_tool(row)
                return None
        except Exception as e:
            logger.error(f"Error updating tool {tool_id}: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
```

**Step 2: 新增 `get_tools_paginated` 方法**

```python
    def get_tools_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "title",
        sort_order: str = "asc",
        show_pc: Optional[bool] = None,
        show_mobile: Optional[bool] = None,
    ) -> dict:
        """分页查询工具，支持搜索、筛选、排序"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # 构建 WHERE 条件
                conditions = []
                params = []

                if search:
                    conditions.append("(LOWER(title) LIKE LOWER(%s) OR LOWER(description) LIKE LOWER(%s))")
                    params.extend([f"%{search}%", f"%{search}%"])

                if status:
                    conditions.append("status = %s")
                    params.append(status)

                if category:
                    conditions.append("category = %s")
                    params.append(category)

                if show_pc is not None:
                    conditions.append("show_pc = %s")
                    params.append(show_pc)

                if show_mobile is not None:
                    conditions.append("show_mobile = %s")
                    params.append(show_mobile)

                where_clause = " AND ".join(conditions) if conditions else "TRUE"

                # 排序字段白名单
                allowed_sort = {"title", "status", "category", "rating", "usage_count", "created_at"}
                if sort_by not in allowed_sort:
                    sort_by = "title"
                if sort_order not in ("asc", "desc"):
                    sort_order = "asc"

                # 总数
                cur.execute(f"SELECT COUNT(*) FROM tools WHERE {where_clause}", params)
                total = cur.fetchone()["count"]

                # 分页
                offset = (page - 1) * page_size
                cur.execute(
                    f"SELECT * FROM tools WHERE {where_clause} ORDER BY {sort_by} {sort_order} LIMIT %s OFFSET %s",
                    params + [page_size, offset]
                )
                rows = cur.fetchall()
                tools = [self._row_to_tool(row) for row in rows]

                total_pages = (total + page_size - 1) // page_size

                return {
                    "tools": tools,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }
        except Exception as e:
            logger.error(f"Error paginating tools: {e}")
            return {"tools": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 0}
        finally:
            if conn:
                conn.close()
```

**Step 3: 新增图标上传方法**

```python
    def upload_tool_icon(self, tool_id: str, content: bytes, filename: str) -> Optional[str]:
        """上传工具图标到 OSS，上传前先删除旧图标"""
        from app.services.oss_service import oss_service
        from io import BytesIO

        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT id, custom_icon_url FROM tools WHERE id = %s", (tool_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Tool {tool_id} not found")

                # 删除旧 OSS 图标（如果存在）
                old_url = row[1]
                if old_url:
                    # 从 URL 提取 object_name（格式：https://bucket.endpoint/tools/icons/xxx.png）
                    old_object_name = old_url.split("/", 3)[-1] if "/" in old_url else None
                    if old_object_name:
                        oss_service.delete_file(old_object_name)
                        logger.info(f"Deleted old icon for {tool_id}: {old_object_name}")
            conn.close()
            conn = None

            # 确定文件扩展名
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
            if ext not in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
                raise ValueError(f"不支持的文件类型: {ext}")

            object_name = f"tools/icons/{tool_id}.{ext}"

            # 上传到 OSS（oss_service.upload_file 接受 BytesIO）
            url = oss_service.upload_file(
                object_name=object_name,
                data=BytesIO(content),
                size=len(content),
                content_type=f"image/{ext}",
                uploaded_by="admin"
            )

            if not url:
                raise ValueError("OSS 上传失败")

            # 更新数据库
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tools SET custom_icon_url = %s WHERE id = %s",
                    (url, tool_id)
                )
                conn.commit()

            return url
        except Exception as e:
            logger.error(f"Error uploading tool icon for {tool_id}: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    def delete_tool_icon(self, tool_id: str) -> bool:
        """删除工具自定义图标"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tools SET custom_icon_url = NULL WHERE id = %s",
                    (tool_id,)
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting tool icon for {tool_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
```

**Step 4: 新增 `get_tools_for_platform` 方法**

```python
    def get_tools_for_platform(self, platform: str, category: Optional[str] = None) -> List[Tool]:
        """按平台获取在线工具，支持分类过滤（参数化查询防止 SQL 注入）"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                base_sql = "SELECT * FROM tools WHERE status = 'online'"
                params: list = []

                if platform == "pc":
                    base_sql += " AND show_pc = TRUE"
                elif platform == "mobile":
                    base_sql += " AND show_mobile = TRUE"

                if category and category != "全部工具":
                    base_sql += " AND category = %s"
                    params.append(category)

                base_sql += " ORDER BY category, title"
                cur.execute(base_sql, params)

                rows = cur.fetchall()
                return [self._row_to_tool(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching tools for platform {platform}: {e}")
            return []
        finally:
            if conn:
                conn.close()
```

**Step 5: 验证语法**

Run: `cd backend && python -m py_compile app/services/tools_service.py`
Expected: 无输出

**Step 6: 提交**

```bash
git add backend/app/services/tools_service.py
git commit -m "feat(tool-mgmt): Service 层新增编辑、分页搜索、图标上传方法"
```

---

### Task 4: 后端路由 — 新增编辑、分页、图标上传接口

**Files:**
- Modify: `backend/app/routes/admin.py`
- Modify: `backend/app/routes/tools.py`

**Step 1: 修改 admin.py 工具路由**

在 `admin.py` 第 157-173 行，替换原有工具路由：

```python
# ==================== Tool Management ====================

@router.get("/tools", response_model=dict)
async def list_tools_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(online|offline)$"),
    category: Optional[str] = Query(None),
    sort_by: str = Query("title"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    show_pc: Optional[bool] = Query(None),
    show_mobile: Optional[bool] = Query(None),
    admin_user: UserResponse = Depends(get_admin_user),
):
    """分页查询工具，支持搜索、筛选、排序"""
    return tools_service.get_tools_paginated(
        page=page, page_size=page_size, search=search, status=status,
        category=category, sort_by=sort_by, sort_order=sort_order,
        show_pc=show_pc, show_mobile=show_mobile,
    )

@router.put("/tools/{tool_id}", response_model=Tool)
async def update_tool(
    tool_id: str,
    data: ToolUpdateRequest,
    admin_user: UserResponse = Depends(get_admin_user),
):
    """行编辑：完整更新工具信息"""
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供更新数据")
    result = tools_service.update_tool(tool_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="工具不存在")
    return result

@router.post("/tools/{tool_id}/icon", response_model=dict)
async def upload_tool_icon(
    tool_id: str,
    file: UploadFile = File(...),
    admin_user: UserResponse = Depends(get_admin_user),
):
    """上传工具自定义图标"""
    # 验证文件类型
    allowed_types = {"image/png", "image/jpeg", "image/gif", "image/svg+xml", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")

    # 验证大小（最大 2MB）
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 2MB")

    url = tools_service.upload_tool_icon(tool_id, content, file.filename or "icon.png")
    return {"url": url}

@router.delete("/tools/{tool_id}/icon", response_model=bool)
async def delete_tool_icon(
    tool_id: str,
    admin_user: UserResponse = Depends(get_admin_user),
):
    """删除工具自定义图标"""
    return tools_service.delete_tool_icon(tool_id)
```

需要在 admin.py 顶部添加必要的 import：

```python
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, UploadFile, File
```

并导入 `ToolUpdateRequest`（在 `from app.models import ...` 行添加）：

将第 14 行 `from app.models import Tool` 改为：

```python
from app.models import Tool, ToolUpdateRequest
```

**Step 2: 修改 tools.py 公共接口**

修改 `/tools` 接口，新增 `platform` 查询参数：

将第 46-50 行替换为：

```python
@router.get("/tools", response_model=ToolsResponse)
def get_tools(
    platform: Optional[str] = Query(None, description="平台过滤: pc 或 mobile"),
    category: Optional[str] = Query(None, description="分类过滤")
):
    """获取所有工具（支持 platform 和 category 过滤）"""
    tools = tools_service.get_tools_for_platform(platform, category)
    return ToolsResponse(tools=tools)
```

在 `tools.py` 顶部添加 import：

```python
from typing import List, Optional
```

**Step 3: 验证语法**

Run: `cd backend && python -m py_compile app/routes/admin.py && python -m py_compile app/routes/tools.py`
Expected: 无输出

**Step 4: 提交**

```bash
git add backend/app/routes/admin.py backend/app/routes/tools.py
git commit -m "feat(tool-mgmt): 新增行编辑、分页搜索、图标上传、platform 过滤接口"
```

---

### Task 5: 前端类型 — 更新 Tool 类型定义

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/adminApi.ts`

**Step 1: 更新 types/index.ts 的 Tool 接口**

在第 19 行 `category: string;` 之后新增：

```typescript
  custom_icon_url?: string;
  show_pc?: boolean;
  show_mobile?: boolean;
```

**Step 2: 更新 adminApi.ts 的 Tool 接口**

在第 109 行 `status: string;` 之后新增：

```typescript
    custom_icon_url?: string;
    show_pc?: boolean;
    show_mobile?: boolean;
```

**Step 3: 新增分页相关类型和 API 函数**

在 `adminApi.ts` 末尾新增：

```typescript
export interface ToolsPaginatedResponse {
    tools: Tool[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface ToolsListParams {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    category?: string;
    sort_by?: string;
    sort_order?: string;
    show_pc?: boolean;
    show_mobile?: boolean;
}

export async function listToolsPaginated(params?: ToolsListParams): Promise<ToolsPaginatedResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.category) searchParams.append('category', params.category);
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params?.sort_order) searchParams.append('sort_order', params.sort_order);
    if (params?.show_pc !== undefined) searchParams.append('show_pc', String(params.show_pc));
    if (params?.show_mobile !== undefined) searchParams.append('show_mobile', String(params.show_mobile));

    const queryString = searchParams.toString();
    const url = queryString ? `${API_BASE_URL}/tools?${queryString}` : `${API_BASE_URL}/tools`;

    const response = await fetch(url, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to list tools');
    return response.json();
}

export async function updateTool(toolId: string, data: Partial<Tool>): Promise<Tool> {
    const response = await fetch(`${API_BASE_URL}/tools/${toolId}`, {
        method: 'PUT',
        headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update tool');
    return response.json();
}

export async function uploadToolIcon(toolId: string, file: File): Promise<{ url: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/tools/${toolId}/icon`, {
        method: 'POST',
        headers: {
            'Authorization': getAuthHeaders()['Authorization'] || ''
        },
        body: formData
    });
    if (!response.ok) throw new Error('Failed to upload icon');
    return response.json();
}

export async function deleteToolIcon(toolId: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/tools/${toolId}/icon`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete icon');
    return response.json();
}
```

**Step 4: 提交**

```bash
git add frontend/src/types/index.ts frontend/src/api/adminApi.ts
git commit -m "feat(tool-mgmt): 前端新增 Tool 类型字段和分页/编辑 API"
```

---

### Task 6: 管理后台 — 弹窗编辑器 + 图标上传

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx`

**Step 1: 新增状态变量**

在第 18 行之后、`fetchData` 之前新增：

```typescript
  // Tool Edit Modal State
  const [editingTool, setEditingTool] = useState<Tool | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toolForm, setToolForm] = useState<Partial<Tool>>({});
  const [iconFile, setIconFile] = useState<File | null>(null);
  const [iconPreview, setIconPreview] = useState<string | null>(null);
  const [uploadingIcon, setUploadingIcon] = useState(false);
  const [saving, setSaving] = useState(false);
```

导入必要的 API：

将第 2 行替换为：

```typescript
import { listToolsPaginated, updateToolStatus, updateTool, uploadToolIcon, deleteToolIcon, Tool, ToolCategory, ToolsListParams } from '../../api/adminApi';
```

**Step 2: 新增弹窗处理函数**

在 `handleStatusChange` 之后新增：

```typescript
  const handleEditTool = (tool: Tool) => {
    setEditingTool(tool);
    setToolForm({ ...tool });
    setIconFile(null);
    setIconPreview(tool.custom_icon_url || null);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingTool(null);
    setToolForm({});
    setIconFile(null);
    setIconPreview(null);
  };

  const handleIconFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 验证大小
    if (file.size > 2 * 1024 * 1024) {
      error('图标文件大小不能超过 2MB');
      return;
    }

    setIconFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => setIconPreview(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleSaveTool = async () => {
    if (!editingTool) return;

    // 表单校验
    if (!toolForm.title?.trim()) {
      error('工具名称不能为空');
      return;
    }

    setSaving(true);
    try {
      // 1. 先保存基本信息
      const updateData: Partial<Tool> = {};
      const fields: (keyof Tool)[] = ['title', 'description', 'icon', 'iconColor', 'category', 'status', 'sort_order', 'show_pc', 'show_mobile'];
      for (const field of fields) {
        if (toolForm[field] !== undefined && toolForm[field] !== editingTool[field]) {
          (updateData as any)[field] = toolForm[field];
        }
      }

      if (Object.keys(updateData).length > 0) {
        await updateTool(editingTool.id, updateData);
      }

      // 2. 如果有新图标，上传
      if (iconFile) {
        await uploadToolIcon(editingTool.id, iconFile);
      }

      success('工具信息已更新');
      handleCloseModal();
      await fetchData();
    } catch (e: any) {
      error(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteIcon = async () => {
    if (!editingTool) return;
    try {
      await deleteToolIcon(editingTool.id);
      success('图标已删除');
      setIconPreview(null);
      setIconFile(null);
      await fetchData();
    } catch (e) {
      error('删除图标失败');
    }
  };
```

**Step 3: 修改操作列**

在第 153-164 行，操作列替换为：

```tsx
                  <td className="px-6 py-4 flex space-x-3">
                    <button
                      onClick={() => handleEditTool(tool)}
                      className="text-blue-400 hover:text-blue-300 text-sm font-medium"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleStatusChange(tool.id, tool.status)}
                      className={`text-sm font-medium transition-colors ${
                        tool.status === 'online'
                          ? 'text-red-400 hover:text-red-300'
                          : 'text-green-400 hover:text-green-300'
                      }`}
                    >
                      {tool.status === 'online' ? '下线' : '上线'}
                    </button>
                  </td>
```

**Step 4: 新增弹窗 Modal 组件**

在组件末尾（`</div>` 之前、最后返回之前）新增弹窗 JSX：

```tsx
      {/* 编辑工具弹窗 */}
      {isModalOpen && editingTool && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={handleCloseModal}>
          <div className="bg-slate-800 rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <h3 className="text-xl font-semibold text-white mb-6">编辑工具：{editingTool.title}</h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-400 mb-1">工具名称</label>
                  <input
                    type="text"
                    value={toolForm.title || ''}
                    onChange={(e) => setToolForm({...toolForm, title: e.target.value})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-400 mb-1">描述</label>
                  <textarea
                    value={toolForm.description || ''}
                    onChange={(e) => setToolForm({...toolForm, description: e.target.value})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    rows={3}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">分类</label>
                  <select
                    value={toolForm.category || ''}
                    onChange={(e) => setToolForm({...toolForm, category: e.target.value})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.name}>{cat.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">图标颜色</label>
                  <input
                    type="text"
                    value={toolForm.iconColor || ''}
                    onChange={(e) => setToolForm({...toolForm, iconColor: e.target.value})}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                {/* 图标上传区域 */}
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-400 mb-1">自定义图标</label>
                  <div className="bg-slate-700 border border-slate-600 rounded p-4">
                    {iconPreview ? (
                      <div className="flex items-center space-x-4">
                        <img src={iconPreview} alt="图标预览" className="w-16 h-16 rounded object-contain bg-slate-600" />
                        <div className="flex-1">
                          <p className="text-sm text-slate-300">已上传自定义图标</p>
                          <button
                            onClick={handleDeleteIcon}
                            className="text-xs text-red-400 hover:text-red-300 mt-1"
                          >
                            删除自定义图标（恢复默认）
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400 mb-2">当前使用默认 FontAwesome 图标</p>
                    )}
                    <div className="mt-3">
                      <label className="inline-block px-4 py-2 bg-blue-600 text-white text-sm rounded cursor-pointer hover:bg-blue-700">
                        选择文件
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/gif,image/svg+xml,image/webp"
                          onChange={handleIconFileChange}
                          className="hidden"
                        />
                      </label>
                      <span className="text-xs text-slate-500 ml-2">JPG/PNG/SVG，≤2MB</span>
                    </div>
                  </div>
                </div>

                {/* Toggle 开关 */}
                <div className="col-span-2 grid grid-cols-3 gap-4">
                  <div className="flex items-center justify-between bg-slate-700 rounded p-3">
                    <span className="text-sm text-slate-300">PC 端展示</span>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={toolForm.show_pc ?? true}
                        onChange={(e) => setToolForm({...toolForm, show_pc: e.target.checked})}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between bg-slate-700 rounded p-3">
                    <span className="text-sm text-slate-300">移动端展示</span>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={toolForm.show_mobile ?? true}
                        onChange={(e) => setToolForm({...toolForm, show_mobile: e.target.checked})}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between bg-slate-700 rounded p-3">
                    <span className="text-sm text-slate-300">上线状态</span>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={toolForm.status === 'online'}
                        onChange={(e) => setToolForm({...toolForm, status: e.target.checked ? 'online' : 'offline'})}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-slate-700">
                <button
                  onClick={handleCloseModal}
                  className="px-6 py-2 bg-slate-600 text-white rounded hover:bg-slate-500 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleSaveTool}
                  disabled={saving}
                  className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {saving ? '保存中...' : '保存'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
```

**Step 5: 提交**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(tool-mgmt): 管理后台新增弹窗编辑器、图标上传、Toggle 开关"
```

---

### Task 7: 管理后台 — 分页组件 + 高级搜索栏

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx`

**Step 1: 新增分页搜索状态**

在组件文件顶部确保导入 `useCallback`（如果还没有）：

```typescript
import { useState, useEffect, useCallback } from 'react';
```

在现有状态变量中新增：

```typescript
  const [toolPage, setToolPage] = useState(1);
  const [toolPageSize, setToolPageSize] = useState(20);
  const [toolTotal, setToolTotal] = useState(0);
  const [toolTotalPages, setToolTotalPages] = useState(0);
  const [toolSearch, setToolSearch] = useState('');
  const [toolStatusFilter, setToolStatusFilter] = useState<string>('');
  const [toolCategoryFilter, setToolCategoryFilter] = useState<string>('');
  const [toolSortBy, setToolSortBy] = useState('title');
  const [toolSortOrder, setToolSortOrder] = useState<'asc' | 'desc'>('asc');
  const [showPcFilter, setShowPcFilter] = useState<string>('all');
  const [showMobileFilter, setShowMobileFilter] = useState<string>('all');
```

**Step 2: 修改 fetchData 为分页查询**

将 `fetchData` 函数替换为：

```typescript
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: ToolsListParams = {
        page: toolPage,
        page_size: toolPageSize,
        search: toolSearch || undefined,
        status: toolStatusFilter || undefined,
        category: toolCategoryFilter || undefined,
        sort_by: toolSortBy,
        sort_order: toolSortOrder,
        show_pc: showPcFilter === 'all' ? undefined : showPcFilter === 'true',
        show_mobile: showMobileFilter === 'all' ? undefined : showMobileFilter === 'true',
      };

      const [toolsData, categoriesData] = await Promise.all([
        listToolsPaginated(params),
        listCategories()
      ]);

      setTools(toolsData.tools);
      setToolTotal(toolsData.total);
      setToolTotalPages(toolsData.total_pages);
      setCategories(categoriesData);
    } catch (e) {
      error('获取数据失败');
    } finally {
      setLoading(false);
    }
  }, [toolPage, toolPageSize, toolSearch, toolStatusFilter, toolCategoryFilter, toolSortBy, toolSortOrder, showPcFilter, showMobileFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);
```

**注意**：使用 `useCallback` 包裹 `fetchData`，将依赖数组移到 `useCallback` 中。`useEffect` 只依赖 `fetchData` 引用，避免 React lint 警告和潜在的不稳定引用问题。这样当任何一个筛选条件变化时，`fetchData` 引用变化 → `useEffect` 重新执行 → 只发一次请求。

**Step 3: 新增搜索栏**

在工具管理 tab 的 `<table>` 标签之前新增：

```tsx
        {/* 搜索筛选栏 */}
        <div className="bg-slate-800 p-4 rounded-lg mb-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
            <input
              type="text"
              placeholder="搜索名称/描述..."
              value={toolSearch}
              onChange={(e) => { setToolSearch(e.target.value); setToolPage(1); }}
              className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
            <select
              value={toolStatusFilter}
              onChange={(e) => { setToolStatusFilter(e.target.value); setToolPage(1); }}
              className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="">全部状态</option>
              <option value="online">在线</option>
              <option value="offline">离线</option>
            </select>
            <select
              value={toolCategoryFilter}
              onChange={(e) => { setToolCategoryFilter(e.target.value); setToolPage(1); }}
              className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="">全部分类</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.name}>{cat.name}</option>
              ))}
            </select>
            <select
              value={`${toolSortBy}-${toolSortOrder}`}
              onChange={(e) => { const [by, order] = e.target.value.split('-'); setToolSortBy(by); setToolSortOrder(order as 'asc'|'desc'); }}
              className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="title-asc">名称 A-Z</option>
              <option value="title-desc">名称 Z-A</option>
              <option value="rating-desc">评分 高→低</option>
              <option value="rating-asc">评分 低→高</option>
              <option value="usage_count-desc">使用次数 多→少</option>
              <option value="usage_count-asc">使用次数 少→多</option>
              <option value="created_at-desc">最新创建</option>
              <option value="created_at-asc">最早创建</option>
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select
              value={showPcFilter}
              onChange={(e) => { setShowPcFilter(e.target.value); setToolPage(1); }}
              className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="all">PC 展示: 全部</option>
              <option value="true">仅 PC 展示</option>
              <option value="false">仅 PC 不展示</option>
            </select>
            <select
              value={showMobileFilter}
              onChange={(e) => { setShowMobileFilter(e.target.value); setToolPage(1); }}
              className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="all">移动展示: 全部</option>
              <option value="true">仅移动展示</option>
              <option value="false">仅移动不展示</option>
            </select>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-slate-400">每页</span>
              <select
                value={toolPageSize}
                onChange={(e) => { setToolPageSize(Number(e.target.value)); setToolPage(1); }}
                className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
              <span className="text-sm text-slate-400">条</span>
            </div>
          </div>
        </div>
```

**Step 4: 新增分页组件**

在 `</table>` 之后新增：

```tsx
        {/* 分页控件 */}
        {toolTotalPages > 1 && (
          <div className="flex items-center justify-between mt-4 text-sm text-slate-400">
            <span>共 {toolTotal} 条记录，第 {toolPage}/{toolTotalPages} 页</span>
            <div className="flex space-x-1">
              <button
                onClick={() => setToolPage(1)}
                disabled={toolPage === 1}
                className="px-3 py-1 rounded bg-slate-700 disabled:opacity-50 hover:bg-slate-600"
              >
                首页
              </button>
              <button
                onClick={() => setToolPage(p => Math.max(1, p - 1))}
                disabled={toolPage === 1}
                className="px-3 py-1 rounded bg-slate-700 disabled:opacity-50 hover:bg-slate-600"
              >
                上一页
              </button>
              {Array.from({ length: Math.min(5, toolTotalPages) }, (_, i) => {
                let pageNum = Math.max(1, Math.min(toolPage - 2, toolTotalPages - 4));
                pageNum = i + pageNum;
                if (pageNum > toolTotalPages) return null;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setToolPage(pageNum)}
                    className={`px-3 py-1 rounded ${pageNum === toolPage ? 'bg-blue-600 text-white' : 'bg-slate-700 hover:bg-slate-600'}`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              <button
                onClick={() => setToolPage(p => Math.min(toolTotalPages, p + 1))}
                disabled={toolPage >= toolTotalPages}
                className="px-3 py-1 rounded bg-slate-700 disabled:opacity-50 hover:bg-slate-600"
              >
                下一页
              </button>
              <button
                onClick={() => setToolPage(toolTotalPages)}
                disabled={toolPage >= toolTotalPages}
                className="px-3 py-1 rounded bg-slate-700 disabled:opacity-50 hover:bg-slate-600"
              >
                末页
              </button>
            </div>
          </div>
        )}
        {toolTotalPages <= 1 && toolTotal > 0 && (
          <div className="mt-4 text-sm text-slate-400">共 {toolTotal} 条记录</div>
        )}
```

**注意**：当 `toolTotalPages <= 1` 时隐藏所有翻页按钮，只显示统计文本。避免首页/末页/上下页全部 disabled 但还占位的问题。

**Step 5: 提交**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(tool-mgmt): 管理后台新增分页组件和高级搜索筛选"
```

---

### Task 8: 前端首页 — platform 过滤 + 自定义图标

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/components/ToolCard/ToolCard.tsx`（或对应文件）
- Modify: `frontend/src/App.tsx`

**Step 1: 修改前端 API 传 platform 参数**

在 `api.ts` 中，修改 `fetchTools`：

```typescript
export async function fetchTools(platform?: string): Promise<Tool[]> {
  try {
    const url = platform
      ? `${API_BASE_URL}/tools?platform=${platform}`
      : `${API_BASE_URL}/tools`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    const data = await response.json();
    return data.tools;
  } catch (error) {
    console.error('Error fetching tools:', error);
    throw error;
  }
}
```

同样修改 `fetchToolsByCategory`，添加 platform 支持：

```typescript
export async function fetchToolsByCategory(category: string, platform?: string): Promise<Tool[]> {
  try {
    const params = new URLSearchParams();
    if (platform) params.append('platform', platform);
    const response = await fetch(`${API_BASE_URL}/tools/category/${encodeURIComponent(category)}?${params.toString()}`);
    if (!response.ok) {
      throw new Error('Failed to fetch tools by category');
    }
    const data = await response.json();
    return data.tools;
  } catch (error) {
    console.error('Error fetching tools by category:', error);
    throw error;
  }
}
```

**Step 2: 修改 App.tsx 首页加载逻辑**

在 `HomePage` 组件中，将 `loadTools` 和 `loadToolsDataByCategory` 调用改为传 `platform='pc'`：

```typescript
  const loadTools = async () => {
    try {
      setLoading(true);
      const data = await fetchTools('pc');
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      setError(t.errors.toolLoadFailed);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadToolsDataByCategory = async (category: string) => {
    try {
        setLoading(true);
        const data = await loadToolsByCategory(category, 'pc');
        setFilteredTools(data);
        setError(null);
    } catch (err) {
        setError(t.errors.toolLoadFailed);
        console.error(err);
    } finally {
        setLoading(false);
    }
  };
```

修改 `api.ts` 的 `loadToolsByCategory`：

```typescript
export async function loadToolsByCategory(category: string, platform?: string): Promise<Tool[]> {
    return fetchToolsByCategory(category, platform);
}
```

**Step 3: 修改 ToolCard 支持自定义图标**

读取 `frontend/src/components/ToolCard/ToolCard.tsx` 当前内容后修改：

如果 `tool.custom_icon_url` 存在，则渲染 `<img src={custom_icon_url}>` 代替 FontAwesome `<i>` 标签。

**Step 4: 提交**

```bash
git add frontend/src/services/api.ts frontend/src/App.tsx frontend/src/components/ToolCard/ToolCard.tsx
git commit -m "feat(tool-mgmt): PC 端首页按 platform 过滤 + 支持自定义图标"
```

---

### Task 9: 小程序 — platform 过滤 + 自定义图标

**Files:**
- Modify: `tools-mini-program/src/services/tool.ts`
- Modify: `tools-mini-program/src/components/ToolCard/index.tsx`
- Modify: `tools-mini-program/src/types/index.ts`

**Step 1: 更新小程序 Tool 类型**

在 `tools-mini-program/src/types/index.ts` 的 Tool 接口中新增：

```typescript
  custom_icon_url?: string;
  show_pc?: boolean;
  show_mobile?: boolean;
```

**Step 2: 修改工具列表 API**

在 `tool.ts` 的 `getTools` 方法中，修改请求 URL 添加 `platform=mobile`：

```typescript
  getTools: async (category?: ToolCategory): Promise<Tool[]> => {
    const params = new URLSearchParams();
    params.append('platform', 'mobile');
    if (category && category !== 'all') params.append('category', category);
    const res = await request<{ tools: Tool[] }>(`/tools?${params.toString()}`, {
      needAuth: false
    });
    // ... 剩余逻辑不变
```

**注意**：后端 `/tools` 接口已在 Task 4 中支持 `platform` 和 `category` 联合过滤。

**Step 3: ~~修改后端 `/tools` 接口支持 category 过滤~~（已在 Task 4 完成）**

（Task 4 已实现 `get_tools(platform, category)` 方法，此处跳过）

**Step 4: 修改小程序 ToolCard 图标渲染**

```typescript
export default function ToolCard({ tool, onClick }: ToolCardProps) {
  const hasCustomIcon = !!tool.custom_icon_url

  return (
    <View className='tool-card' onClick={onClick}>
      <View className='tool-card-icon'>
        {hasCustomIcon ? (
          <Image
            src={tool.custom_icon_url!}
            className='tool-card-custom-icon'
            mode='aspectFit'
          />
        ) : (
          <Text className='tool-card-emoji'>{getToolEmoji(tool.icon)}</Text>
        )}
      </View>
      <View className='tool-card-info'>
        <Text className='tool-card-name' numberOfLines={1}>{tool.title}</Text>
        <Text className='tool-card-desc' numberOfLines={2}>{tool.description}</Text>
      </View>
    </View>
  )
}
```

在 `ToolCard.scss` 中新增：

```scss
.tool-card-custom-icon {
  width: 48rpx;
  height: 48rpx;
  object-fit: contain;
}
```

**Step 5: 提交**

```bash
git add tools-mini-program/src/services/tool.ts tools-mini-program/src/components/ToolCard/index.tsx tools-mini-program/src/components/ToolCard/ToolCard.scss tools-mini-program/src/types/index.ts
git commit -m "feat(tool-mgmt): 小程序按 platform 过滤 + 支持自定义图标"
```

---

### Task 10: 后端搜索/分类接口同步 platform 过滤

**Files:**
- Modify: `backend/app/services/tools_service.py`
- Modify: `backend/app/routes/tools.py`

当前 `/tools/search` 和 `/tools/category/{category}` 也需要支持 `platform` 过滤。

**Step 1: 修改 `search_tools` 方法**

替换 `tools_service.py` 中第 206-229 行的 `search_tools` 方法：

```python
    def search_tools(self, query: str, platform: Optional[str] = None) -> List[Tool]:
        """搜索工具，支持 platform 过滤（参数化查询防止 SQL 注入）"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                search_term = f"%{query}%"
                sql = """
                    SELECT * FROM tools 
                    WHERE status = 'online'
                    AND (LOWER(title) LIKE LOWER(%s) OR LOWER(description) LIKE LOWER(%s))
                """
                params: list = [search_term, search_term]

                if platform == "pc":
                    sql += " AND show_pc = TRUE"
                elif platform == "mobile":
                    sql += " AND show_mobile = TRUE"

                cur.execute(sql, params)

                rows = cur.fetchall()
                return [self._row_to_tool(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            return []
        finally:
            if conn:
                conn.close()
```

**Step 2: 修改 `get_tools_by_category` 方法**

替换 `tools_service.py` 中第 181-204 行的 `get_tools_by_category` 方法：

```python
    def get_tools_by_category(self, category: str, platform: Optional[str] = None) -> List[Tool]:
        """按分类获取工具，支持 platform 过滤（参数化查询防止 SQL 注入）"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                sql = "SELECT * FROM tools WHERE status = 'online'"
                params: list = []

                if platform == "pc":
                    sql += " AND show_pc = TRUE"
                elif platform == "mobile":
                    sql += " AND show_mobile = TRUE"

                if category == "全部工具":
                    sql += " ORDER BY title"
                else:
                    sql += " AND category = %s ORDER BY title"
                    params.append(category)

                cur.execute(sql, params)

                rows = cur.fetchall()
                return [self._row_to_tool(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching tools by category: {e}")
            return []
        finally:
            if conn:
                conn.close()
```

**Step 3: 修改路由**

在 `tools.py` 中，修改搜索路由（第 52-56 行）：

```python
@router.get("/tools/search", response_model=SearchResponse)
def search_tools_endpoint(
    q: str = Query(..., description="搜索关键词"),
    platform: Optional[str] = Query(None, description="平台过滤: pc 或 mobile")
):
    """搜索工具"""
    tools = tools_service.search_tools(q, platform)
    return SearchResponse(tools=tools, count=len(tools))
```

修改分类路由（第 58-62 行）：

```python
@router.get("/tools/category/{category}", response_model=CategoryResponse)
def get_tools_by_category_endpoint(
    category: str,
    platform: Optional[str] = Query(None, description="平台过滤: pc 或 mobile")
):
    """按分类获取工具"""
    tools = tools_service.get_tools_by_category(category, platform)
    return CategoryResponse(tools=tools, category=category)
```

**Step 4: 验证语法**

Run: `cd backend && python -m py_compile app/services/tools_service.py && python -m py_compile app/routes/tools.py`
Expected: 无输出

**Step 5: 提交**

```bash
git add backend/app/services/tools_service.py backend/app/routes/tools.py
git commit -m "feat(tool-mgmt): 搜索和分类接口支持 platform 过滤"
```

---

### Task 11: 后端验证语法 + 全量检查

**Step 1: 全量语法检查**

Run: `cd backend && python -m py_compile app/services/tools_service.py && python -m py_compile app/models/tool_models.py && python -m py_compile app/routes/admin.py && python -m py_compile app/routes/tools.py`
Expected: 全部无输出

**Step 2: 提交**

```bash
# 检查 git status 确保没有遗漏
git status
```
