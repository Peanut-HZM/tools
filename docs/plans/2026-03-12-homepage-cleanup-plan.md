# 首页底部区域清理实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 清理用户端首页底部无用区域，简化 Footer 设计

**Architecture:** 直接删除无用组件文件，修改 App.tsx 和 Footer.tsx

**Tech Stack:** React, TypeScript, Tailwind CSS

---

## Task 1: 删除无用组件文件

**Files:**
- Delete: `frontend/src/components/Features/Features.tsx`
- Delete: `frontend/src/components/Features/FeatureItem.tsx`
- Delete: `frontend/src/components/Recommendations/Recommendations.tsx`

**Step 1: 删除 Features 目录**

```bash
rm frontend/src/components/Features/Features.tsx
rm frontend/src/components/Features/FeatureItem.tsx
# 如果目录为空，删除目录
rmdir frontend/src/components/Features 2>/dev/null || true
```

**Step 2: 删除 Recommendations 文件**

```bash
rm frontend/src/components/Recommendations/Recommendations.tsx
```

**Step 3: 验证文件已删除**

```bash
ls frontend/src/components/Features/ 2>&1 || echo "Features 目录已删除"
ls frontend/src/components/Recommendations/Recommendations.tsx 2>&1 || echo "Recommendations.tsx 已删除"
```

Expected: 文件不存在

---

## Task 2: 修改 App.tsx

**Files:**
- Modify: `frontend/src/App.tsx:1-10`

**Step 1: 读取当前代码确认位置**

```bash
# 确认导入位置（第 4-7 行附近）
Read: frontend/src/App.tsx (lines 1-15)
```

**Step 2: 移除 Features 和 Recommendations 导入**

```tsx
// ===== 修改前（第 4-7 行）=====
import Header from './components/Header/Header';
import Hero from './components/Hero/Hero';
import Features from './components/Features/Features';           // ← 删除
import Statistics from './components/Statistics/Statistics';
import Recommendations from './components/Recommendations/Recommendations'; // ← 删除

// ===== 修改后 =====
import Header from './components/Header/Header';
import Hero from './components/Hero/Hero';
import Statistics from './components/Statistics/Statistics';
```

**Step 3: 移除组件渲染**

```tsx
// ===== 修改前（第 217-227 行附近）=====
          <Hero
            activeCategory={activeCategory}
            onCategoryChange={handleCategoryChange}
            tools={filteredTools}
            onToolClick={handleToolClick}
            categories={categories}
          />
          <Features />           // ← 删除
          <Statistics />
          <Recommendations />    // ← 删除

// ===== 修改后 =====
          <Hero
            activeCategory={activeCategory}
            onCategoryChange={handleCategoryChange}
            tools={filteredTools}
            onToolClick={handleToolClick}
            categories={categories}
          />
          <Statistics />
```

**Step 4: 验证代码编译**

```bash
# 观察前端终端，确认无编译错误
```

Expected: 无编译错误

**Step 5: 提交**

```bash
git add frontend/src/App.tsx
git add frontend/src/components/Features
git add frontend/src/components/Recommendations
git commit -m "refactor: 移除首页无用组件（Features 和 Recommendations）

- 删除 Features 组件（为什么选择区域）
- 删除 Recommendations 组件（技术分析区域）
- 移除相关导入和渲染
- 首页现在只显示 Hero 和 Statistics"
```

---

## Task 3: 简化 Footer 组件

**Files:**
- Modify: `frontend/src/components/Footer/Footer.tsx:1-45`

**Step 1: 读取当前代码**

```bash
Read: frontend/src/components/Footer/Footer.tsx
```

**Step 2: 重写 Footer 组件**

```tsx
// ===== 完整替换 =====
import { useI18n } from '../../i18n';

export default function Footer() {
  const { t } = useI18n();

  return (
    <footer className="bg-slate-800 border-t border-slate-700">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between text-sm text-slate-400">
          <div className="text-xl font-['Pacifico'] text-primary">{t.common.tools}</div>
          <p>{t.footer.copyright}</p>
        </div>
      </div>
    </footer>
  );
}
```

