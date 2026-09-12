import { describe, it, expect } from 'vitest';
import { iconTintClass } from './iconTint';

describe('iconTintClass', () => {
  it('把后端 bg-<name>-<shade> 类名映射为 tint 类', () => {
    expect(iconTintClass('bg-blue-500')).toBe('tint tint-blue');
    expect(iconTintClass('bg-violet-500')).toBe('tint tint-violet');
    expect(iconTintClass('bg-emerald-500')).toBe('tint tint-emerald');
    expect(iconTintClass('bg-red-600')).toBe('tint tint-red');
  });
  it('未知颜色回退 violet', () => {
    expect(iconTintClass('bg-chartreuse-900')).toBe('tint tint-violet');
  });
  it('空值回退 violet', () => {
    expect(iconTintClass()).toBe('tint tint-violet');
    expect(iconTintClass('')).toBe('tint tint-violet');
  });
});
