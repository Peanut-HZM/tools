import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { safeGetItem, safeSetItem } from './localStorage';

describe('safeGetItem', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('返回值存在时返回正确值', () => {
    localStorage.setItem('test-key', 'test-value');
    expect(safeGetItem('test-key')).toBe('test-value');
  });

  it('值不存在时返回 null', () => {
    expect(safeGetItem('non-existent')).toBeNull();
  });

  it('localStorage 抛出异常时返回 null', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    expect(safeGetItem('any-key')).toBeNull();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
});

describe('safeSetItem', () => {
  it('正常写入返回 true', () => {
    expect(safeSetItem('key', 'value')).toBe(true);
    expect(localStorage.getItem('key')).toBe('value');
  });

  it('localStorage 抛出异常时返回 false', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    expect(safeSetItem('key', 'value')).toBe(false);
    vi.restoreAllMocks();
  });
});
