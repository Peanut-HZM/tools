---
purpose: 修复本机 token-usage 页面无法采集当前设备数据：UsageFetcher.fetch_claude 依赖 PATH 找 ccusage，但 uvicorn 子进程继承不到 git bash 的 PATH；改用项目已有的 ccusage_invoker.find_ccusage() 跨平台路径扫描（支持 .cmd / nvm / pnpm）。
date: 2026-08-09
---

# 本机 Token Usage 采集修复设计

## 背景

`http://localhost:5178/tools/token-usage` 点击"同步数据"后，本机无法采集当前设备的 Claude Code 用量。原因：ccusage 在 Windows 下通过全局 npm 安装为 `.cmd` 文件，依赖 `PATH` 才能被 `shutil.which("ccusage")` 找到。

`dev-services.py` 用 `python dev-services.py restart backend` 启动的 `uvicorn` 进程继承的是 `python.exe`（系统 pythoncore）的 PATH，**不含 git bash 的 PATH**，导致 `shutil.which("ccusage")` 返回 None → `UsageFetcher.fetch_claude` 报 `{"error": "CLI 未安装: ccusage"}` → 同步失败。

## 方案

`backend/app/utils/ccusage_invoker.py` 已有跨平台 `find_ccusage()`（扫描 Windows `.cmd` / nvm / pnpm / 标准路径），直接用它替换 `fetch_claude` 中的 `shutil.which` 检查。`ccusage_invoker.run_ccusage` 内部已统一处理 PATH、HOME、找不到的结构化错误。

## 改动

### `backend/app/utils/usage_fetcher.py` `fetch_claude`

删除：
```python
        if shutil.which("ccusage") is None:
            return {"error": "CLI 未安装: ccusage"}
```

直接调用 `run_ccusage(args, timeout=180)`；找不到 ccusage 由 `run_ccusage` 返回 `{"ok": False, "error": CcusageError}`，自然走到下面的 `error` 分支返回结构化错误。

`shutil` import 若不再使用可一并删除（仅此处用到）。

## 不动

- `config.py` 的 `HOME` 覆盖逻辑（`ccusage_invoker._execute_and_parse` 已用 `REAL_HOME` 还原子进程 env）
- `_DESKTOP_MODE` 早返回（桌面模式仍禁用）
- 其他数据源（opencode-usage / ccusage-opencode）走 `run_generic_cli`，已用 `find_ccusage` 同款的路径扫描

## 验证

1. `python dev-services.py restart backend`
2. 浏览器 `http://localhost:5178/tools/token-usage`，登录后点"同步数据"
3. 后端日志应出现 `[ccusage-invoker] 找到 ccusage: ...`（不再 `CLI 未安装`）
4. 前端 Toast 显示 `已同步 N 条记录`，页面出现图表与明细

## 回滚

```bash
git checkout HEAD -- backend/app/utils/usage_fetcher.py
```