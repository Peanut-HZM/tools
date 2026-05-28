import React, { useState, useCallback } from 'react';
import { DatabaseToolProvider, useDatabaseTool } from '../../../contexts/DatabaseToolContext';
import ConnectionList from './components/ConnectionList';
import SQLExecutor from './SQLExecutor';
import DatabaseConfigPanel from './DatabaseConfigPanel';
import TableDataViewer from './TableDataViewer';
import ResizablePanel from '../CursorHistory/ResizablePanel';

interface SqlTabState {
  configId: string;
  databaseName: string;
  schemaName: string;
  sql: string;
}

interface Tab {
  id: string;
  type: 'sql' | 'table';
  title: string;
  data?: {
    configId: string;
    databaseName?: string;
    tableName: string;
    schemaName?: string;
  };
  sqlState?: SqlTabState;
}

const deriveTabTitle = (configId: string, databaseName: string, configs: { id: string; alias: string }[]): string => {
  if (!configId) return 'SQL Console';
  const config = configs.find(c => c.id === configId);
  if (!config) return 'SQL Console';
  const title = databaseName 
    ? `${config.alias}.${databaseName}` 
    : config.alias;
  return title.length > 25 ? title.substring(0, 22) + '...' : title;
};

const DatabaseToolContent: React.FC = () => {
  const { configs } = useDatabaseTool();
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [editConfigId, setEditConfigId] = useState<string | null>(null);
  
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

  const handleSelectTable = (configId: string, databaseName: string | undefined, tableName: string, schemaName?: string) => {
    const tabId = `table-${configId}-${databaseName || ''}-${schemaName || ''}-${tableName}`;

    const existingTab = tabs.find(t => t.id === tabId);
    if (existingTab) {
      setActiveTabId(tabId);
    } else {
      const newTab: Tab = {
        id: tabId,
        type: 'table',
        title: tableName,
        data: { configId, databaseName, tableName, schemaName }
      };
      setTabs(prev => [...prev, newTab]);
      setActiveTabId(tabId);
    }
  };

  const handleCloseTab = (e: React.MouseEvent, tabId: string) => {
    e.stopPropagation();
    
    const newTabs = tabs.filter(t => t.id !== tabId);
    setTabs(newTabs);
    
    if (activeTabId === tabId) {
      if (newTabs.length > 0) {
        setActiveTabId(newTabs[newTabs.length - 1].id);
      } else {
        const defaultTab: Tab = { id: 'sql-console', type: 'sql', title: 'SQL Console' };
        setTabs([defaultTab]);
        setActiveTabId(defaultTab.id);
      }
    }
  };

  const handleTabClick = (tabId: string) => {
    setActiveTabId(tabId);
  };
  
  const handleOpenSqlConsole = (initialSql?: string, databaseName?: string, configId?: string, schemaName?: string) => {
    const tabId = `sql-${Date.now()}`;

    const title = deriveTabTitle(configId || '', databaseName || '', configs);

    const sqlState: SqlTabState | undefined = configId ? {
      configId,
      databaseName: databaseName || '',
      schemaName: schemaName || '',
      sql: initialSql || '',
    } : undefined;

    const newTab: Tab = { 
      id: tabId, 
      type: 'sql', 
      title,
      sqlState,
    };
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(tabId);
  };

  const handleConnectionSelect = useCallback((configId: string, databaseName?: string, schemaName?: string) => {
    setTabs(prev => {
      const activeTab = prev.find(t => t.id === activeTabId);
      if (activeTab?.type !== 'sql') return prev;

      const db = databaseName || configs.find(c => c.id === configId)?.database_name || '';
      const existingSchema = activeTab.sqlState?.schemaName || '';
      const schema = schemaName !== undefined ? schemaName : existingSchema;
      const currentSql = activeTab.sqlState?.sql || '';
      return prev.map(t =>
        t.id === activeTabId
          ? {
              ...t,
              sqlState: { configId, databaseName: db, schemaName: schema, sql: currentSql },
              title: deriveTabTitle(configId, db, configs)
            }
          : t
      );
    });
  }, [activeTabId, configs]);

  // 右→左联动：SQLExecutor内状态变更时更新Tab
  const handleSqlStateChange = useCallback((tabId: string, state: { configId: string; database: string; schema?: string; sql: string }) => {
    setTabs(prev => prev.map(t => {
      if (t.id !== tabId) return t;
      
      const existingSchema = t.sqlState?.schemaName || '';
      return {
        ...t,
        sqlState: { 
          configId: state.configId, 
          databaseName: state.database, 
          schemaName: state.schema !== undefined ? state.schema : existingSchema, 
          sql: state.sql 
        },
        title: deriveTabTitle(state.configId, state.database, configs)
      };
    }));
  }, [configs]);

  // 从活跃Tab派生左侧高亮状态
  const activeTab = tabs.find(t => t.id === activeTabId);
  const activeConfigId = activeTab?.type === 'sql' 
    ? activeTab.sqlState?.configId 
    : activeTab?.data?.configId;
  const activeDatabaseName = activeTab?.type === 'sql'
    ? activeTab.sqlState?.databaseName
    : activeTab?.data?.databaseName;
  const activeSchemaName = activeTab?.type === 'sql'
    ? activeTab.sqlState?.schemaName
    : activeTab?.data?.schemaName;

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-slate-900 text-slate-100">
      <ResizablePanel
        defaultWidth={280}
        minWidth={200}
        maxWidth={500}
        storageKey="dbTool.leftPanelWidth"
      >
        <ConnectionList
          onAddConfig={handleAddConfig}
          onEditConfig={handleEditConfig}
          onSelectTable={handleSelectTable}
          onOpenSqlConsole={handleOpenSqlConsole}
          activeConfigId={activeConfigId}
          activeDatabaseName={activeDatabaseName}
          activeSchemaName={activeSchemaName}
          onConnectionSelect={handleConnectionSelect}
        />
      </ResizablePanel>
      
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
          <button 
                onClick={() => handleOpenSqlConsole()}
                className="px-3 py-2 text-slate-500 hover:text-blue-400 transition-colors"
                title="New SQL Console"
              >
                <i className="fas fa-plus text-xs"></i>
              </button>
        </div>

        {/* Tab Content Area */}
        <div className="flex-1 overflow-hidden relative">
          {tabs.map(tab => (
            <div 
              key={tab.id} 
              className="absolute inset-0 w-full h-full bg-slate-900"
              style={{ 
                display: activeTabId === tab.id ? 'block' : 'none',
                visibility: activeTabId === tab.id ? 'visible' : 'hidden'
              }}
            >
              {tab.type === 'sql' ? (
                <SQLExecutor
                  configId={tab.sqlState?.configId || ''}
                  database={tab.sqlState?.databaseName || ''}
                  schema={tab.sqlState?.schemaName || ''}
                  sql={tab.sqlState?.sql || ''}
                  onStateChange={(state) => handleSqlStateChange(tab.id, state)}
                />
              ) : (
                tab.data && (
                  <TableDataViewer
                    configId={tab.data.configId}
                    databaseName={tab.data.databaseName}
                    tableName={tab.data.tableName}
                    schemaName={tab.data.schemaName}
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
                    onClick={() => handleOpenSqlConsole()}
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