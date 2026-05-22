# Header 折叠功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 Header 右侧添加折叠按钮，用户可完全收起 Header 节省屏幕空间，折叠状态通过 localStorage 持久化

**Architecture:** 所有逻辑封装在 Header 组件内部，使用函数式 useState 初始化读取 localStorage，切换时同步写入，安全读写包裹在 try-catch 中。折叠时 Header 替换为 32px 迷你横条。

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Vitest (单元测试)

---

### Task 1: 编写 localStorage 安全读写工具测试

**Files:**
- Create: `frontend/src/utils/localStorage.test.ts`
- Modify: (none)

**背景：** 浏览器隐私模式下 `localStorage` 可能抛出 `SecurityError`，需要安全降级。先写测试确保工具函数行为正确。

**Step 1: 编写测试**

创建文件 `frontend/src/utils/localStorage.test.ts`：

```typescript
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
```

**Step 2: 运行测试确认失败**

```bash
cd frontend && npx vitest run src/utils/localStorage.test.ts -v
```

预期：FAIL — `Cannot find module './localStorage'`

**Step 3: 提交**

```bash
git add frontend/src/utils/localStorage.test.ts
git commit -m "test: 添加 localStorage 安全读写测试"
```

---

### Task 2: 实现 localStorage 安全读写工具

**Files:**
- Create: `frontend/src/utils/localStorage.ts`

**Step 1: 实现代码**

创建文件 `frontend/src/utils/localStorage.ts`：

```typescript
export function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}
```

**Step 2: 运行测试确认通过**

```bash
cd frontend && npx vitest run src/utils/localStorage.test.ts -v
```

预期：5 个测试全部 PASS

**Step 3: 提交**

```bash
git add frontend/src/utils/localStorage.ts
git commit -m "feat: 添加 localStorage 安全读写工具函数"
```

---

### Task 3: 在 Header 中添加折叠状态和迷你横条渲染

**Files:**
- Modify: `frontend/src/components/Header/Header.tsx`（全文件）

**背景：** 先实现折叠状态管理和折叠后的迷你横条渲染，暂不改展开 Header 部分。

**Step 1: 读取当前文件**

```bash
cat frontend/src/components/Header/Header.tsx
```

**Step 2: 修改 Header.tsx**

将文件完整替换为：

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import SearchBar from './SearchBar';
import LoginButton from './LoginButton';
import { useI18n } from '../../i18n';
import ContactModal from '../ContactModal/ContactModal';
import { useAuth } from '../../stores/authStore';
import { safeGetItem, safeSetItem } from '../../utils/localStorage';

interface HeaderProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
}

const STORAGE_KEY = 'header-collapsed';

