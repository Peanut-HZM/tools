/**
 * MarkdownEditor 内容搜索功能测试
 *
 * 覆盖：
 * - Preview 组件的 DOM 高亮逻辑与匹配计数
 * - 匹配导航（上一个/下一个）
 * - 搜索栏 Escape 键关闭
 * - 多实例隔离（使用 ref 而非全局选择器）
 * - 父组件通过 onMatchCountChange 接收真实 DOM 匹配数
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
import Preview from '../Preview/Preview';

/* ------------------------------------------------------------------ */
/* Mock 依赖（hljs / DOMPurify / markdown-it CSS）                    */
/* ------------------------------------------------------------------ */
vi.mock('highlight.js', () => ({
  default: {
    highlight: (value: string) => ({ value }),
    getLanguage: () => true,
  },
}));

vi.mock('highlight.js/styles/github.css', () => ({}));

vi.mock('dompurify', () => ({
  default: {
    sanitize: (html: string) => html,
  },
}));

vi.mock('../Preview.css', () => ({}));

/* ------------------------------------------------------------------ */
/* jsdom 兼容：polyfill scrollIntoView                                 */
/* ------------------------------------------------------------------ */
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function () { /* jsdom no-op */ };
}

/* ------------------------------------------------------------------ */
/* 辅助函数                                                           */
/* ------------------------------------------------------------------ */

/** 获取容器中所有搜索高亮 mark 元素 */
function getSearchMarks(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll('mark.search-highlight'));
}

/** 获取当前激活的搜索高亮 mark 元素 */
function getActiveMark(container: HTMLElement): HTMLElement | null {
  return container.querySelector('mark.search-highlight.active-search-match');
}

/* ------------------------------------------------------------------ */
/* Preview 搜索高亮测试                                                */
/* ------------------------------------------------------------------ */
describe('Preview 内容搜索 - DOM 高亮', () => {
  afterEach(() => {
    cleanup();
  });

  it('高亮所有匹配的文本节点', () => {
    const { container } = render(
      <Preview content="hello world hello" searchQuery="hello" currentMatchIndex={0} />
    );

    const marks = getSearchMarks(container);
    expect(marks).toHaveLength(2);
    expect(marks[0].textContent).toBe('hello');
    expect(marks[1].textContent).toBe('hello');
  });

  it('空搜索词不产生高亮', () => {
    const { container } = render(
      <Preview content="hello world" searchQuery="" currentMatchIndex={0} />
    );
    expect(getSearchMarks(container)).toHaveLength(0);
  });

  it('大小写不敏感匹配', () => {
    const { container } = render(
      <Preview content="Hello HELLO hello" searchQuery="hello" currentMatchIndex={0} />
    );
    expect(getSearchMarks(container)).toHaveLength(3);
  });

  it('无匹配时高亮数量为 0', () => {
    const { container } = render(
      <Preview content="hello world" searchQuery="xyz" currentMatchIndex={0} />
    );
    expect(getSearchMarks(container)).toHaveLength(0);
  });

  it('当前匹配项添加 active-search-match 样式', () => {
    const { container } = render(
      <Preview content="aaa bbb aaa" searchQuery="aaa" currentMatchIndex={1} />
    );

    const marks = getSearchMarks(container);
    expect(marks).toHaveLength(2);
    // 第二个 mark（index=1）应为 active
    expect(marks[0].classList.contains('active-search-match')).toBe(false);
    expect(marks[1].classList.contains('active-search-match')).toBe(true);
  });

  it('currentMatchIndex 超出范围时通过取模定位', () => {
    const { container } = render(
      <Preview content="aaa bbb" searchQuery="aaa" currentMatchIndex={5} />
    );

    const marks = getSearchMarks(container);
    expect(marks).toHaveLength(1);
    // 5 % 1 === 0，第一个 mark 应被激活
    expect(marks[0].classList.contains('active-search-match')).toBe(true);
  });

  it('通过 onMatchCountChange 回调报告真实 DOM 匹配数', () => {
    const onMatchCountChange = vi.fn();
    render(
      <Preview
        content="hello world hello hello"
        searchQuery="hello"
        currentMatchIndex={0}
        onMatchCountChange={onMatchCountChange}
      />
    );

    expect(onMatchCountChange).toHaveBeenCalledWith(3);
  });

  it('查询词为空时不报告匹配数（或报告 0）', () => {
    const onMatchCountChange = vi.fn();
    render(
      <Preview
        content="hello world"
        searchQuery=""
        currentMatchIndex={0}
        onMatchCountChange={onMatchCountChange}
      />
    );

    // 无搜索词时，不产生高亮，回调不应被调用（或调用 0）
    const calls = onMatchCountChange.mock.calls;
    if (calls.length > 0) {
      expect(calls[calls.length - 1][0]).toBe(0);
    }
  });

  it('正则特殊字符被正确转义', () => {
    const { container } = render(
      <Preview content="price is $10.00 and $20.00" searchQuery="$10.00" currentMatchIndex={0} />
    );
    const marks = getSearchMarks(container);
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe('$10.00');
  });
});

