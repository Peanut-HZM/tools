# 快速启动指南

## 前置要求

- Python 3.10+
- Node.js 16+
- npm 或 yarn

## 快速启动步骤

### 1. 启动后端服务

打开第一个终端窗口：

```bash
# 进入后端目录
cd backend

# 安装Python依赖
pip install -r requirements.txt

# 启动后端服务
uvicorn app.main:app --reload --port 19092
```

后端服务将在 http://localhost:19092 启动

### 2. 启动前端应用

打开第二个终端窗口：

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端应用将在 http://localhost:5178 启动

### 3. 访问应用

在浏览器中打开 http://localhost:5178

## 验证安装

### 验证后端

访问 http://localhost:19092/docs 查看API文档

或使用curl测试：
```bash
curl http://localhost:19092/api/tools
```

### 验证前端

1. 打开 http://localhost:5178
2. 应该看到完整的工具箱页面
3. 尝试点击分类标签筛选工具
4. 尝试在搜索框中搜索工具

## 常见问题

### 端口被占用

如果19092或5178端口被占用，可以修改端口：

**后端：**
```bash
uvicorn app.main:app --reload --port 19093
```

**前端：**
修改 `frontend/vite.config.ts` 中的 `server.port`

### 依赖安装失败

**Python依赖：**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Node依赖：**
```bash
rm -rf node_modules package-lock.json
npm install
```

### CORS错误

确保后端的CORS配置包含前端地址。检查 `backend/app/main.py` 中的 `allow_origins` 配置。

## 功能测试清单

- [ ] 页面正常加载，显示所有工具卡片
- [ ] 点击分类标签可以筛选工具
- [ ] 搜索框可以搜索工具
- [ ] 工具卡片悬停有动画效果
- [ ] 点击工具卡片显示提示信息
- [ ] 点击"立即使用"按钮显示提示信息
- [ ] 页面响应式布局正常（调整浏览器窗口大小测试）

## 下一步

- 查看 [README.md](README.md) 了解项目详情
- 查看 [DEPLOYMENT.md](DEPLOYMENT.md) 了解部署方法
- 查看 `.kiro/specs/tool-aggregation-website/` 了解完整的需求和设计文档
