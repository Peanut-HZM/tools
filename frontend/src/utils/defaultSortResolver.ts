import type { TableSchema } from '../types/databaseTool';

/**
 * 创建时间字段的候选名称（全部小写，用于匹配）。
 */
const CREATE_TIME_VARIANTS = ['create_time', 'created_at', 'createtime', 'createdat'];

/**
 * 更新时间字段的候选名称（全部小写，用于匹配）。
 */
const UPDATE_TIME_VARIANTS = ['update_time', 'updated_at', 'updatetime', 'updatedat'];

/**
 * 根据表结构推算默认排序字段。
 *
 * 匹配优先级：
 * 1. 创建时间字段（create_time / created_at / createTime / createdAt）
 * 2. 更新时间字段（update_time / updated_at / updateTime / updatedAt）
 * 3. 主键列名包含 "id"（大小写不敏感）
 * 4. 均不满足则返回空字符串（保持数据库默认排序）
 *
 * 所有匹配大小写不敏感，返回时使用数据库中的原始列名。
 */
export function resolveDefaultSort(schema: TableSchema): string {
  if (!schema || !schema.columns || schema.columns.length === 0) {
    return '';
  }

  // 构造小写列名 → 原始列名的映射（取第一个命中的）
  const lowerToOriginal = new Map<string, string>();
  for (const col of schema.columns) {
    const lower = col.name.toLowerCase();
    if (!lowerToOriginal.has(lower)) {
      lowerToOriginal.set(lower, col.name);
    }
  }

  // 优先级 1：创建时间字段
  for (const variant of CREATE_TIME_VARIANTS) {
    const original = lowerToOriginal.get(variant);
    if (original) {
      return `${original} DESC`;
    }
  }

  // 优先级 2：更新时间字段
  for (const variant of UPDATE_TIME_VARIANTS) {
    const original = lowerToOriginal.get(variant);
    if (original) {
      return `${original} DESC`;
    }
  }

  // 优先级 3：主键列名包含 "id"
  if (schema.primary_key && schema.primary_key.length > 0) {
    // 在多列主键中找第一个名字包含 "id" 的列
    const matchedPk = schema.primary_key.find(pkCol => pkCol.toLowerCase().includes('id'));
    if (matchedPk) {
      return `${matchedPk} DESC`;
    }
  }

  // 优先级 4：无合适字段，保持默认
  return '';
}