export default function Header({ searchValue, onSearchChange, onSearch }: HeaderProps) {
  const { t, language, toggleLanguage } = useI18n();
  const { user } = useAuth();
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);

  const [isCollapsed, setIsCollapsed] = useState(() => safeGetItem(STORAGE_KEY) === 'true');

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      safeSetItem(STORAGE_KEY, String(next));
      return next;
    });
  };

  // 折叠状态：显示迷你横条
  if (isCollapsed) {
    return (
      <header className="sticky top-0 z-40 bg-slate-800 border-b border-slate-700 h-8 flex items-center justify-center">
        <button
          onClick={toggleCollapse}
          className="px-3 py-1 rounded text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          title="展开导航"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </header>
    );
  }

  // 展开状态：原始 Header（尚未添加折叠按钮，下一步添加）
  return (
    <>
      <header className="sticky top-0 z-40 bg-slate-800 border-b border-slate-700">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-10">
            <Link to="/" className="text-2xl font-['Pacifico'] text-primary" key={language}>
              {t.common.logo}
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            <SearchBar
              value={searchValue}
              onChange={onSearchChange}
              onSearch={onSearch}
            />
            {user?.role === 'admin' && (
              <Link
                to="/admin"
                className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium transition-colors cursor-pointer"
              >
                {t.nav.admin}
              </Link>
            )}
            <button
              onClick={() => setIsContactModalOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors cursor-pointer"
            >
              {t.nav.contactUs}
            </button>
            <button
              onClick={toggleLanguage}
              className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium transition-colors border border-slate-600 cursor-pointer"
              title={language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
            >
              {language === 'zh-CN' ? 'EN' : '中'}
            </button>
            <LoginButton />
          </div>
        </div>
      </header>

      {/* 联系我们弹窗 */}
      <ContactModal
        isOpen={isContactModalOpen}
        onClose={() => setIsContactModalOpen(false)}
      />
    </>
  );
}
```

**关键变更：**
1. 新增 `useState` 从 localStorage 读取折叠状态
2. 新增 `toggleCollapse` 切换函数
3. 折叠状态下渲染 32px 迷你横条（含 chevron-down 展开按钮）
4. 展开状态下保持原始 Header 不变（折叠按钮下一步添加）

**Step 3: 验证能正常编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

预期：无新增类型错误（可能有已有错误，不影响本次改动）

**Step 4: 启动前端验证（手动）**

```bash
cd frontend && npm run dev
```

- 打开浏览器访问 `http://localhost:5178`
- 确认 Header 正常显示（此时还没有折叠按钮）
- 手动在控制台执行 `localStorage.setItem('header-collapsed', 'true')` 并刷新
- 确认顶部出现 32px 迷你横条
- 点击横条中的向下箭头，确认 Header 恢复

**Step 5: 提交**

```bash
git add frontend/src/components/Header/Header.tsx
git commit -m "feat: Header 添加折叠状态管理和迷你横条渲染"
```

---

### Task 4: 在展开 Header 中添加折叠按钮

**Files:**
- Modify: `frontend/src/components/Header/Header.tsx:68-78`（展开状态的右侧按钮区域）

**Step 1: 添加折叠按钮**

在语言切换按钮和 LoginButton 之间插入折叠按钮。找到展开状态代码中的这一段：

```tsx
            <button
              onClick={toggleLanguage}
              className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium transition-colors border border-slate-600 cursor-pointer"
              title={language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
            >
              {language === 'zh-CN' ? 'EN' : '中'}
            </button>
            <LoginButton />
```

替换为：

```tsx
            <button
              onClick={toggleLanguage}
              className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium transition-colors border border-slate-600 cursor-pointer"
              title={language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
            >
              {language === 'zh-CN' ? 'EN' : '中'}
            </button>
            <button
              onClick={toggleCollapse}
              className="px-2 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm transition-colors cursor-pointer"
              title="折叠导航"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="18 15 12 9 6 15" />
              </svg>
            </button>
            <LoginButton />
```

**Step 2: 验证编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: 提交**

```bash
git add frontend/src/components/Header/Header.tsx
git commit -m "feat: Header 右侧添加折叠按钮"
```

---

### Task 5: 浏览器端到端验证

**前置条件：** 前端服务正在运行（`npm run dev`），访问 `http://localhost:5178`

**验证清单（逐项执行）：**

| # | 操作 | 预期结果 |
|---|------|----------|
| 1 | 打开首页 `http://localhost:5178` | Header 正常显示，右侧有折叠按钮（向上箭头图标） |
| 2 | 点击折叠按钮 | Header 完全收起，顶部出现 32px 迷你横条，中间有向下箭头 |
| 3 | 点击迷你横条中的向下箭头 | Header 恢复完整显示 |
| 4 | 再次点击折叠按钮，然后刷新页面 | 页面刷新后仍保持折叠状态（迷你横条） |
| 5 | 点击展开，刷新页面 | 页面刷新后 Header 保持展开 |
| 6 | 切换到工具页面 `/tools/json-formatter` | Header 状态保持一致（与首页共享 localStorage） |
| 7 | 打开浏览器开发者工具 Console | 无任何报错 |
| 8 | 在 Console 执行 `localStorage.getItem('header-collapsed')` | 折叠时返回 `'true'`，展开时返回 `'false'` |

如果任何一项失败，修复后重新验证直至全部通过。

**Step: 提交最终代码**

```bash
git status
git add frontend/src/components/Header/Header.tsx frontend/src/utils/localStorage.ts frontend/src/utils/localStorage.test.ts
git commit -m "feat: Header 折叠功能 — 折叠按钮 + localStorage 持久化 + 安全读写工具"
```
