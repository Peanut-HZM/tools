/**
 * 单元格格式化工具：按列类型差异化展示数据库字段值。
 * 替代旧的 formatNumericValue / formatDateTimeValue 双函数方案。
 */

const SCALE_RE = /(?:decimal|numeric)\s*\(\s*\d+\s*,\s*(\d+)\s*\)/i;
const DATE_TYPES = new Set(['date', 'datetime']);
const TIMESTAMP_RE = /timestamp/i;

/** 列类型的最小可读信息 */
export interface ColumnTypeInfo {
  type?: string;
}

/** 从列类型字符串提取 decimal/numeric 的 scale，未匹配返回 null */
function extractScale(type: string | undefined): number | null {
  if (!type) return null;
  const m = type.match(SCALE_RE);
  return m ? Number(m[1]) : null;
}

/** 判断是否为日期时间类型 */
function isDateTimeType(type: string | undefined): boolean {
  if (!type) return false;
  const t = type.toLowerCase().trim();
  return DATE_TYPES.has(t) || TIMESTAMP_RE.test(t);
}

/**
 * 将数据库字段值格式化为展示字符串。
 *
 * 规则：
 * - null/undefined → ''（外层仍渲染 "NULL" 文案）
 * - 非 number 原样字符串化；日期类型额外本地化
 * - 整数类型（int/bigint 等）原样输出
 * - 浮点类型（float/double/real）原样输出
 * - decimal/numeric 按 (p,s) 括号中的 s 调用 toFixed；无括号默认 scale=2
 * - 其他未知类型原样输出（不调用 toFixed）
 */
export function formatCellValue(value: unknown, colDef?: ColumnTypeInfo | null): string {
  if (value === null || value === undefined) return '';

  if (typeof value !== 'number') {
    const str = String(value);
    if (isDateTimeType(colDef?.type)) {
      const date = new Date(str);
      if (!isNaN(date.getTime())) {
        return date.toLocaleString('zh-CN');
      }
    }
    return str;
  }

  // number 分支
  if (!isFinite(value)) return String(value);

  const type = colDef?.type?.toLowerCase();
  if (!type) return value.toString();

  // 整数类型（精确匹配，避免误匹配 point/polygon/interval 等）
  if (/\b(?:tiny|small|medium|big)?int(?:eger)?\b/i.test(type)) return value.toString();

  // 浮点类型
  if (/float|double|real/.test(type)) return value.toString();

  // decimal / numeric
  if (/decimal|numeric/.test(type)) {
    const scale = extractScale(type) ?? 2;
    return value.toFixed(scale);
  }

  // 其他未知类型，原样输出
  return value.toString();
}