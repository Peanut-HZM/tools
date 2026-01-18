import './MarkdownEditor.css';
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import FileTree from './FileTree/FileTree';
import Editor from './Editor/Editor';
import Preview from './Preview/Preview';
import SearchDialog from './SearchDialog/SearchDialog';
import SettingsDialog from './SettingsDialog/SettingsDialog';
import StatusBar from './StatusBar/StatusBar';
import { useFileStore } from '../../stores/fileStore';
import { useEditorStore } from '../../stores/editorStore';
import { useConfigStore } from '../../stores/configStore';
import { useI18n } from '../../i18n';
import type { EditorConfig } from '../../types/markdownEditor';

// SVG Icons
const Icons = {
  FolderOpened: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M832 320H544l-64-64h-256c-52.9 0-96 43.1-96 96v512c0 52.9 43.1 96 96 96h608c52.9 0 96-43.1 96-96V416c0-52.9-43.1-96-96-96zm32 608H224V352h229.7l64 64H864v512z"/></svg>,
  Plus: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M480 480V128a32 32 0 0 1 64 0v352h352a32 32 0 0 1 0 64H544v352a32 32 0 0 1-64 0V544H128a32 32 0 0 1 0-64h352z"/></svg>,
  View: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M942.2 486.2C847.4 286.5 704.1 186 512 186c-192.2 0-335.4 100.5-430.2 300.3a60.3 60.3 0 0 0 0 51.5C176.6 737.5 319.9 838 512 838c192.2 0 335.4-100.5 430.2-300.3 7.7-16.2 7.7-35 0-51.5zM512 766c-161.3 0-279.4-81.8-362.7-254C232.6 339.8 350.7 258 512 258c161.3 0 279.4 81.8 362.7 254C791.5 684.2 673.4 766 512 766zm-4-430c-97.2 0-176 78.8-176 176s78.8 176 176 176 176-78.8 176-176-78.8-176-176-176zm0 288c-61.9 0-112-50.1-112-112s50.1-112 112-112 112 50.1 112 112-50.1 112-112 112z"/></svg>,
  Edit: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M257.7 752c2 0 4-.2 6-.5L431.9 722c2-.4 3.9-1.3 5.3-2.8l423.9-423.9a9.96 9.96 0 0 0 0-14.1L694.9 114.9c-1.9-1.9-4.4-2.9-7.1-2.9s-5.2 1-7.1 2.9L256.8 538.8c-1.5 1.5-2.4 3.3-2.8 5.3l-29.5 168.2a9.9 9.9 0 0 0 13.2 11.7zM687.8 170.7l148.6 148.6-35.3 35.3-148.6-148.6 35.3-35.3zM294.6 557.5L626.6 225.5l148.6 148.6-332 332-132.8 23.2 23.2-132.8z"/><path fill="currentColor" d="M832 832H192c-17.7 0-32 14.3-32 32v32c0 17.7 14.3 32 32 32h640c17.7 0 32-14.3 32-32v-32c0-17.7-14.3-32-32-32z"/></svg>,
  DocumentChecked: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M854.6 288.7L639.4 73.4c-6-6-14.2-9.4-22.7-9.4H192c-17.7 0-32 14.3-32 32v832c0 17.7 14.3 32 32 32h640c17.7 0 32-14.3 32-32V311.3c0-8.5-3.4-16.7-9.4-22.6zM602 137.8L790.2 326H602V137.8zM792 888H232V136h302v216a42 42 0 0 0 42 42h216v494z"/><path fill="currentColor" d="M512 688l-96-96-48 48 144 144 240-240-48-48-192 192z"/></svg>,
  Setting: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M924.8 625.7l-65.5-56c3.1-19 4.7-38.4 4.7-57.8s-1.6-38.8-4.7-57.8l65.5-56a32.03 32.03 0 0 0 9.3-35.2l-.9-2.6a443.74 443.74 0 0 0-79.7-137.9l-1.8-2.1a32.12 32.12 0 0 0-35.1-9.5l-81.3 28.9c-30-24.6-63.5-44-99.7-57.6l-15.7-85a32.05 32.05 0 0 0-25.8-25.7l-2.7-.5c-52.1-9.4-106.9-9.4-159 0l-2.7.5a32.05 32.05 0 0 0-25.8 25.7l-15.8 85.4a351.86 351.86 0 0 0-99 57.4l-81.9-29.1a32 32 0 0 0-35.1 9.5l-1.8 2.1a446.02 446.02 0 0 0-79.7 137.9l-.9 2.6c-4.5 12.5-.8 26.5 9.3 35.2l66.3 56.6c-3.1 18.8-4.6 38-4.6 57.1 0 19.2 1.5 38.4 4.6 57.1L99 625.5a32.03 32.03 0 0 0-9.3 35.2l.9 2.6c18.1 50.4 44.9 96.9 79.7 137.9l1.8 2.1a32.12 32.12 0 0 0 35.1 9.5l81.9-29.1c29.8 24.5 63.1 43.9 99 57.4l15.8 85.4a32.05 32.05 0 0 0 25.8 25.7l2.7.5a449.4 449.4 0 0 0 159 0l2.7-.5a32.05 32.05 0 0 0 25.8-25.7l15.7-85a350 350 0 0 0 99.7-57.6l81.3 28.9a32 32 0 0 0 35.1-9.5l1.8-2.1c34.8-41.1 61.6-87.5 79.7-137.9l.9-2.6a32.03 32.03 0 0 0-9.3-35.2zM512 714c-111.6 0-202-90.4-202-202s90.4-202 202-202 202 90.4 202 202-90.4 202-202 202z"/></svg>,
  Sunny: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M512 736c-123.7 0-224-100.3-224-224s100.3-224 224-224 224 100.3 224 224-100.3 224-224 224zm0-384c-88.4 0-160 71.6-160 160s71.6 160 160 160 160-71.6 160-160-71.6-160-160-160zm0-256c-17.7 0-32 14.3-32 32v96c0 17.7 14.3 32 32 32s32-14.3 32-32V128c0-17.7-14.3-32-32-32zm0 640c-17.7 0-32 14.3-32 32v96c0 17.7 14.3 32 32 32s32-14.3 32-32v-96c0-17.7-14.3-32-32-32zM128 512c0-17.7 14.3-32 32-32h96c17.7 0 32 14.3 32 32s-14.3 32-32 32H160c-17.7 0-32-14.3-32-32zm640 0c0-17.7 14.3-32 32-32h96c17.7 0 32 14.3 32 32s-14.3 32-32 32H800c-17.7 0-32-14.3-32-32zm-539.3-265.4c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0l67.9 67.9c12.5 12.5 12.5 32.8 0 45.3s-32.8 12.5-45.3 0l-67.9-67.9zm429.3 429.3c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0l67.9 67.9c12.5 12.5 12.5 32.8 0 45.3s-32.8 12.5-45.3 0l-67.9-67.9zM228.7 737.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l67.9 67.9c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-67.9-67.9zm429.3-429.3c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l67.9 67.9c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-67.9-67.9z"/></svg>,
  Moon: () => <svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M222.7 573.5c8.3-2.9 17.3-1.4 24.2 4.1 36 28.5 81.3 45.4 130.4 45.4 116.3 0 210.7-94.4 210.7-210.7 0-49.1-16.9-94.4-45.4-130.4-5.5-6.9-7-15.9-4.1-24.2 2.9-8.3 9.9-14.6 18.2-16.6C673 218 768 313 768 432c0 150.2-121.8 272-272 272-119 0-214-95-251.1-211.7-2-8.3 4.3-15.3 12.6-18.2zM496 832c220.9 0 400-179.1 400-400 0-79-23.2-152.8-63.3-215.3-7.5-11.7-22.7-14.8-33.8-6.9-11.2 8-13.8 23.6-5.8 35.1C824.2 291.6 840 359.3 840 432c0 189.9-154.1 344-344 344-72.7 0-140.4-15.8-192.9-46.9-11.5-8-27.1-5.4-35.1 5.8-8 11.2-4.9 26.3 6.9 33.8C343.2 808.8 417 832 496 832z"/></svg>,
};

