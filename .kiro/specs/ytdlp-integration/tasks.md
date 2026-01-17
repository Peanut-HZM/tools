# Implementation Plan: yt-dlp Integration

## Overview

本实施计划将 yt-dlp 集成到视频下载器中，实现服务器端视频下载功能。实施分为后端集成、前端更新和测试验证三个阶段。

## Tasks

- [x] 1. 环境准备和依赖安装
  - 添加 yt-dlp 到 requirements.txt
  - 安装 ffmpeg（yt-dlp 依赖）
  - 创建临时文件目录
  - 验证 yt-dlp 安装成功
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. 实现 YtdlpService 核心服务
  - [x] 2.1 创建 ytdlp_service.py 文件
    - 实现 YtdlpDownloader 类
    - 配置 yt-dlp 默认选项
    - 实现进度回调函数
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 2.2 实现 download() 方法
    - 支持质量选择（best, 1080p, 720p, 480p）
    - 实现错误处理和重试逻辑
    - 返回下载文件路径
    - _Requirements: 2.1, 2.2, 2.4, 5.1, 5.2_

  - [x] 2.3 实现 get_formats() 方法
    - 提取视频所有可用格式
    - 解析格式信息（质量、大小、编码）
    - 返回格式列表
    - _Requirements: 4.1, 4.2_

  - [x] 2.4 实现 get_info() 方法
    - 获取视频元数据（不下载）
    - 提取标题、时长、缩略图等信息
    - 缓存视频信息
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 3. 实现 DownloadManager 任务管理
  - [x] 3.1 创建 download_manager.py 文件
    - 定义 DownloadTask 数据模型
    - 实现 DownloadManager 类
    - 初始化任务字典
    - _Requirements: 3.1, 3.2_

  - [x] 3.2 实现任务创建和管理
    - 实现 create_task() 方法
    - 生成唯一任务ID
    - 初始化任务状态
    - _Requirements: 3.1, 3.2_

  - [x] 3.3 实现异步下载任务
    - 实现 download_task() 异步方法
    - 使用后台任务执行下载
    - 更新任务进度和状态
    - _Requirements: 2.1, 2.2, 3.3, 3.4_

  - [x] 3.4 实现任务状态查询
    - 实现 get_task() 方法
    - 返回任务详细状态
    - 包含进度、速度、ETA等信息
    - _Requirements: 3.2, 3.3_

  - [x] 3.5 实现临时文件清理
    - 实现 cleanup_old_tasks() 方法
    - 定期清理超过1小时的任务
    - 删除临时文件
    - _Requirements: 7.2, 7.3, 7.4_

- [x] 4. 创建 API 端点
  - [x] 4.1 实现创建下载任务端点
    - POST /api/tools/download-video-ytdlp
    - 验证请求参数
    - 创建下载任务
    - 返回任务ID
    - _Requirements: 2.1, 4.3_

  - [x] 4.2 实现查询任务状态端点
    - GET /api/tools/download-task/{task_id}
    - 查询任务状态
    - 返回进度信息
    - _Requirements: 3.2, 3.3, 3.4_

  - [x] 4.3 实现下载文件端点
    - GET /api/tools/download-file/{task_id}
    - 验证任务已完成
    - 流式传输文件
    - 设置正确的响应头
    - _Requirements: 2.4, 8.2_

  - [x] 4.4 实现获取视频格式端点
    - GET /api/tools/video-formats
    - 提取视频格式列表
    - 返回格式信息
    - _Requirements: 4.1, 4.2_

- [ ] 5. 实现错误处理和安全限制
  - [ ] 5.1 实现 URL 验证
    - 验证 URL 协议
    - 检查本地和内网地址
    - 防止 SSRF 攻击
    - _Requirements: 6.4, 5.4_

  - [ ] 5.2 实现文件大小限制
    - 设置最大文件大小为 500MB
    - 在下载前检查文件大小
    - 超限时返回错误
    - _Requirements: 6.1_

  - [ ] 5.3 实现并发限制
    - 限制同时下载任务数为 5
    - 使用信号量控制并发
    - 队列等待机制
    - _Requirements: 6.2, 8.1_

  - [ ] 5.4 实现速率限制
    - 使用 slowapi 限制请求频率
    - 每分钟最多 10 次下载请求
    - 返回 429 错误码
    - _Requirements: 6.2_

  - [ ] 5.5 实现超时控制
    - 设置下载超时为 10 分钟
    - 超时自动取消任务
    - 清理临时文件
    - _Requirements: 6.3_

