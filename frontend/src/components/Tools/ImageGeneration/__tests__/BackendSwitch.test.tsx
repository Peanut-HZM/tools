import { describe, expect, it, beforeEach } from 'vitest';
import { getBackend, setBackend } from '../BackendSwitch';

describe('BackendSwitch localStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('默认返回 selfdev', () => {
    expect(getBackend()).toBe('selfdev');
  });

  it('设置后能读取', () => {
    setBackend('dify');
    expect(getBackend()).toBe('dify');
  });

  it('设置 selfdev 后能读取', () => {
    setBackend('selfdev');
    expect(getBackend()).toBe('selfdev');
  });
});
