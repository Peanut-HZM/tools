# Skills 下载工具

本目录包含从 skills.sh 网站下载 AI Agent Skills 的工具脚本。

## 📁 文件说明

### 核心脚本

1. **advanced_download_skills.py** - 🚀 高级并行下载工具（推荐）
   - ✨ **多线程并行下载**（速度提升 5-10 倍）
   - 📊 **实时进度条显示**（可以看到每个任务状态）
   - 🎯 **智能超时检测**（自动跳过卡住的任务）
   - 🔄 **支持断点续传**（已下载的自动跳过）
   - 📈 **详细统计信息**（成功/失败/跳过数量）
   
   使用方法：
   ```bash
   python advanced_download_skills.py
   ```
   
   特点：
   - 默认使用 8 个线程并行下载
   - 每个任务有 120 秒超时限制
   - 实时显示当前下载的 skill 名称
   - 自动统计下载速度和预计时间

2. **parallel_download_skills.py** - 并行下载工具（基础版）
   - 多线程并行下载
   - 简单进度显示
   - 适合不需要进度条的场景
   
   使用方法：
   ```bash
   python parallel_download_skills.py
   ```

3. **smart_download_skills.py** - 智能下载工具（单线程版）
   - 单线程顺序下载
   - 智能尝试多种下载方法
   - 适合网络不稳定的情况
   
   使用方法：
   ```bash
   python smart_download_skills.py
   ```

2. **check_progress.py** - 快速查看下载进度
   - 显示当前下载进度
   - 显示进度条
   - 列出最近下载的 skills
   
   使用方法：
   ```bash
   python check_progress.py
   ```

3. **monitor_download_progress.py** - 实时监控下载进度
   - 每 10 秒自动更新进度
   - 显示下载速度
   - 预计剩余时间
   - 实时显示最新下载的 skills
   
   使用方法：
   ```bash
   python monitor_download_progress.py
   ```

4. **generate_skills_report.py** - 生成详细报告
   - 生成 `SKILLS_REPORT.md` 文件
   - 包含已下载和未下载的 skills 列表
   - 按安装量排序
   
   使用方法：
   ```bash
   python generate_skills_report.py
   ```

### 数据文件

- **skills_raw.txt** - 包含 25,354 个 skills 的 JSON 数据
- **skills_page.html** - skills.sh 网站的 HTML 页面（参考）

### 输出目录

- **skills/** - 下载的 skills 存放目录
- **SKILLS_REPORT.md** - 生成的详细报告
- **SKILLS_DOWNLOAD_SUMMARY.md** - 下载总结文档

## 🚀 快速开始

### 1. 并行下载所有 skills（推荐）

```bash
# 使用高级并行下载工具（带进度条）
python advanced_download_skills.py

# 会询问：
# - 要下载多少个？（直接按 Enter 下载全部）
# - 使用多少个线程？（建议 8-10，默认 8）
```

### 2. 基础并行下载

```bash
# 使用基础并行下载工具
python parallel_download_skills.py
```

### 3. 单线程下载（网络不稳定时）

```bash
# 使用智能单线程下载
python smart_download_skills.py
```

### 2. 查看进度

```bash
# 快速查看
python check_progress.py

# 实时监控
python monitor_download_progress.py
```

### 3. 生成报告

```bash
python generate_skills_report.py
```

## 💡 性能对比

| 下载方式 | 线程数 | 预计时间 | 适用场景 |
|---------|--------|---------|---------|
| **advanced_download_skills.py** | 8-10 | 5-10 小时 | ✅ 推荐：网络稳定，需要进度条 |
| **parallel_download_skills.py** | 5-10 | 8-15 小时 | 网络稳定，不需要进度条 |
| **smart_download_skills.py** | 1 | 30-70 小时 | 网络不稳定，需要重试机制 |

## 🎯 并行下载优势

1. **速度提升**: 10 线程比单线程快 5-10 倍
2. **实时反馈**: 进度条显示当前下载状态
3. **超时检测**: 自动跳过卡住的任务（120秒超时）
4. **资源优化**: 充分利用网络带宽和 CPU

## 📊 当前状态

- **总计**: 25,354 个 skills
- **数据来源**: skills.sh 官方网站
- **下载方法**: Git clone（深度=1）

## ⚠️ 注意事项

1. **磁盘空间**: 下载全部 skills 需要几十 GB 空间
2. **下载时间**: 预计需要 30-70 小时（取决于网络速度）
3. **网络稳定性**: 建议在稳定的网络环境下运行
4. **GitHub 限制**: 频繁克隆可能触发 GitHub 限制

## 🔧 故障排除

### 下载失败
- 脚本会自动跳过失败的 skills
- 可以重新运行脚本，已下载的会自动跳过

### 临时文件清理
- 脚本会自动清理 `_temp_*` 目录
- 如需手动清理：
  ```bash
  Get-ChildItem -Path "skills" -Directory -Filter "_temp_*" | Remove-Item -Recurse -Force
  ```

### 查看下载进程
如果使用后台进程下载，可以查看进程输出：
```bash
# 在 Kiro 中使用 getProcessOutput 工具
```

## 📝 更新日志

- 2025-01-26: 创建智能下载工具，支持 25,354 个 skills
- 已成功下载: 29+ skills
- 下载进程: 正在后台运行中
