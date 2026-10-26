/**
 * /api/v1 组路由的基址（统一出口）
 *
 * 背景：
 *   后端有两套路由挂载约定——
 *     · /api/...      例如 /api/admin（用户管理）、/api/tools/*
 *     · /api/v1/...   例如 /api/v1/admin/llm-providers、/api/v1/conversations
 *   而 .env 的 VITE_API_BASE_URL 约定是 /api（如 http://127.0.0.1:19092/api）。
 *   若 /api/v1 这组的前端文件直接用 VITE_API_BASE_URL 拼接，请求会落到
 *   /api/admin/xxx 上而后端只挂了 /api/v1/admin/xxx —— 全部 404。
 *
 * 处理：
 *   在 VITE_API_BASE_URL 基础上归一化出 /api/v1 结尾的基址：
 *   先去掉末尾斜杠，再去掉已有的 /v1，最后统一补 /v1。
 *   结果对以下输入均正确：
 *     http://127.0.0.1:19092/api        → http://127.0.0.1:19092/api/v1
 *     /api                              → /api/v1
 *     https://host/api                  → https://host/api/v1
 *     https://host/api/v1               → https://host/api/v1
 */

/** 归一化后的 /api/v1 基址 */
export const API_V1_BASE_URL = `${(
  import.meta.env.VITE_API_BASE_URL || '/api'
)
  .replace(/\/+$/, '')
  .replace(/\/v1$/, '')}/v1`;
