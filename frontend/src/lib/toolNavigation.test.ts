import { describe, expect, it } from 'vitest';
import { getStandaloneToolPath } from './toolNavigation';

describe('getStandaloneToolPath', () => {
  it('课程和技术内容使用独立页面路由', () => {
    expect(getStandaloneToolPath('course-platform')).toBe('/courses');
    expect(getStandaloneToolPath('tech-contents')).toBe('/tech-contents');
  });

  it('专业工具留在统一工作台', () => {
    expect(getStandaloneToolPath('k8s-tool')).toBeNull();
    expect(getStandaloneToolPath('ocr-tool')).toBeNull();
  });
});
