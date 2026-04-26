---
author: Peanut
created_at: 2026-04-25
purpose: Token 消耗统计页面 Windows 兼容性修复设计文档
status: 已审查
---

# Token 消耗统计页面 Windows 兼容性修复

## 背景

Token 消耗统计页面 (`http://localhost:5178/tools/token-usage`) 在 macOS 开发环境下功能正常，但在 Windows 开发环境下无法正常工作。经过分析，问题出在 `backend/app/utils/usage_fetcher.py` 中的 HOME 目录路径处理逻辑。

## 问题分析

### 根因

`usage_fetcher.py` 第 13-16 行代码：

```python
_home_raw = os.path.expanduser("~")
if "IdeaProjects" in _home_raw:
    _home_raw = f"/Users/{os.getlogin()}"
USER_HOME = _home_raw
```

**问题**：当在 Windows 上从项目目录（如 `G:\IdeaProjects\tools`）运行后端服务时，`os.path.expanduser("~")` 返回 `C:\Users\peanu`，不包含 "IdeaProjects"，所以不会触发转换。但如果某些情况下路径包含 "IdeaProjects"（比如在子目录中），会被强制改为 `/Users/xxx` 的 macOS 格式，导致路径错误。

**更深层问题**：这段代码的意图是处理 macOS 上从项目子目录运行时 `expanduser` 返回项目路径而非用户主目录的情况。但这种修正逻辑在 Windows 上完全不适用。

### 影响范围

- **文件**：`backend/app/utils/usage_fetcher.py`
- **功能**：Token 消耗统计 API 的数据获取
- **用户**：Windows 开发环境用户

## 解决方案

### 修改内容

**文件**：`backend/app/utils/usage_fetcher.py`

**修改前**：
```python
_home_raw = os.path.expanduser("~")
if "IdeaProjects" in _home_raw:
    _home_raw = f"/Users/{os.getlogin()}"
USER_HOME = _home_raw
```

**修改后**：
```python
import platform
_home_raw = os.path.expanduser("~")
# macOS 上从 JetBrains 项目子目录运行时，expanduser 可能返回项目路径
# 而非真实用户主目录，此时需要修正。Windows 无此问题，故跳过。
if platform.system() != "Windows" and "IdeaProjects" in _home_raw:
    _home_raw = f"/Users/{os.getlogin()}"
USER_HOME = _home_raw
```

### 设计决策

1. **最小修改原则**：仅添加平台判断，不改变原有 macOS 逻辑
2. **向后兼容**：macOS 功能保持原样，Windows 获得修复
3. **明确注释**：添加注释说明为何需要平台判断
4. **使用 `platform.system()`**：比 `sys.platform` 更直观，覆盖更广（包括 Cygwin、MSYS2 等）

## 验证计划

### Windows 验证
1. 启动前后端服务
2. 访问 `http://localhost:5178/tools/token-usage`
3. 确认页面正常加载，数据显示正确
4. 测试刷新功能
5. 测试导出 CSV 功能

### macOS 验证
1. 通过代码审查确认逻辑正确
2. 确认 `platform.system() != "Windows"` 在 macOS 上为 `True`
3. 确认原有路径修正逻辑仍然执行

### Linux 验证
1. 确认 `platform.system() != "Windows"` 在 Linux 上为 `True`
2. 确认从 `~/IdeaProjects` 子目录运行时路径修正仍然有效

### 边界情况
1. 测试 `os.getlogin()` 异常时的错误处理（应添加 try-except）
2. 确认 CLI 工具（ccusage、opencode-usage）在 Windows 上已安装

## 影响评估

- **修改文件数**：1
- **修改行数**：3（添加 import 和平台判断）
- **Breaking Change**：无
- **风险等级**：低

## 实施记录

- **实施日期**：2026-04-25
- **实施人**：Peanut
- **状态**：已完成

## 后续改进（TODO）

1. **生产环境路径配置**：考虑通过环境变量 `USER_HOME` 或配置文件来设置主目录，而不是依赖运行时推断
2. **错误处理增强**：为 `os.getlogin()` 添加 try-except，防止在特殊环境下失败

## 备注

此修复仅针对开发环境。生产环境应使用配置化的路径管理，避免依赖 `expanduser` 的假设。