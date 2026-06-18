---
author: peanut
created_at: 2026-06-18
purpose: GLM-Coding Pro 抢购工具的设计规格，包括架构、流程、错误处理和测试方案
---

# GLM-Coding Pro 抢购工具设计规格

## 1. 概述

### 1.1 背景

智谱 AI 开放平台（https://open.bigmodel.cn/glm-coding）提供 GLM-Coding Pro 订阅服务，每天 10:00 限量开放购买。由于抢购人数众多，手动操作难以抢到，需要自动化工具在指定时间检测页面状态并自动点击购买。

### 1.2 目标

在当前工具聚合平台中新增一个"GLM-Coding Pro 抢购"工具，实现以下核心功能：

- 浏览器自动化登录并持久化登录态
- 在抢购时间前预热浏览器
- 高频刷新页面检测按钮状态
- 按钮变为可点击时毫秒级自动点击
- 提供可视化配置、倒计时和实时日志
- 手动触发，避免后台全自动运行的风控风险

### 1.3 非目标

- 不实现全自动定时任务（避免长期运行和风控）
- 不处理支付环节（只负责进入支付页，由用户手动完成支付）
- 不支持多账号并发
- 不自动处理验证码/滑块

## 2. 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | 项目现有技术栈，保持一致 |
| 浏览器自动化 | Playwright（Python） | 支持现代 SPA、持久化 state、headless/headed 模式切换 |
| 前端框架 | React + TypeScript + Tailwind | 项目现有技术栈 |
| 状态管理 | Zustand（前端） | 管理抢购状态和日志 |
| 登录态存储 | Playwright storage_state | 持久化 cookie 和 localStorage |
| 日志存储 | PostgreSQL（项目现有） | 存储抢购任务日志 |

## 3. 架构设计

### 3.1 后端模块

| 文件 | 职责 |
|------|------|
| `backend/app/routes/glm_coding_rusher.py` | API 路由：登录、配置、启动/停止、状态、日志 |
| `backend/app/services/glm_coding_rusher_service.py` | 核心抢购逻辑：Playwright 浏览器管理、页面操作 |
| `backend/app/models/glm_coding_rusher_models.py` | SQLAlchemy 模型 |
| `backend/app/schemas/glm_coding_rusher_schemas.py` | Pydantic 请求/响应模型 |
| `backend/data/glm_coding_rusher/` | 登录态 state 文件存储 |
| `backend/app/data/tools_data.py` | 工具注册表新增条目 |
| `backend/app/main.py` | 注册路由 |

### 3.2 前端模块

| 文件 | 职责 |
|------|------|
| `frontend/src/components/Tools/GlmCodingRusher/GlmCodingRusher.tsx` | 抢购工具主页面 |
| `frontend/src/api/glmCodingRusherApi.ts` | 后端 API 封装 |
| `frontend/src/App.tsx` | 路由映射 |
| `frontend/src/i18n/zh.ts` | 中文文案 |
| `frontend/src/i18n/en.ts` | 英文文案 |

### 3.3 外部依赖

- 后端新增：`playwright` Python 包
- 前端：无需新增依赖

## 4. 核心抢购流程

### 4.1 首次登录

1. 用户在前端点击"打开登录窗口"
2. 后端启动 Playwright（headed 模式）
3. 打开 `https://open.bigmodel.cn/glm-coding`
4. 用户手动扫码/短信登录
5. 后端调用 `context.storage_state()` 保存到 `backend/data/glm_coding_rusher/state.json`
6. 关闭浏览器，返回"登录成功"

### 4.2 抢购预热（开抢前 N 分钟）

1. 用户点击"开始抢购"
2. 后端用保存的 state 启动 headless 浏览器
3. 打开目标页面，校验登录态
4. 如果登录态失效，提示用户重新登录
5. 记录按钮基线状态（"暂时售罄"）

### 4.3 抢购主循环

```
从 9:59:50 开始：
while 未超时 and 未成功:
    刷新页面
    等待页面加载完成
    定位 Pro 套餐区域
    读取按钮文字/状态
    if 按钮可点击:
        立即点击按钮
        进入下单流程
        返回结果
        break
    else:
        等待 refresh_interval_ms 后继续
```

### 4.4 按钮检测

- 定位 Pro 套餐卡片的 CSS 选择器或文字匹配
- 检测按钮的 `disabled` 属性、文字内容、class
- 可点击状态判定：
  - 文字包含"立即购买"/"立即开通"/"特惠订阅" 且非 disabled
  - 或 class 从灰色变为高亮

### 4.5 下单流程

1. 点击 Pro 套餐按钮
2. 等待确认弹窗/订单页出现
3. 点击确认（如果有）
4. 进入支付页后截取订单信息
5. 返回成功结果
6. 停止循环

### 4.6 前端状态展示

- **倒计时**：距离下次 10:00
- **浏览器状态**：idle / preheating / refreshing / clicking / success / failed
- **实时日志**：刷新和检测结果文本流
- **手动停止**：随时中断

## 5. API 设计

### 5.1 路由前缀：`/api/glm-coding-rusher`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/login` | 启动浏览器打开登录页，登录成功后保存 state |
| GET | `/login-status` | 检查 state 是否存在及有效 |
| POST | `/config` | 保存抢购配置 |
| GET | `/config` | 获取当前配置 |
| POST | `/start` | 启动抢购任务 |
| POST | `/stop` | 停止当前抢购任务 |
| GET | `/status` | 获取任务状态 |
| GET | `/logs` | 获取抢购日志 |
| GET | `/logs/{task_id}` | 获取某次任务详细日志 |