- [ ] 6. 前端集成
  - [x] 6.1 更新 VideoDownloader 组件
    - 添加"服务器下载"按钮
    - 区分 HLS 和普通视频
    - 显示下载选项
    - _Requirements: 10.1, 10.2_

  - [x] 6.2 实现下载进度显示
    - 创建进度条组件
    - 轮询任务状态
    - 显示进度百分比和速度
    - _Requirements: 3.3, 3.4, 10.3_

  - [x] 6.3 实现质量选择界面
    - 获取视频可用格式
    - 显示质量选项列表
    - 用户选择质量后开始下载
    - _Requirements: 4.2, 4.3, 10.2_

  - [x] 6.4 实现文件下载触发
    - 任务完成后自动下载
    - 使用 Blob 和 URL.createObjectURL
    - 设置正确的文件名
    - _Requirements: 10.3, 10.4_

  - [x] 6.5 实现取消下载功能
    - 添加取消按钮
    - 调用取消 API
    - 清理前端状态
    - _Requirements: 10.5_

- [ ] 7. 后台任务和清理
  - [ ] 7.1 实现后台清理任务
    - 使用 FastAPI BackgroundTasks
    - 每小时运行一次清理
    - 删除旧任务和文件
    - _Requirements: 7.2, 7.3, 7.4_

  - [ ] 7.2 实现启动时清理
    - 在应用启动时清理临时目录
    - 删除所有旧文件
    - 初始化任务管理器
    - _Requirements: 7.4_

  - [ ] 7.3 实现磁盘空间监控
    - 检查临时目录大小
    - 超过 5GB 时发出警告
    - 记录到日志
    - _Requirements: 7.5_

- [ ] 8. 日志和监控
  - [ ] 8.1 实现下载日志记录
    - 记录每次下载请求
    - 记录成功和失败情况
    - 记录错误详情
    - _Requirements: 11.1, 11.2_

  - [ ] 8.2 实现统计功能
    - 统计下载数量和大小
    - 计算平均下载时间
    - 计算成功率
    - _Requirements: 11.3, 11.4_

  - [ ] 8.3 实现统计查询接口
    - GET /api/tools/download-stats
    - 返回统计数据
    - 支持时间范围查询
    - _Requirements: 11.5_

- [ ] 9. 测试和验证
  - [ ] 9.1 单元测试
    - 测试 YtdlpDownloader 类
    - 测试 DownloadManager 类
    - 测试错误处理
    - _Requirements: All_

  - [ ] 9.2 集成测试
    - 测试 API 端点
    - 测试完整下载流程
    - 测试并发下载
    - _Requirements: All_

  - [ ] 9.3 端到端测试
    - 测试前端到后端完整流程
    - 测试进度更新
    - 测试文件下载
    - _Requirements: All_

  - [ ] 9.4 性能测试
    - 测试下载速度
    - 测试并发性能
    - 测试内存使用
    - _Requirements: 8.1, 8.2, 8.3_

- [ ] 10. 文档和部署
  - [ ] 10.1 更新 API 文档
    - 添加新端点说明
    - 添加请求/响应示例
    - 更新 OpenAPI schema
    - _Requirements: All_

  - [ ] 10.2 更新用户文档
    - 添加服务器下载使用说明
    - 更新 HLS_VIDEO_SUPPORT.md
    - 添加常见问题解答
    - _Requirements: All_

  - [ ] 10.3 更新部署文档
    - 添加 ffmpeg 安装说明
    - 添加环境变量配置
    - 更新 Docker 配置
    - _Requirements: All_

  - [ ] 10.4 验证生产环境
    - 测试 ffmpeg 可用性
    - 测试临时目录权限
    - 测试下载功能
    - _Requirements: All_

## Notes

- 任务按顺序执行，确保依赖关系正确
- 每个任务完成后进行测试验证
- 重点关注错误处理和安全性
- 保持代码简洁和可维护性
- 定期清理临时文件避免磁盘占满

## Checkpoints

- **Checkpoint 1**: 完成任务 1-3，核心下载功能可用
- **Checkpoint 2**: 完成任务 4-5，API 端点和安全限制就绪
- **Checkpoint 3**: 完成任务 6-7，前端集成和后台任务完成
- **Checkpoint 4**: 完成任务 8-10，测试、文档和部署完成

---

**创建时间**: 2024-12-28  
**状态**: 📝 任务清单  
**版本**: 1.0.0
