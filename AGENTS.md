# AGENTS.md - 项目智能代理规则

**所有项目规则详见 [CLAUDE.md](./CLAUDE.md)**

本文件是 CLAUDE.md 的引用入口，供不同 agent 加载。所有规则（Git 工作流、问题排查、部署流程、前后端规范等）均在 CLAUDE.md 中维护。

**最后同步：2026-09-13**
- 初始版本：从 logistics-finance 项目规则适配而来
- 适配内容：
  - 删除 Java/Spring Boot/微服务特定规则
  - 删除 Vue3/Element Plus 前端特定规则
  - 删除菜单权限、对账业务等业务特定规则
  - 新增 Python/FastAPI 后端开发规范
  - 新增 React/TypeScript/Tailwind 前端开发规范
  - 新增 pytest/Vitest 测试规范
  - 保留通用工程实践（事后规则沉淀、问题排查、Git 工作流等）

---

## 快速参考

### 核心原则

1. **事后规则沉淀**：问题解决后必须沉淀规则，防止重复踩坑
2. **禁止 Mock 与兜底**：真实问题必须如实暴露，禁止掩盖
3. **问题排查强制规则**：必须找到代码级根因，禁止猜测
4. **Git 工作流**：统一使用 rebase，禁止 merge
5. **临时产物清理**：任务完成后必须清理所有临时文件
6. **禁止批量脚本修改**：所有代码修改必须逐个文件手动进行

### 技术栈

- **后端**: Python 3.10+ / FastAPI / SQLAlchemy / PostgreSQL
- **前端**: React 18 / TypeScript / Vite / Tailwind CSS / Zustand
- **存储**: 阿里云 OSS
- **测试**: pytest (后端) / Vitest (前端)

### 常用命令

```bash
# 服务管理
python dev-services.py              # 启动服务
python dev-services.py restart      # 重启服务
python dev-services.py status       # 查看状态

# 后端
cd backend
uvicorn app.main:app --reload --port 19092
ruff check .
pytest

# 前端
cd frontend
npm run dev
npm run build
npm run test
```

### 关键规则

- ✅ 所有对话和代码注释使用中文
- ✅ 优先使用热重载，非必要不重启服务
- ✅ 修改后必须在浏览器中验收（前端视觉验证 + 后端集成验证）
- ✅ 后端关键代码必须包含日志记录
- ✅ 使用 `dev-services.py` 管理服务，不要手动启动
- ❌ 禁止批量脚本修改代码
- ❌ 禁止 Mock 与兜底
- ❌ 禁止猜测式修复
- ❌ 禁止只改代码不验收就声称"已修复"
- ❌ 禁止 `git pull`（不带 `--rebase`）
- ❌ 禁止 `git merge` 更新本地分支
- ❌ 禁止硬编码敏感信息

---

## 与 logistics-finance 项目的差异

本项目的规则是从 logistics-finance 项目适配而来，主要差异：

### 已删除的规则（不适用于本项目）

- ❌ keep-alive 缓存命名规则（Vue 特有）
- ❌ 物理删除实现规则（Java/MyBatis 特有）
- ❌ 业务表禁止冗余组织/部门字段（logistics-finance 业务）
- ❌ MyBatis-Plus 写法规则（Java 特有）
- ❌ 菜单与权限管理规则（logistics-finance 复杂权限系统）
- ❌ @RequiresPermission 通配符规则（Spring Security 特有）
- ❌ API 路由与 Gateway 配置规则（微服务特有）
- ❌ 双前端菜单独立性规则（logistics-finance 多前端）
- ❌ 移动端样式规则（小程序特有）
- ❌ 小程序包大小规则（Taro 特有）
- ❌ OCR 服务规则（logistics-finance 业务）
- ❌ 对账数据生成规则（logistics-finance 业务）
- ❌ 实体 update 方法的 String 字段规则（Java 特有）
- ❌ 内部 ID 字段不在前端页面展示规则（logistics-finance 业务）
- ❌ 清理与删除脚本必须先 SELECT 精确 ID 规则（logistics-finance 数据清理）
- ❌ 数据库唯一约束治理规则（logistics-finance 数据治理）
- ❌ 数据库操作执行方式强制规则（logistics-finance 数据库管理）
- ❌ 动态路由注册规则（Vue 特有）
- ❌ 动态 import 加载失败兜底规则（Vue 特有）

### 已新增的规则（本项目特有）

- ✅ FastAPI 路由设计规范
- ✅ SQLAlchemy ORM 使用规范
- ✅ React 函数组件 + Hooks 规范
- ✅ Zustand 状态管理规范
- ✅ Tailwind CSS 样式规范
- ✅ pytest 测试规范
- ✅ Vitest 测试规范
- ✅ FastAPI 错误处理规范
- ✅ CORS 配置规范
- ✅ JWT 认证规范

### 已保留并适配的规则（通用工程实践）

- ✅ 事后规则沉淀机制
- ✅ 禁止批量脚本修改代码
- ✅ 临时产物及时清理
- ✅ 禁止 Mock 与兜底
- ✅ 问题排查强制规则
- ✅ 客户端代码路径 DRY
- ✅ Git 工作流规范（rebase）
- ✅ 配置文件管理规范
- ✅ 浏览器进程管理
- ✅ ID 字段类型规则（适配 Python）
- ✅ 日志管理规范（适配 Python logging）
- ✅ 热加载与重启规则（适配 dev-services.py）
- ✅ 部署规范（简化）
- ✅ 安全规范（通用部分）

---

## 规则演进记录

### 2026-09-13 - 初始版本

- 从 logistics-finance 项目规则适配
- 删除所有 Java/Spring Boot/Vue3 特定规则
- 新增 Python/FastAPI/React 技术栈规范
- 保留通用工程实践
- 简化部署流程（单机部署，无微服务）
- 调整日志规范（Python logging 模块）

---

**所有详细规则请参见 [CLAUDE.md](./CLAUDE.md)**

**END**