### 5.2 主要 Schema

```python
class RusherConfig(BaseModel):
    target_package: str = "pro"
    sale_time: str = "10:00"
    preheat_seconds: int = 90
    refresh_interval_ms: int = 500
    timeout_seconds: int = 60
    headless: bool = False


class RusherStatus(BaseModel):
    is_running: bool
    current_phase: str  # idle / preheating / refreshing / clicking / success / failed
    message: str
    next_sale_time: Optional[str]
    last_error: Optional[str]


class RusherLog(BaseModel):
    id: str
    task_id: str
    phase: str
    message: str
    created_at: datetime
```

## 6. 数据库设计

### 6.1 glm_coding_rusher_configs

| 列 | 类型 | 说明 |
|----|------|------|
| id | String (PK) | UUID |
| user_id | String | 用户 ID |
| target_package | String | 目标套餐，默认 "pro" |
| sale_time | String | 每天开抢时间，默认 "10:00" |
| preheat_seconds | Integer | 提前预热秒数，默认 90 |
| refresh_interval_ms | Integer | 刷新间隔毫秒，默认 500 |
| timeout_seconds | Integer | 超时秒数，默认 60 |
| headless | Boolean | 是否无头浏览器，默认 False |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 6.2 glm_coding_rusher_logs

| 列 | 类型 | 说明 |
|----|------|------|
| id | String (PK) | UUID |
| task_id | String (Index) | 任务 ID |
| user_id | String | 用户 ID |
| phase | String | 阶段 |
| message | Text | 日志消息 |
| created_at | DateTime | 时间戳 |

## 7. 错误处理

### 7.1 登录态相关

| 场景 | 处理 |
|------|------|
| 首次登录未完成 | 浏览器窗口保持打开，前端显示"等待登录..." |
| state 文件不存在 | 前端提示"请先登录" |
| state 已过期 | 预热阶段检测重定向到登录页，提示"登录态已失效" |
| 抢购过程中被踢出 | 检测到登录页特征后停止，标记失败"登录态丢失" |

### 7.2 页面与元素相关

| 场景 | 处理 |
|------|------|
| 页面刷新失败 | 重试 3 次，仍失败则停止 |
| 找不到 Pro 套餐卡片 | 报"目标套餐元素未找到" |
| 按钮状态无法识别 | 记录按钮文字和 HTML，标记"状态未知"但不停止 |
| 点击后无响应 | 等待 3 秒后重试点击（最多 2 次） |

### 7.3 抢购过程相关

| 场景 | 处理 |
|------|------|
| 按钮仍不可点 | 持续刷新直到超时（默认 60 秒） |
| 提示"当前抢购人数太多" | 正常情况，继续刷新 |
| 提示"库存不足" | 停止，标记"已售罄" |
| 进入支付页 | 截取订单信息，返回结果，工具不继续操作支付 |
| 二次确认弹窗 | 自动点击确认 |

### 7.4 风控相关

| 场景 | 处理 |
|------|------|
| 刷新太频繁被限流 | 最小间隔 500ms，遇到限流自动加大间隔 |
| 验证码/滑块 | 立即停止，提示用户手动处理 |
| IP 被封 | 停止并提示 |

### 7.5 任务控制

- **单实例**：后台全局变量或文件锁保证同时只有一个任务
- **手动停止**：前端 stop 请求终止 Playwright 进程
- **自动停止**：成功、超时、异常、登录态失效
- **后端重启**：服务重启时清理进行中的任务

## 8. 测试方案

### 8.1 单元测试

- `parse_button_state()`：按钮状态解析
- `next_sale_time()`：下次开抢时间计算
- `format_countdown()`：倒计时格式化
- `validate_config()`：配置校验
- 任务状态机转换

### 8.2 浏览器自动化测试

- 本地 HTML 页面模拟套餐卡片
- 按钮从"暂时售罄"变为"立即购买"
- 验证检测和点击行为
- 测试异常分支

### 8.3 登录流程测试

- 浏览器正常打开
- state 保存和加载
- state 过期识别

### 8.4 真实页面预验证

- 非抢购时段打开真实页面
- 确认能识别 Pro 套餐卡片和按钮
- 验证刷新和按钮状态读取
- 确认登录态保持

### 8.5 真实抢购验证

- 抢购当天提前部署
- 9:55 开始预热
- 观察刷新和检测行为
- 记录结果

### 8.6 浏览器验证

按项目规范验证：
- 页面正常渲染
- 登录按钮可点击
- 配置保存成功
- 倒计时显示正确
- Console 无报错

## 9. 部署与运行

### 9.1 本地运行

工具通过 `dev_services.py` 在本地启动服务：

```bash
python dev_services.py start
```

访问 `http://localhost:5178/tools/glm-coding-rusher`

### 9.2 首次使用

1. 安装 Playwright：`pip install playwright && playwright install chromium`
2. 打开工具页面
3. 点击"打开登录窗口"完成登录
4. 配置抢购参数
5. 到点前 1-2 分钟点击"开始抢购"

### 9.3 注意事项

- 抢购前确认登录态有效
- 保持电脑不锁屏、不断网
- 刷新间隔不宜过小（≥500ms），避免风控
- 工具只负责进入支付页，支付需手动完成

## 10. 未来扩展（不在本次范围内）

- 全自动定时任务
- 多账号并发抢购
- 微信/钉钉通知
- 抢购成功率统计和分析
- 支持其他平台的类似抢购场景
