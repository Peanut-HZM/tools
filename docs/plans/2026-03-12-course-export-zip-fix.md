# 课程导出 ZIP 功能修复

> 日期：2026-03-12
> 状态：已批准

## 问题描述

后台管理课程详情页导出功能中，选择 ZIP 压缩包后导出报错。

**根本原因：**
- 前端 `ImportExportDialog.tsx` 调用了 `downloadCourseExportZip` 函数
- 该函数在 `coursePlatform.ts` 中未定义
- 后端缺少 `/api/admin/courses/export-zip` API 端点

## 修复方案

### 后端实现

#### 1. 添加 API 端点

**文件：** `backend/app/routes/course_platform_admin.py`

在课程导入导出接口部分添加：

```python
@router.post(
    "/courses/{course_id}/export-zip",
    summary="导出课程 ZIP 包",
    description="导出课程数据为 ZIP 格式（包含 JSON 和 Markdown 文件）",
)
async def export_course_zip(
    course_id: int,
    db: Session = Depends(get_db),
):
    """导出课程 ZIP 包（Admin）"""
    try:
        export_service = CourseExportService(db)

        # 生成 ZIP 文件
        zip_buffer = export_service.export_to_zip(course_id=course_id)

        # 返回 ZIP 文件
        response = StreamingResponse(
            io.BytesIO(zip_buffer),
            media_type="application/zip",
        )
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        response.headers["Content-Disposition"] = f"attachment; filename=course-export-{timestamp}.zip"
        return response

    except Exception as e:
        logger.error(f"导出 ZIP 失败 (course_id={course_id}): {e}")
        raise HTTPException(status_code=500, detail="导出 ZIP 失败")
```

#### 2. 添加服务层方法

**文件：** `backend/app/services/course_import_export_service.py`

添加 `export_to_zip` 方法：

```python
def export_to_zip(self, course_id: Optional[int] = None) -> bytes:
    """导出课程为 ZIP 格式"""
    import zipfile
    import io

    # 获取导出数据
    export_data = self.export_to_json(course_id=course_id)

    # 创建 ZIP 文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 添加 JSON 文件
        json_content = json.dumps(export_data.model_dump(), ensure_ascii=False, indent=2)
        zip_file.writestr('course-data.json', json_content)

        # 添加每个章节的 Markdown 文件
        for chapter in export_data.chapters:
            md_content = self._chapter_to_markdown(chapter)
            filename = f"chapters/{chapter.slug}.md"
            zip_file.writestr(filename, md_content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
```

### 前端实现

#### 1. 添加 API 函数

**文件：** `frontend/src/services/coursePlatform.ts`

在 `downloadCourseExport` 函数之后添加：

```typescript
/**
 * 下载课程 ZIP 包（包含 JSON + Markdown 文件）
 */
export const downloadCourseExportZip = async (
  courseId?: number,
  courseTitle?: string
): Promise<void> => {
  const response = await axios.post(
    `${API_BASE}/admin/courses/${courseId || 4}/export-zip`,
    null,
    {
      responseType: 'blob',
    }
  );

  // 创建下载链接
  const blob = new Blob([response.data], { type: 'application/zip' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const timestamp = new Date().toISOString().split('T')[0];
  link.setAttribute('download', `course-export-${timestamp}.zip`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
```

#### 2. 更新类型导出

确保 `coursePlatform.ts` 导出 `downloadCourseExportZip` 函数。

## 影响范围

| 文件 | 修改类型 | 影响 |
|------|---------|------|
| course_platform_admin.py | 新增 API 端点 | 课程 ZIP 导出 |
| course_import_export_service.py | 新增方法 | 课程 ZIP 导出 |
| coursePlatform.ts | 新增函数 | 课程 ZIP 导出 |
| ImportExportDialog.tsx | 无需修改 | 已调用该函数 |

## 验证标准

- [ ] 点击 ZIP 导出按钮后正常下载 ZIP 文件
- [ ] ZIP 文件包含 `course-data.json` 和所有章节 Markdown 文件
- [ ] JSON 文件内容完整
- [ ] Markdown 文件格式正确
- [ ] 浏览器 Console 无错误

## 相关文件

- 设计文档：`docs/plans/2026-03-10-course-editor-markdown-fix.md`（之前 ZIP 导出的设计）
