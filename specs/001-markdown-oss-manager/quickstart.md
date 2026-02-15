# Quickstart Guide: Markdown OSS 文件管理

**Feature**: Markdown OSS 文件管理  
**Setup Time**: ~15 minutes  
**Prerequisites**: 已配置阿里云 OSS 服务

## Prerequisites

1. **后端服务已启动**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 19092
   ```

2. **阿里云 OSS 已配置**
   确保 `backend/app/config/config.py` 中已配置：
   ```python
   ALIYUN_OSS_ACCESS_KEY_ID: str = "your-key-id"
   ALIYUN_OSS_ACCESS_KEY_SECRET: str = "your-key-secret"
   ALIYUN_OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"
   ALIYUN_OSS_BUCKET_NAME: str = "your-bucket"
   ```

3. **前端依赖已安装**
   ```bash
   cd frontend
   npm install
   ```

## Quick Setup

### 1. 配置 OSS 生命周期规则（推荐）

登录阿里云 OSS 控制台，为版本历史存储桶配置生命周期规则：

```xml
<LifecycleConfiguration>
  <Rule>
    <ID>DeleteOldVersions</ID>
    <Prefix>versions/</Prefix>
    <Status>Enabled</Status>
    <Expiration>
      <Days>30</Days>
    </Expiration>
  </Rule>
</LifecycleConfiguration>
```

### 2. 启动开发服务器

**后端**:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 19092
```

**前端**:
```bash
cd frontend
npm run dev
```

### 3. 测试 OSS 功能

1. 打开浏览器访问 `http://localhost:5178`
2. 登录系统（已有账号或注册新账号）
3. 导航到 Markdown 编辑器工具
4. 点击左侧"云端文件"区域
5. 上传一个 Markdown 文件测试

## Key Features Test Checklist

- [ ] **文件上传**: 拖拽或点击上传 `.md` 文件
- [ ] **文件列表**: 左侧显示 OSS 文件，带有云端图标标识
- [ ] **文件打开**: 点击 OSS 文件，内容加载到编辑器
- [ ] **文件编辑**: 修改内容后按 Ctrl+S 保存到 OSS
- [ ] **版本历史**: 查看文件的历史版本列表
- [ ] **版本回滚**: 选择一个历史版本回滚
- [ ] **离线编辑**: 断开网络后仍可编辑，恢复后自动同步
- [ ] **分块上传**: 测试上传超过 10MB 的文件（可选）

## Common Issues

### 1. OSS 连接失败

**症状**: 上传文件时提示 "OSS service is not configured"

**解决**:
```bash
# 检查后端配置
cat backend/app/config/config.py | grep ALIYUN_OSS

# 确保 oss2 已安装
pip install oss2
```

### 2. CORS 错误

**症状**: 浏览器控制台显示跨域错误

**解决**: 在阿里云 OSS 控制台配置 CORS:
```json
{
  "AllowedOrigin": ["http://localhost:5178"],
  "AllowedMethod": ["GET", "POST", "PUT", "DELETE", "HEAD"],
  "AllowedHeader": ["*"],
  "ExposeHeader": ["ETag"],
  "MaxAgeSeconds": 300
}
```

### 3. 版本历史不显示

**症状**: 保存文件后版本历史为空

**解决**: 检查后端 API 是否正确返回版本列表：
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:19092/api/markdown-editor/oss/versions?file_path=markdown/{user_id}/test.md
```

## API Testing with curl

### 上传文件
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/test.md" \
  -F "path=docs" \
  http://localhost:19092/api/markdown-editor/oss/upload
```

### 列出文件
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:19092/api/markdown-editor/oss/list
```

### 读取文件
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:19092/api/markdown-editor/oss/read?file_path=markdown/{user_id}/docs/test.md"
```

### 保存文件
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "markdown/{user_id}/docs/test.md",
    "content": "# Updated Content"
  }' \
  http://localhost:19092/api/markdown-editor/oss/save
```

## Development Tips

### 1. 使用 React DevTools 调试状态

安装 React DevTools 浏览器插件，查看：
- `fileStore`: 检查文件列表状态
- `offlineStore`: 检查离线缓存和同步队列

### 2. 查看 IndexedDB 缓存

Chrome DevTools:
1. Application 标签
2. IndexedDB > offline_cache
3. 查看 files 和 syncQueue 表

### 3. 模拟离线环境

Chrome DevTools:
1. Network 标签
2. Throttling 选择 "Offline"
3. 测试离线编辑和同步功能

### 4. 日志调试

前端代码中添加：
```typescript
// 开启详细日志
localStorage.setItem('DEBUG_OSS', 'true');

// 查看 IndexedDB 内容
import { getAllOfflineFiles } from './utils/indexedDb';
const files = await getAllOfflineFiles();
console.table(files);
```

## Next Steps

1. **运行测试**:
   ```bash
   cd frontend
   npm test -- FileTree
   ```

2. **构建生产版本**:
   ```bash
   cd frontend
   npm run build
   ```

3. **部署前检查**:
   - [ ] OSS 生命周期规则已配置
   - [ ] CORS 跨域配置正确
   - [ ] 生产环境 OSS 密钥已更新
   - [ ] 版本历史保留策略符合需求

## Resources

- [Feature Specification](../spec.md)
- [API Documentation](./api.md)
- [Data Model](../data-model.md)
- [阿里云 OSS 文档](https://help.aliyun.com/document_detail/31883.html)

## Support

遇到问题？

1. 查看浏览器控制台错误信息
2. 检查后端日志：`tail -f backend/logs/app.log`
3. 使用 API 测试工具（Postman/Insomnia）验证 API
4. 查看本功能的 GitHub Issues（如有）