type ViewMode = 'edit' | 'preview';

interface TocItem {
  id: string;
  text: string;
  level: number;
}

export default function MarkdownEditor() {
  const navigate = useNavigate();
  
  // Stores
  const {
    directoryTree,
    currentFile,
    currentFilePath,
    rootPath,
    hasRootPath,
    expandedNodes,
    isLoading: fileLoading,
    error: fileError,
    loadDirectoryTree,
    openFile,
    saveCurrentFile,
    createFile,
    deleteFile,
    renameFile,
    createDirectory,
    deleteDirectory,
    toggleNode,
    clearError: clearFileError,
    setRootPath,
    loadRootPath
  } = useFileStore();

  const {
    content,
    cursorLine,
    cursorColumn,
    saveStatus,
    lastSaveTime,
    isDirty,
    setContent,
    updateContent,
    setCursorPosition,
    markAsSaved,
    setSaving,
    setSaveError
  } = useEditorStore();

  const {
    config,
    loadConfig,
    saveConfig,
    updateConfig,
    setTheme
  } = useConfigStore();

  const { language, setLanguage, t } = useI18n();

  // Sync global language to editor config
  useEffect(() => {
    if (config.language !== language) {
      updateConfig({ language });
      // Debounce saving or just save? 
      // Since this happens on mount/change, we should be careful not to spam.
      // But for now, let's just update the store state. 
      // We can trigger saveConfig if needed, but maybe not strictly necessary for every toggle 
      // if we trust I18nProvider as source of truth.
      // However, if we want to persist to backend:
      // saveConfig(); 
    }
  }, [language, config.language, updateConfig]);

  // Local state
  const [viewMode, setViewMode] = useState<ViewMode>('edit'); // 'edit' or 'preview' (where preview means read-only with TOC)
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [previewWidth, setPreviewWidth] = useState(450); // For edit mode
  const [tocSidebarWidth, setTocSidebarWidth] = useState(220); // For view mode
  const [editorFlex, setEditorFlex] = useState(1);

  const [showSearch, setShowSearch] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  // Dialog states
  const [showFolderSelect, setShowFolderSelect] = useState(false);
  const [folderPathInput, setFolderPathInput] = useState('');
  const [showNewFile, setShowNewFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileFolder, setNewFileFolder] = useState('');
  
  const [isResizing, setIsResizing] = useState(false);
  const [resizeType, setResizeType] = useState<'sidebar' | 'preview' | 'toc' | null>(null);

  // TOC State
  const [documentToc, setDocumentToc] = useState<TocItem[]>([]);
  const [activeTocId, setActiveTocId] = useState('');

  // Auto-save timer ref
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Load initial data
  useEffect(() => {
    loadRootPath().then((info) => {
      if (info.exists) {
        loadDirectoryTree();
      }
    });
    loadConfig();
  }, [loadRootPath, loadDirectoryTree, loadConfig]);

  // Update editor content when file changes
  useEffect(() => {
    if (currentFile) {
      setContent(currentFile.content, true);
    }
  }, [currentFile, setContent]);

  // Generate TOC when content changes
  useEffect(() => {
    const lines = content.split('\n');
    const toc: TocItem[] = [];
    const idMap = new Map();
    
    lines.forEach((line) => {
      const match = line.match(/^(#{1,6})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        const text = match[2].trim();
        let id = text.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');
        
        if (idMap.has(id)) {
          const count = idMap.get(id);
          idMap.set(id, count + 1);
          id = `${id}-${count}`;
        } else {
          idMap.set(id, 1);
        }
        
        toc.push({ id, text, level });
      }
    });
    setDocumentToc(toc);
    if (toc.length > 0 && !activeTocId) {
      setActiveTocId(toc[0].id);
    }
  }, [content]);

  // Auto-save functionality
  useEffect(() => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    if (isDirty && currentFilePath && config.autoSaveInterval > 0) {
      autoSaveTimerRef.current = setTimeout(() => {
        handleSave();
      }, config.autoSaveInterval * 1000);
    }

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [isDirty, content, currentFilePath, config.autoSaveInterval]);

  // Handle save
  const handleSave = useCallback(async () => {
    if (!currentFilePath || !isDirty) return;

    setSaving(true);
    try {
      await saveCurrentFile(content);
      markAsSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [currentFilePath, isDirty, content, saveCurrentFile, markAsSaved, setSaving, setSaveError]);

  // Handle file select
  const handleFileSelect = useCallback(async (path: string) => {
    if (isDirty) {
      const shouldSave = window.confirm('当前文件未保存，是否保存？');
      if (shouldSave) {
        await handleSave();
      }
    }
    await openFile(path);
  }, [isDirty, handleSave, openFile]);

  // Handle Resizing
  const startResize = (type: 'sidebar' | 'preview' | 'toc') => {
    setIsResizing(true);
    setResizeType(type);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !resizeType) return;

      if (resizeType === 'sidebar') {
        const newWidth = Math.max(150, Math.min(500, e.clientX));
        setSidebarWidth(newWidth);
      } else if (resizeType === 'preview') {
        // Right side resize
        const maxPreviewWidth = window.innerWidth - sidebarWidth - 200;
        const newWidth = Math.max(100, Math.min(maxPreviewWidth, window.innerWidth - e.clientX));
        setPreviewWidth(newWidth);
      } else if (resizeType === 'toc') {
         const tocX = e.clientX - sidebarWidth - 5;
         setTocSidebarWidth(Math.max(150, Math.min(400, tocX)));
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      setResizeType(null);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, resizeType, sidebarWidth]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        setShowSearch(true);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === ',') {
        e.preventDefault();
        setShowSettings(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  // Handlers for Header Actions
  const handleOpenFolder = async () => {
    if (!folderPathInput) return;
    
    // Close dialog immediately to show loading state clearly
    setShowFolderSelect(false);
    
    try {
      await setRootPath(folderPathInput);
      await loadDirectoryTree();
      setFolderPathInput('');
    } catch (e) {
      console.error(e);
      // Re-open dialog if failed so user can try again
      setShowFolderSelect(true);
      alert('Failed to open folder: ' + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleCreateFile = async () => {
    if (!newFileName) return;
    let fileName = newFileName;
    if (!fileName.endsWith('.md') && !fileName.endsWith('.markdown')) {
      fileName += '.md';
    }
    
    // Combine folder and filename
    let fullPath = fileName;
    if (newFileFolder) {
      // Ensure folder ends with / or use a join helper. 
      // Backend expects relative path from root.
      // If folder is "foo", fullPath should be "foo/bar.md"
      // Remove leading/trailing slashes from folder just in case, but keep internal structure
      const cleanFolder = newFileFolder.replace(/^\/+|\/+$/g, '');
      if (cleanFolder) {
        fullPath = `${cleanFolder}/${fileName}`;
      }
    }

    try {
      await createFile(fullPath);
      setShowNewFile(false);
      setNewFileName('');
      setNewFileFolder('');
    } catch (e) {
      console.error(e);
      alert('Failed to create file: ' + (e instanceof Error ? e.message : String(e)));
    }
  };

  const openNewFileDialog = () => {
    // Determine default folder based on current file
    let defaultFolder = '';
    if (currentFilePath) {
      // Get directory of current file
      const parts = currentFilePath.split('/');
      if (parts.length > 1) {
        parts.pop(); // Remove filename
        defaultFolder = parts.join('/');
      }
    }
    setNewFileFolder(defaultFolder);
    setShowNewFile(true);
  };

  const toggleTheme = () => {
    const newTheme = config.theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    saveConfig();
  };

  const scrollToSection = (id: string) => {
    setActiveTocId(id);
    // Note: This relies on Preview rendering IDs. simpleMarkdownToHtml doesn't currently do that.
    // We would need to update Preview to support IDs for this to work perfectly.
    // For now, it's a placeholder.
    const element = document.getElementById(id);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const isDark = config.theme === 'dark';

  return (
    <div className={`markdown-editor-container ${isDark ? 'dark-theme' : ''}`}>
      {/* Header */}
      <div className="header">
        <div className="header-left">
          <h1>{t.editor.title}</h1>
        </div>
        <div className="header-right">
          <div className="neon-button-group">
            <button className="neon-button" onClick={() => setShowFolderSelect(true)}>
              <Icons.FolderOpened />
              {t.common.openFolder || 'Open Folder'}
            </button>
            <button className="neon-button" onClick={openNewFileDialog} disabled={!hasRootPath}>
              <Icons.Plus />
              {t.common.new || 'New'}
            </button>
          </div>

          {currentFile && (
            <div className="neon-button-group">
              <button 
                className={`neon-button ${viewMode === 'preview' ? 'primary' : ''}`}
                onClick={() => setViewMode('preview')}
              >
                <Icons.View />
                {t.editor.preview}
              </button>
              <button 
                className={`neon-button ${viewMode === 'edit' ? 'primary' : ''}`}
                onClick={() => setViewMode('edit')}
              >
                <Icons.Edit />
                {t.editor.edit}
              </button>
            </div>
          )}

          {viewMode === 'edit' && (
            <button className="neon-button" onClick={handleSave} disabled={!isDirty || !currentFile}>
              <Icons.DocumentChecked />
              {t.common.save}
            </button>
          )}

          <button className="neon-button icon-only" onClick={toggleTheme} title={t.settings.theme}>
            {isDark ? <Icons.Sunny /> : <Icons.Moon />}
          </button>

          <button className="neon-button icon-only" onClick={() => setShowSettings(true)} title={t.common.settings}>
            <Icons.Setting />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Sidebar */}
        <div className="sidebar" style={{ width: sidebarWidth }}>
          {!hasRootPath ? (
            <div className="no-folder-state">
              <p>{t.editor.selectFile}</p>
              <button className="neon-button primary" onClick={() => setShowFolderSelect(true)}>
                <Icons.FolderOpened />
                {t.common.openFolder || 'Open Folder'}
              </button>
            </div>
          ) : (
            <FileTree
              tree={directoryTree}
              currentFilePath={currentFilePath}
              expandedNodes={expandedNodes}
              onFileSelect={handleFileSelect}
              onToggleNode={toggleNode}
              onCreateFile={createFile}
              onCreateDirectory={createDirectory}
              onDeleteFile={deleteFile}
              onDeleteDirectory={deleteDirectory}
              onRenameFile={renameFile}
            />
          )}
        </div>

        <div className="resize-handle" onMouseDown={() => startResize('sidebar')} />

        {/* Content Area */}
        {viewMode === 'preview' ? (
          // View Mode: TOC + Preview
          <div className="content-area view-mode">
             {currentFile ? (
               <div className="view-mode-container">
                 <div className="toc-sidebar" style={{ width: tocSidebarWidth }}>
                   <div className="toc-sidebar-header">
                     <span>{t.search?.results || 'CONTENTS'}</span>
                   </div>
                   <div className="toc-sidebar-content">
                      {documentToc.length > 0 ? (
                        <ul className="toc-nav-list">
                          {documentToc.map(item => (
                            <li 
                              key={item.id}
                              className={`toc-nav-item toc-level-${item.level} ${activeTocId === item.id ? 'active' : ''}`}
                              onClick={() => scrollToSection(item.id)}
                            >
                              {item.text}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <div className="toc-empty">{t.search?.noResults || 'No headings'}</div>
                      )}
                   </div>
                 </div>
                 
                 <div className="resize-handle toc-resize" onMouseDown={() => startResize('toc')} />
                 
                 <div className="preview-full">
                    <Preview content={content} theme={config.theme} />
                 </div>
               </div>
             ) : (
               <div className="empty-state">
                 <p>{hasRootPath ? t.editor.selectFile : t.editor.selectFile}</p>
               </div>
             )}
          </div>
        ) : (
          // Edit Mode: Editor + Preview (Resizable)
          <>
            <div className="editor-area" style={{ flex: 1 }}>
               {currentFile ? (
                 <Editor
                   content={content}
                   config={config}
                   onChange={updateContent}
                   onSave={handleSave}
                   onCursorChange={setCursorPosition}
                 />
               ) : (
                 <div className="empty-state">
                   <p>{hasRootPath ? t.editor.selectFile : t.editor.selectFile}</p>
                 </div>
               )}
            </div>
            
            <div className="resize-handle" onMouseDown={() => startResize('preview')} />
            
            <div className="preview-area" style={{ width: previewWidth }}>
              <Preview content={content} theme={config.theme} />
            </div>
          </>
        )}
      </div>

      {/* Status Bar */}
      <div className="status-bar">
         {rootPath && (
           <span className="status-item">
             📂 {rootPath}
           </span>
         )}
         <span className="status-item">
           {currentFilePath || t.fileTree.noFiles}
         </span>
         <span className={`status-item mode-indicator ${viewMode === 'edit' ? 'edit-mode' : ''}`}>
           {viewMode === 'edit' ? t.editor.edit.toUpperCase() : t.editor.preview.toUpperCase()}
         </span>
         {viewMode === 'edit' && (
           <>
             <span className="status-item">{t.search.line} {cursorLine}, Col {cursorColumn}</span>
             <span className={`status-item status-${saveStatus}`}>
               {saveStatus === 'saved' ? t.common.success : saveStatus === 'unsaved' ? t.editor.unsavedChanges : saveStatus === 'saving' ? t.common.loading : ''}
             </span>
           </>
         )}
      </div>

      {/* Dialogs */}
      <SearchDialog
        open={showSearch}
        onClose={() => setShowSearch(false)}
        onFileSelect={handleFileSelect}
      />

      <SettingsDialog
        open={showSettings}
        onClose={() => setShowSettings(false)}
        config={config}
        onConfigChange={updateConfig}
        onSave={saveConfig}
      />

      {/* Open Folder Dialog Overlay */}
      {showFolderSelect && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className={`bg-card p-6 rounded-lg w-[500px] border border-slate-700 shadow-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-white text-black'}`}>
            <h2 className="text-xl font-bold mb-4">{t.common.openFolder || 'Open Folder'}</h2>
            <div className="mb-4">
              <label className="block text-sm mb-2 text-slate-400">Folder Path</label>
              <input 
                type="text" 
                value={folderPathInput}
                onChange={(e) => setFolderPathInput(e.target.value)}
                placeholder="C:\path\to\folder"
                className="w-full p-2 rounded bg-slate-900 border border-slate-700 focus:border-cyan-500 outline-none text-white"
              />
              <p className="text-xs text-slate-500 mt-2">Enter absolute path to folder</p>
            </div>
            <div className="flex justify-end gap-2">
              <button 
                onClick={() => setShowFolderSelect(false)}
                className="px-4 py-2 rounded text-slate-400 hover:text-white"
              >
                {t.common.cancel}
              </button>
              <button 
                onClick={handleOpenFolder}
                className="px-4 py-2 rounded bg-cyan-500 text-white hover:bg-cyan-600"
              >
                {t.common.confirm}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New File Dialog Overlay */}
      {showNewFile && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className={`bg-card p-6 rounded-lg w-[400px] border border-slate-700 shadow-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-white text-black'}`}>
            <h2 className="text-xl font-bold mb-4">{t.fileTree.newFile}</h2>
            <div className="mb-4">
              <label className="block text-sm mb-2 text-slate-400">{t.common.folderName || 'Folder'}</label>
              <input 
                type="text" 
                value={newFileFolder}
                onChange={(e) => setNewFileFolder(e.target.value)}
                placeholder="e.g. docs/guides (leave empty for root)"
                className="w-full p-2 rounded bg-slate-900 border border-slate-700 focus:border-cyan-500 outline-none text-white"
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm mb-2 text-slate-400">{t.common.fileName || 'File Name'}</label>
              <input 
                type="text" 
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                placeholder="example.md"
                className="w-full p-2 rounded bg-slate-900 border border-slate-700 focus:border-cyan-500 outline-none text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button 
                onClick={() => setShowNewFile(false)}
                className="px-4 py-2 rounded text-slate-400 hover:text-white"
              >
                {t.common.cancel}
              </button>
              <button 
                onClick={handleCreateFile}
                className="px-4 py-2 rounded bg-cyan-500 text-white hover:bg-cyan-600"
              >
                {t.common.create}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {fileError && (
        <div className="fixed bottom-20 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {fileError}
          <button
            onClick={clearFileError}
            className="ml-2 text-white/80 hover:text-white cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Loading Overlay */}
      {fileLoading && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-[60]">
          <div className="bg-slate-800 rounded-lg p-4 flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-cyan-500" />
            <span className="text-white">{t.common.loading}</span>
          </div>
        </div>
      )}
    </div>
  );
}
