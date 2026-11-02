/**
 * 客户端设备标识测试
 *
 * 目的：显示偏好按设备隔离，前端必须稳定地产生并携带同一个设备标识。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getClientDeviceId,
  withDeviceId,
  DEVICE_ID_HEADER,
  DEVICE_ID_KEY,
} from './clientDevice';

describe('clientDevice', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('首次调用生成并持久化设备标识', () => {
    const id = getClientDeviceId();

    expect(id).toBeTruthy();
    expect(id.length).toBeGreaterThan(10);
    expect(localStorage.getItem(DEVICE_ID_KEY)).toBe(id);
  });

  it('多次调用返回同一个设备标识（稳定）', () => {
    const first = getClientDeviceId();
    const second = getClientDeviceId();
    const third = getClientDeviceId();

    expect(second).toBe(first);
    expect(third).toBe(first);
  });

  it('已有存储值时直接复用（刷新页面不换设备）', () => {
    localStorage.setItem(DEVICE_ID_KEY, 'preset-device-id');
    expect(getClientDeviceId()).toBe('preset-device-id');
  });

  it('withDeviceId 追加设备标识请求头', () => {
    const headers = withDeviceId({ Authorization: 'Bearer x' });

    expect(headers.Authorization).toBe('Bearer x');
    expect(headers[DEVICE_ID_HEADER]).toBe(getClientDeviceId());
  });

  it('withDeviceId 不修改传入的对象', () => {
    const original = { Authorization: 'Bearer x' };
    withDeviceId(original);

    expect(Object.keys(original)).toEqual(['Authorization']);
  });

  it('withDeviceId 支持 Headers 实例', () => {
    const headers = withDeviceId(new Headers({ 'X-Test': 'v' }));

    // Headers 会把键名规范化为小写
    expect(headers['x-test']).toBe('v');
    expect(headers[DEVICE_ID_HEADER]).toBeTruthy();
  });

  it('withDeviceId 支持数组形式的 header', () => {
    const headers = withDeviceId([['X-Test', 'v']]);

    expect(headers['X-Test']).toBe('v');
    expect(headers[DEVICE_ID_HEADER]).toBeTruthy();
  });
});
