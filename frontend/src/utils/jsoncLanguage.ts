/**
 * JSONC 文件支持
 *
 * 背景：
 * - Monaco 内置的 `json` 语言服务默认 `comments: 'error'`、
 *   `trailingCommas: 'error'`，会把 JSONC（JSON with Comments）文件里的
 *   行注释、块注释与尾逗号标成红波浪线。
 * - `opencode.jsonc`、VSCode `settings.json` / `tsconfig.json` 等配置文件
 *   本身就是 JSONC 格式，必须容忍注释与尾逗号。
 *
 * 方案：
 * `.jsonc` 复用 Monaco 内置 `json` 语言（语法高亮、补全、折叠全部保留，
 * tokenization 本身已支持注释 token），仅在打开 JSONC 文件时把 JSON
 * 诊断中的注释与尾逗号降级为 `ignore`；关闭/切走后恢复严格校验，
 * 使普通 `.json` 文件的严格报错行为不受影响。
 */

/** JSONC 诊断配置（注释与尾逗号合法） */
const JSONC_DIAGNOSTICS = { comments: 'ignore', trailingCommas: 'ignore' } as const;

/** 严格 JSON 诊断配置（Monaco 默认值，用于恢复） */
const STRICT_JSON_DIAGNOSTICS = { comments: 'error', trailingCommas: 'error' } as const;

/** Monaco JSON 语言配置接口（仅声明本模块用到的部分） */
interface MonacoJsonDefaults {
  setDiagnosticsOptions: (options: Record<string, unknown>) => void;
}

interface MonacoLike {
  languages?: {
    json?: { jsonDefaults?: MonacoJsonDefaults };
  };
}

/** 当前诊断配置是否处于 JSONC 宽松模式 */
let jsoncMode = false;

/**
 * 获取 Monaco 的 JSON 语言配置入口
 *
 * @param monaco - Monaco 实例（@monaco-editor/react 的 useMonaco() 返回值）
 * @returns jsonDefaults；Monaco 未暴露时返回 null
 */
function getJsonDefaults(monaco: unknown): MonacoJsonDefaults | null {
  const defaults = (monaco as MonacoLike | null)?.languages?.json?.jsonDefaults;
  return defaults?.setDiagnosticsOptions ? defaults : null;
}

/**
 * 打开 JSONC 文件时调用：放开 JSON 注释与尾逗号诊断
 *
 * 重复调用安全（幂等）。Monaco 未就绪或未暴露 jsonDefaults 时静默跳过，
 * 不影响文件内容的正常显示与编辑。
 *
 * @param monaco - Monaco 实例
 */
export function enableJsoncDiagnostics(monaco: unknown): void {
  const defaults = getJsonDefaults(monaco);
  if (!defaults) return;
  defaults.setDiagnosticsOptions({ ...JSONC_DIAGNOSTICS });
  jsoncMode = true;
}

/**
 * 离开 JSONC 文件（关闭/切换到其他文件）时调用：恢复严格 JSON 校验
 *
 * @param monaco - Monaco 实例
 */
export function restoreStrictJsonDiagnostics(monaco: unknown): void {
  if (!jsoncMode) return;
  const defaults = getJsonDefaults(monaco);
  if (!defaults) return;
  defaults.setDiagnosticsOptions({ ...STRICT_JSON_DIAGNOSTICS });
  jsoncMode = false;
}

/**
 * 判断文件是否为 JSONC 文件
 *
 * @param filePath - 文件路径或文件名
 */
export function isJsoncFile(filePath: string): boolean {
  return filePath.toLowerCase().endsWith('.jsonc');
}
