/**
 * 带鉴权拦截的 fetch 封装
 * 当接口返回 401 时，自动触发全局登录弹窗
 */

export type AuthFailureHandler = () => void;

let authFailureHandler: AuthFailureHandler | null = null;

/**
 * 注册 401 失败回调（由 App 挂载时调用一次）
 * 同时暴露给 axios 拦截器使用
 */
export function registerAuthFailureHandler(handler: AuthFailureHandler): void {
  authFailureHandler = handler;
  // 挂载到全局，供 axios 拦截器访问
  (window as any).__authFailureHandler = handler;
}

/**
 * 带鉴权的 fetch 封装
 * - 自动附加 Authorization header（若 token 存在）
 * - 响应 401 时触发登录弹窗
 */
export async function authedFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401 && authFailureHandler) {
    authFailureHandler();
  }
  return response;
}
