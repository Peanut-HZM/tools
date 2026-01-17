# Backend API

工具箱后端服务，基于FastAPI构建。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行服务

```bash
uvicorn app.main:app --reload --port 8000
```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

- `GET /api/tools` - 获取所有工具
- `GET /api/tools/search?q={query}` - 搜索工具
- `GET /api/tools/category/{category}` - 按分类获取工具
