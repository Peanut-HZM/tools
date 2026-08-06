import { describe, it, expect } from 'vitest';
import { formatCellValue } from './cellFormatter';

describe('formatCellValue', () => {
  it('整数类型原样输出', () => {
    expect(formatCellValue(123, { type: 'int(11)' })).toBe('123');
    expect(formatCellValue(42, { type: 'bigint(20)' })).toBe('42');
    expect(formatCellValue(1, { type: 'tinyint(4)' })).toBe('1');
    expect(formatCellValue(100, { type: 'INTEGER' })).toBe('100');
    expect(formatCellValue(255, { type: 'mediumint(8)' })).toBe('255');
    expect(formatCellValue(1000, { type: 'smallint(5)' })).toBe('1000');
  });

  it('整数类型不误匹配非整数类型', () => {
    // point/polygon/interval 包含 'int' 子串，但不应走整数分支
    expect(formatCellValue(3.14, { type: 'point' })).toBe('3.14');
    expect(formatCellValue(2.5, { type: 'polygon' })).toBe('2.5');
    expect(formatCellValue(1.5, { type: 'interval' })).toBe('1.5');
  });

  it('浮点类型保留原值', () => {
    expect(formatCellValue(3.14, { type: 'float' })).toBe('3.14');
    expect(formatCellValue(2.718281828, { type: 'double' })).toBe('2.718281828');
    expect(formatCellValue(1.5, { type: 'real' })).toBe('1.5');
  });

  it('decimal/numeric 按 scale 显示', () => {
    expect(formatCellValue(0.0001, { type: 'numeric(8,4)' })).toBe('0.0001');
    expect(formatCellValue(1.5, { type: 'decimal(10,2)' })).toBe('1.50');
    expect(formatCellValue(1.56789, { type: 'decimal(10,2)' })).toBe('1.57');
    expect(formatCellValue(1.5, { type: 'decimal' })).toBe('1.50');
    expect(formatCellValue(1.5, { type: 'DECIMAL(10,2)' })).toBe('1.50');
    expect(formatCellValue(1.5, { type: 'decimal(10)' })).toBe('1.50'); // 仅 precision 无 scale，默认 2
  });

  it('负数和科学计数法', () => {
    expect(formatCellValue(-42, { type: 'int(11)' })).toBe('-42');
    expect(formatCellValue(-3.14, { type: 'decimal(10,2)' })).toBe('-3.14');
    expect(formatCellValue(1e21, { type: 'int(11)' })).toBe('1e+21'); // 超大整数走科学计数法
  });

  it('未知类型不动用 toFixed', () => {
    expect(formatCellValue(42)).toBe('42');
    expect(formatCellValue(42, { type: undefined })).toBe('42');
    expect(formatCellValue(42, null)).toBe('42');
    expect(formatCellValue(42, { type: 'json' })).toBe('42');
  });

  it('非数字原样字符串化', () => {
    expect(formatCellValue('hello', { type: 'int(11)' })).toBe('hello');
    expect(formatCellValue('2025-01-01', { type: 'varchar(255)' })).toBe('2025-01-01');
    expect(formatCellValue(true, { type: 'int(11)' })).toBe('true');
  });

  it('null/undefined 返回空串', () => {
    expect(formatCellValue(null, { type: 'int(11)' })).toBe('');
    expect(formatCellValue(undefined, { type: 'int(11)' })).toBe('');
  });

  it('NaN/Infinity 走 String() 兜底', () => {
    expect(formatCellValue(NaN, { type: 'int(11)' })).toBe('NaN');
    expect(formatCellValue(Infinity, { type: 'int(11)' })).toBe('Infinity');
  });

  it('日期类型本地化', () => {
    const result = formatCellValue('2025-01-01T00:00:00Z', { type: 'datetime' });
    expect(result).not.toBe('2025-01-01T00:00:00Z');
    expect(result).toMatch(/\d{4}/);
  });

  it('timestamp 类型本地化', () => {
    const result = formatCellValue('2025-06-15T12:30:45Z', { type: 'timestamp' });
    expect(result).not.toBe('2025-06-15T12:30:45Z');
    expect(result).toMatch(/2025/);
  });

  it('无效日期字符串保持原样', () => {
    expect(formatCellValue('not-a-date', { type: 'datetime' })).toBe('not-a-date');
  });
});