**变更说明：**
- 移除 `useState` 导入
- 移除 `ContactModal` 导入
- 移除 `isContactModalOpen` 状态
- 移除"联系我们"按钮
- 移除版权信息单独区域
- 移除弹窗组件
- padding 从 `py-8` 改为 `py-4`
- 布局从两行改为单行

**Step 3: 验证代码编译**

```bash
# 观察前端终端，确认无编译错误
```

Expected: 无编译错误

**Step 4: 提交**

```bash
git add frontend/src/components/Footer/Footer.tsx
git commit -m "style: 简化 Footer 为单行布局

变更内容:
- 从两行布局改为单行 flex 布局
- 移除"联系我们"按钮（Header 已有）
- 移除 ContactModal 弹窗代码
- padding 从 py-8 减少到 py-4
- Logo 和版权信息在同一行显示

视觉效果:
- Footer 高度明显降低
- 视觉上更简洁
- 减少页面垂直空间占用"
```

---

## Task 4: 浏览器验证

**Prerequisites:** Task 1-3 完成且前端热加载成功

**Step 1: 打开首页**

```bash
agent-browser open http://localhost:5178
agent-browser wait --load networkidle
agent-browser screenshot --full homepage-after.png
```

**Step 2: 验证页面结构**

```bash
agent-browser eval --stdin <<'EVALEOF'
(function() {
  // 检查是否存在 Features 区域
  const featuresSection = document.evaluate(
    '//h2[contains(text(), "为什么选择")]',
    document,
    null,
    XPathResult.FIRST_ORDERED_NODE_TYPE,
    null
  ).singleNodeValue;

  // 检查是否存在技术分析区域
  const techSection = document.evaluate(
    '//h2[contains(text(), "技术分析")]',
    document,
    null,
    XPathResult.FIRST_ORDERED_NODE_TYPE,
    null
  ).singleNodeValue;

  // 获取 Footer 高度
  const footer = document.querySelector('footer');
  const footerHeight = footer ? footer.offsetHeight : 0;

  // 检查是否有"联系我们"按钮在 Footer 中
  const contactBtnInFooter = footer?.textContent.includes('联系我们');

  return {
    hasFeatures: !!featuresSection,
    hasTechSection: !!techSection,
    footerHeight: footerHeight,
    hasContactBtnInFooter: !!contactBtnInFooter
  };
})()
EVALEOF
```

Expected:
- `hasFeatures: false`
- `hasTechSection: false`
- `hasContactBtnInFooter: false`
- `footerHeight` 明显小于之前的值（理想情况 < 100px）

**Step 3: 验证 Statistics 区域仍存在**

```bash
agent-browser eval --stdin <<'EVALEOF'
(function() {
  const statsSection = document.querySelector('.statistics') ||
                       document.querySelector('[class*="Statistics"]') ||
                       document.evaluate(
                         '//*[contains(text(), "累计服务") or contains(text(), "用户")]',
                         document,
                         null,
                         XPathResult.FIRST_ORDERED_NODE_TYPE,
                         null
                       ).singleNodeValue;
  return { hasStats: !!statsSection };
})()
EVALEOF
```

Expected: `hasStats: true`

**Step 4: 关闭浏览器**

```bash
agent-browser close
```

---

## 验收标准

全部满足才算完成：
- [ ] Features 组件文件已删除
- [ ] Recommendations 组件文件已删除
- [ ] App.tsx 移除了相关导入和渲染
- [ ] Footer 简化为单行布局
- [ ] Footer 无"联系我们"按钮
- [ ] 首页正常渲染（无报错）
- [ ] Statistics 区域仍显示
- [ ] Footer 高度明显降低
- [ ] 代码已提交到 git

---

## 回滚方案

如果清理后出现问题：

```bash
# 回滚最后一个提交
git revert HEAD

# 或者恢复到清理前的状态
git checkout HEAD~3 -- frontend/
```
