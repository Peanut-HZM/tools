# 课程学习页面章节切换修复实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复学习页面左侧章节列表点击无法正确切换内容的问题

**Architecture:** 在 `handleSelectChapter` 函数中添加 `navigate` 调用，同步更新 URL 参数，使状态与 URL 保持一致

**Tech Stack:** React, TypeScript, react-router-dom

---

## Task 1: 修改 handleSelectChapter 函数

**Files:**
- Modify: `frontend/src/pages/CourseLearnPage.tsx:117-121`

**Step 1: 读取当前代码**

```bash
# 确认当前代码位置和内容
Read: frontend/src/pages/CourseLearnPage.tsx (lines 115-125)
```

**Step 2: 修改 handleSelectChapter 函数**

```typescript
// ===== 修改前（第 117-121 行）=====
const handleSelectChapter = (chapter: CourseChapter) => {
  setCurrentChapter(chapter);
  setShowContent('content');
  updateChapterProgress(chapter.id, 'in_progress');
};

// ===== 修改后 =====
const handleSelectChapter = (chapter: CourseChapter) => {
  setCurrentChapter(chapter);
  setShowContent('content');
  updateChapterProgress(chapter.id, 'in_progress');
  // 同步更新 URL 参数
  navigate(`/courses/${slug}/learn?chapterId=${chapter.id}`, { replace: true });
};
```

**Step 3: 验证代码编译**

```bash
# 检查前端是否热加载成功（观察终端输出）
# 或手动检查是否有编译错误
```

Expected: 无编译错误，终端显示热加载成功

**Step 4: 提交**

```bash
git add frontend/src/pages/CourseLearnPage.tsx
git commit -m "fix: 修复学习页面章节切换功能（URL 参数同步）

问题描述:
- 学习页面左侧点击其他章节时，无法正确切换内容
- 始终显示进入页面时的章节

根本原因:
- handleSelectChapter 函数只更新 React 状态，没有同步更新 URL 参数
- 导致状态与 URL 不一致

修复方案:
- 在 handleSelectChapter 中添加 navigate 调用
- 使用 { replace: true } 避免创建大量历史记录
- URL 参数更新后，useEffect 会正确触发状态更新"
```

---

## Task 2: 浏览器验证修复

**Prerequisites:** Task 1 完成且前端热加载成功

**Step 1: 打开课程学习页面**

```bash
# 使用浏览器工具打开课程中心
agent-browser open http://localhost:5178/courses
agent-browser wait --load networkidle
agent-browser snapshot -i
```

**Step 2: 点击"立即学习"进入课程详情页**

```bash
agent-browser click 'button:has-text("立即学习")'
agent-browser wait --load networkidle
agent-browser snapshot -i
```

**Step 3: 点击第 1 章"开始学习"，验证进入第 1 章**

```bash
# 点击第 1 个"开始学习"按钮
agent-browser click @e7
agent-browser wait --load networkidle

# 验证 URL 和当前章节
agent-browser eval --stdin <<'EVALEOF'
(function() {
  const url = window.location.href;
  const chapterId = new URLSearchParams(window.location.search).get('chapterId');
  const chapterButtons = document.querySelectorAll('aside button');
  let activeChapter = null;
  chapterButtons.forEach((btn, idx) => {
    if (btn.className.includes('border-cyan')) {
      activeChapter = btn.textContent.trim().substring(0, 30);
    }
  });
  return { url, chapterId, activeChapter };
})()
EVALEOF
```

Expected:
- URL 包含 `chapterId=16`（第 1 章 ID）
- 高亮章节显示"第 1 章"

**Step 4: 点击左侧第 2 章，验证切换到第 2 章**

```bash
# 获取章节列表并点击第 2 章
agent-browser snapshot -i

# 点击第 2 章按钮（根据实际 ref 调整）
agent-browser click '@eX'  # X 是第 2 章按钮的 ref
agent-browser wait 1000

# 验证 URL 和当前章节
agent-browser eval --stdin <<'EVALEOF'
(function() {
  const url = window.location.href;
  const chapterId = new URLSearchParams(window.location.search).get('chapterId');
  const chapterButtons = document.querySelectorAll('aside button');
  let activeChapter = null;
  chapterButtons.forEach((btn, idx) => {
    if (btn.className.includes('border-cyan')) {
      activeChapter = btn.textContent.trim().substring(0, 30);
    }
  });
  return { url, chapterId, activeChapter };
})()
EVALEOF
```

Expected:
- URL 包含 `chapterId=17`（第 2 章 ID）
- 高亮章节显示"第 2 章"

**Step 5: 点击左侧第 3 章，验证切换到第 3 章**

```bash
# 点击第 3 章按钮
agent-browser snapshot -i
agent-browser click '@eY'  # Y 是第 3 章按钮的 ref
agent-browser wait 1000

# 验证
agent-browser eval --stdin <<'EVALEOF'
(function() {
  return {
    url: window.location.href,
    chapterId: new URLSearchParams(window.location.search).get('chapterId')
  };
})()
EVALEOF
```

Expected:
- URL 包含 `chapterId=18`（第 3 章 ID）

**Step 6: 验证刷新保持状态**

```bash
# 刷新页面
agent-browser open $(agent-browser get url)
agent-browser wait --load networkidle
agent-browser wait 2000

# 验证当前章节
agent-browser eval --stdin <<'EVALEOF'
(function() {
  const chapterButtons = document.querySelectorAll('aside button');
  let activeChapter = null;
  chapterButtons.forEach((btn, idx) => {
    if (btn.className.includes('border-cyan')) {
      activeChapter = btn.textContent.trim().substring(0, 30);
    }
  });
  return { activeChapter, url: window.location.href };
})()
EVALEOF
```

Expected: 刷新后仍高亮显示第 3 章

**Step 7: 关闭浏览器并报告结果**

```bash
agent-browser close
```

验证清单：
- [ ] 点击第 1 章，显示第 1 章内容
- [ ] 点击第 2 章，显示第 2 章内容
- [ ] 点击第 3 章，显示第 3 章内容
- [ ] URL 参数 `chapterId` 随选择变化
- [ ] 刷新页面后仍停留在当前章节

---

## 回滚方案

如果修复后出现问题，可以回滚：

```bash
# 回滚到修复前的提交
git revert HEAD
```

或手动恢复：

```typescript
// 恢复 handleSelectChapter 函数
const handleSelectChapter = (chapter: CourseChapter) => {
  setCurrentChapter(chapter);
  setShowContent('content');
  updateChapterProgress(chapter.id, 'in_progress');
  // 移除 navigate 调用
};
```

---

## 验收标准

全部满足才算完成：
- [ ] 左侧章节列表点击能正确切换内容
- [ ] URL 参数 `chapterId` 与当前章节一致
- [ ] 刷新页面后状态保持
- [ ] 浏览器 Console 无错误
- [ ] 代码已提交到 git
