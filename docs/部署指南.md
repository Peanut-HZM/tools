# 部署指南

本文档说明如何部署工具箱的前端和后端应用。

## 后端部署

### 本地开发环境

1. 安装Python依赖：
```bash
cd backend
pip install -r requirements.txt
```

2. 启动后端服务：
```bash
uvicorn app.main:app --reload --port 8000
```

后端API将在 http://localhost:8000 启动

### 生产环境部署

#### 使用Uvicorn

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 使用Gunicorn + Uvicorn Workers

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Docker部署

创建 `backend/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

构建和运行：
```bash
docker build -t backend .
docker run -p 8000:8000 backend
```

## 前端部署

### 本地开发环境

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

前端应用将在 http://localhost:3000 启动

### 生产环境部署

#### 构建生产版本

```bash
cd frontend
npm run build
```

构建产物将生成在 `dist` 目录

#### 部署到Vercel

1. 安装Vercel CLI：
```bash
npm install -g vercel
```

2. 部署：
```bash
cd frontend
vercel
```

#### 部署到Netlify

1. 安装Netlify CLI：
```bash
npm install -g netlify-cli
```

2. 部署：
```bash
cd frontend
netlify deploy --prod
```

#### 使用Nginx部署

1. 构建前端：
```bash
cd frontend
npm run build
```

2. 配置Nginx：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 环境变量配置

### 后端环境变量

创建 `backend/.env` 文件：

```env
# CORS配置
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# 其他配置
DEBUG=False
```

### 前端环境变量

修改 `frontend/src/services/api.ts` 中的 `API_BASE_URL`：

```typescript
const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000/api';
```

创建 `frontend/.env.production`:

```env
VITE_API_URL=https://your-api-domain.com/api
```

## 云服务部署建议

### 后端推荐平台
- Railway
- Heroku
- AWS EC2
- Google Cloud Run
- DigitalOcean App Platform

### 前端推荐平台
- Vercel (推荐)
- Netlify
- Cloudflare Pages
- AWS S3 + CloudFront

## 健康检查

### 后端健康检查端点

```bash
curl http://localhost:8000/
```

应返回：
```json
{"message": " Tool Aggregation API"}
```

### API文档

访问 http://localhost:8000/docs 查看Swagger UI文档

## 故障排查

### 后端无法启动
- 检查Python版本是否为3.10+
- 确认所有依赖已正确安装
- 检查端口8000是否被占用

### 前端无法连接后端
- 确认后端服务正在运行
- 检查CORS配置是否正确
- 验证API_BASE_URL配置

### 构建失败
- 清除node_modules并重新安装：`rm -rf node_modules && npm install`
- 清除构建缓存：`npm run build -- --force`