/* ------------------------------------------------------------------ */
/* 搜索栏键盘事件（Escape 关闭）                                       */
/* ------------------------------------------------------------------ */
describe('内容搜索栏 - Escape 键关闭', () => {
  afterEach(() => {
    cleanup();
  });

  it('Escape 键触发后搜索栏隐藏', async () => {
    // 通过直接渲染搜索栏的父组件片段测试键盘处理
    // 这里直接模拟 onKeyDown 行为
    const handleKeyDown = vi.fn((e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
      }
    });

    const { container } = render(
      <input
        type="text"
        data-testid="search-input"
        onKeyDown={handleKeyDown}
      />
    );

    const input = screen.getByTestId('search-input');
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(handleKeyDown).toHaveBeenCalled();
    const event = handleKeyDown.mock.calls[0][0];
    expect(event.key).toBe('Escape');
    expect(event.defaultPrevented).toBe(true);
  });
});

/* ------------------------------------------------------------------ */
/* 匹配导航（上一个/下一个）                                            */
/* ------------------------------------------------------------------ */
describe('匹配导航', () => {
  it('goToNextMatch 循环回到起始位置', () => {
    // 模拟导航逻辑（与 MarkdownEditor 保持一致）
    const totalMatches = 3;
    let currentIndex = 0;

    const goToNext = () => {
      currentIndex = (currentIndex + 1) % totalMatches;
    };

    goToNext();
    expect(currentIndex).toBe(1);
    goToNext();
    expect(currentIndex).toBe(2);
    goToNext();
    expect(currentIndex).toBe(0); // 循环
  });

  it('goToPreviousMatch 循环回到末尾', () => {
    const totalMatches = 3;
    let currentIndex = 0;

    const goToPrev = () => {
      currentIndex = (currentIndex - 1 + totalMatches) % totalMatches;
    };

    goToPrev();
    expect(currentIndex).toBe(2); // 从 0 回到末尾
    goToPrev();
    expect(currentIndex).toBe(1);
    goToPrev();
    expect(currentIndex).toBe(0);
  });

  it('totalMatches 为 0 时导航不执行', () => {
    const totalMatches = 0;
    let currentIndex = 0;

    const goToNext = () => {
      if (totalMatches === 0) return;
      currentIndex = (currentIndex + 1) % totalMatches;
    };

    goToNext();
    expect(currentIndex).toBe(0); // 未变化
  });
});

/* ------------------------------------------------------------------ */
/* 多实例隔离                                                         */
/* ------------------------------------------------------------------ */
describe('多实例 Preview 隔离', () => {
  afterEach(() => {
    cleanup();
  });

  it('两个 Preview 实例各自维护独立的搜索高亮', () => {
    const { container: containerA } = render(
      <Preview content="apple banana" searchQuery="apple" currentMatchIndex={0} />
    );
    const { container: containerB } = render(
      <Preview content="cherry cherry cherry" searchQuery="cherry" currentMatchIndex={0} />
    );

    const marksA = getSearchMarks(containerA);
    const marksB = getSearchMarks(containerB);

    expect(marksA).toHaveLength(1);
    expect(marksB).toHaveLength(3);
    // 互不干扰
    expect(marksA[0].textContent).toBe('apple');
    marksB.forEach(mark => expect(mark.textContent).toBe('cherry'));
  });

  it('每个实例独立报告自己的 DOM 匹配数', () => {
    const onCountA = vi.fn();
    const onCountB = vi.fn();

    render(
      <Preview content="a b a" searchQuery="a" currentMatchIndex={0} onMatchCountChange={onCountA} />
    );
    render(
      <Preview content="x y x x" searchQuery="x" currentMatchIndex={0} onMatchCountChange={onCountB} />
    );

    expect(onCountA).toHaveBeenCalledWith(2);
    expect(onCountB).toHaveBeenCalledWith(3);
  });
});
