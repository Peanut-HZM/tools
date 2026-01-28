import React, { useState } from 'react';
import { DatabaseToolProvider } from '../../../contexts/DatabaseToolContext';
import ConnectionList from './components/ConnectionList';
import SQLExecutor from './SQLExecutor';
import DatabaseConfigPanel from './DatabaseConfigPanel';
import TableDataViewer from './TableDataViewer';

interface Tab {
  id: string;
  type: 'sql' | 'table';
  title: string;
  data?: {
    configId: string;
    databaseName?: string;
    tableName: string;
  };
}

const DatabaseToolContent: React.FC = () => {
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [editConfigId, setEditConfigId] = useState<string | null>(null);
  
  // Tab Management State
  const [tabs, setTabs] = useState<Tab[]>([
    { id: 'sql-console', type: 'sql', title: 'SQL Console' }
  ]);
  const [activeTabId, setActiveTabId] = useState<string>('sql-console');

  const handleAddConfig = () => {
    setEditConfigId(null);
    setShowConfigPanel(true);
  };

  const handleEditConfig = (id: string) => {
    setEditConfigId(id);
    setShowConfigPanel(true);
  };

  const handleClosePanel = () => {
    setShowConfigPanel(false);
    setEditConfigId(null);
  };

  const handleSelectTable = (configId: string, databaseName: string | undefined, tableName: string) => {
    const tabId = `table-${configId}-${databaseName || ''}-${tableName}`;
    
    // Check if tab exists
    const existingTab = tabs.find(t => t.id === tabId);
    if (existingTab) {
      setActiveTabId(tabId);
    } else {
      const newTab: Tab = {
        id: tabId,
        type: 'table',
        title: tableName,
        data: { configId, databaseName, tableName }
      };
      setTabs(prev => [...prev, newTab]);
      setActiveTabId(tabId);
    }
  };

  const handleCloseTab = (e: React.MouseEvent, tabId: string) => {
    e.stopPropagation();
    
    // Don't close the last tab if it's SQL Console? 
    // Or allow closing everything and show a placeholder?
    // User request implies persistence, so maybe keep SQL Console always open or easy to reopen.
    // Let's allow closing, but if all closed, maybe show SQL Console or empty state.
    
    const newTabs = tabs.filter(t => t.id !== tabId);
    setTabs(newTabs);
    
    if (activeTabId === tabId) {
      // If we closed the active tab, switch to the last available tab
      if (newTabs.length > 0) {
        setActiveTabId(newTabs[newTabs.length - 1].id);
      } else {
        // If no tabs left, open SQL Console by default
        const defaultTab: Tab = { id: 'sql-console', type: 'sql', title: 'SQL Console' };
        setTabs([defaultTab]);
        setActiveTabId(defaultTab.id);
      }
    }
  };

  const handleTabClick = (tabId: string) => {
    setActiveTabId(tabId);
  };
  
  const handleOpenSqlConsole = () => {
      const tabId = 'sql-console';
      const existingTab = tabs.find(t => t.id === tabId);
      if (existingTab) {
          setActiveTabId(tabId);
      } else {
          const newTab: Tab = { id: tabId, type: 'sql', title: 'SQL Console' };
          setTabs(prev => [...prev, newTab]);
          setActiveTabId(tabId);
      }
  };

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-slate-900 text-slate-100">
      <ConnectionList 
        onAddConfig={handleAddConfig} 
        onEditConfig={handleEditConfig} 
        onSelectTable={handleSelectTable}
        onOpenSqlConsole={handleOpenSqlConsole}
      />
      
      <div className="flex-1 min-w-0 flex flex-col h-full overflow-hidden bg-slate-900">
        {/* Tab Bar */}
        <div className="flex items-center bg-slate-800 border-b border-slate-700 overflow-x-auto no-scrollbar">
          {tabs.map(tab => (
            <div
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={`
                group flex items-center space-x-2 px-4 py-2 border-r border-slate-700 cursor-pointer min-w-[120px] max-w-[200px]
                ${activeTabId === tab.id ? 'bg-slate-900 text-blue-400 border-t-2 border-t-blue-500' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 border-t-2 border-t-transparent'}
              `}
            >
              <i className={`fas ${tab.type === 'sql' ? 'fa-terminal' : 'fa-table'} text-xs`}></i>
              <span className="text-sm truncate flex-1" title={tab.title}>{tab.title}</span>
              <button
                onClick={(e) => handleCloseTab(e, tab.id)}
                className="opacity-0 group-hover:opacity-100 hover:text-red-400 focus:outline-none transition-opacity px-1"
              >
                <i className="fas fa-times text-xs"></i>
              </button>
            </div>
          ))}
          {/* Add SQL Console Button if not present? Or just rely on ConnectionList */}
          {!tabs.find(t => t.id === 'sql-console') && (
              <button 
                onClick={handleOpenSqlConsole}
                className="px-3 py-2 text-slate-500 hover:text-slate-300 transition-colors"
                title="Open SQL Console"
              >
                  <i className="fas fa-plus"></i>
              </button>
          )}
        </div>

        {/* Tab Content Area */}
        <div className="flex-1 overflow-hidden relative">
          {tabs.map(tab => (
            <div 
              key={tab.id} 
              className="absolute inset-0 w-full h-full bg-slate-900"
              style={{ 
                display: activeTabId === tab.id ? 'block' : 'none',
                visibility: activeTabId === tab.id ? 'visible' : 'hidden' // Double ensure
              }}
            >
              {tab.type === 'sql' ? (
                <SQLExecutor />
              ) : (
                tab.data && (
                  <TableDataViewer 
                    configId={tab.data.configId}
                    databaseName={tab.data.databaseName}
                    tableName={tab.data.tableName}
                  />
                )
              )}
            </div>
          ))}
          
          {tabs.length === 0 && (
             <div className="h-full flex flex-col items-center justify-center text-slate-500">
                <i className="fas fa-database text-4xl mb-4 opacity-30"></i>
                <p>Select a table or open SQL Console</p>
                <button 
                    onClick={handleOpenSqlConsole}
                    className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded text-blue-400"
                >
                    Open SQL Console
                </button>
             </div>
          )}
        </div>
      </div>

      {showConfigPanel && (
        <DatabaseConfigPanel 
          editConfigId={editConfigId} 
          onClose={handleClosePanel} 
        />
      )}
    </div>
  );
};

const DatabaseTool: React.FC = () => {
  return (
    <DatabaseToolProvider>
      <DatabaseToolContent />
    </DatabaseToolProvider>
  );
};

export default DatabaseTool;
