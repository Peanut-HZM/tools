import React, { useState, useEffect } from 'react';
import { useI18n } from '../../../../i18n';

interface DatabaseFilterDialogProps {
  isOpen: boolean;
  onClose: () => void;
  allDatabases: string[];
  visibleDatabases: string[] | null; // null means all visible
  onApply: (visible: string[] | null) => void;
}

const DatabaseFilterDialog: React.FC<DatabaseFilterDialogProps> = ({
  isOpen,
  onClose,
  allDatabases,
  visibleDatabases,
  onApply
}) => {
  const { t } = useI18n();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');

  // Initialize selection when opening
  useEffect(() => {
    if (isOpen) {
      if (visibleDatabases === null) {
        // If null (all visible), select all
        setSelected(new Set(allDatabases));
      } else {
        // If filtered, select only those
        // Also ensure we only select ones that are in allDatabases (cleanup)
        const validVisible = visibleDatabases.filter(db => allDatabases.includes(db));
        setSelected(new Set(validVisible));
      }
      setSearchTerm('');
    }
  }, [isOpen, allDatabases, visibleDatabases]);

  if (!isOpen) return null;

  const filteredDatabases = allDatabases.filter(db => 
    db.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleToggle = (db: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(db)) {
      newSelected.delete(db);
    } else {
      newSelected.add(db);
    }
    setSelected(newSelected);
  };

  const handleSelectAll = () => {
    if (selected.size === filteredDatabases.length && filteredDatabases.length > 0) {
        // Deselect currently visible filtered ones
        const newSelected = new Set(selected);
        filteredDatabases.forEach(db => newSelected.delete(db));
        setSelected(newSelected);
    } else {
        // Select all visible filtered ones
        const newSelected = new Set(selected);
        filteredDatabases.forEach(db => newSelected.add(db));
        setSelected(newSelected);
    }
  };

  const handleSave = () => {
    // If all selected, save as null (meaning "Show All" / dynamic)
    // Actually, user might want to explicitly exclude future DBs.
    // But usually "Select All" implies "I want everything".
    // Let's stick to: if selected count == allDatabases count, return null.
    
    if (selected.size === allDatabases.length) {
      onApply(null);
    } else {
      onApply(Array.from(selected));
    }
    onClose();
  };

  const isAllSelected = filteredDatabases.length > 0 && filteredDatabases.every(db => selected.has(db));
  const isIndeterminate = filteredDatabases.some(db => selected.has(db)) && !isAllSelected;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100]">
      <div className="bg-surface-1 rounded-lg shadow-md w-full max-w-md border border-border flex flex-col max-h-[80vh]">
        <div className="flex justify-between items-center p-4 border-b border-border">
          <h3 className="text-lg font-medium text-ink">
             Filter Databases
          </h3>
          <button onClick={onClose} className="text-ink-muted hover:text-ink">
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="p-4 space-y-4 flex-1 overflow-hidden flex flex-col">
          {/* Search */}
          <div className="relative">
            <i className="fas fa-search absolute left-3 top-2.5 text-ink-faint text-sm"></i>
            <input
              type="text"
              placeholder={t.common.search || "Search..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-canvas border border-border rounded-md py-2 pl-9 pr-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          {/* Select All Checkbox */}
          <div className="flex items-center space-x-2 pb-2 border-b border-border/50">
            <input
              type="checkbox"
              id="select-all"
              checked={isAllSelected}
              ref={input => { if (input) input.indeterminate = isIndeterminate; }}
              onChange={handleSelectAll}
              className="rounded border-border bg-surface-2 text-accent-info focus:ring-accent focus:ring-offset-canvas"
            />
            <label htmlFor="select-all" className="text-sm font-medium text-ink-muted cursor-pointer select-none">
              Select All
            </label>
            <span className="text-xs text-ink-faint ml-auto">
              {selected.size} / {allDatabases.length}
            </span>
          </div>

          {/* Database List */}
          <div className="flex-1 overflow-y-auto space-y-1 min-h-[200px]">
             {filteredDatabases.length === 0 ? (
                <div className="text-center text-ink-faint py-8 text-sm">
                   No databases found
                </div>
             ) : (
                filteredDatabases.map(db => (
                  <div 
                    key={db} 
                    className="flex items-center space-x-2 p-2 hover:bg-surface-2/50 rounded cursor-pointer"
                    onClick={() => handleToggle(db)}
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(db)}
                      onChange={() => {}} // Handled by div click
                      className="rounded border-border bg-surface-2 text-accent-info focus:ring-accent focus:ring-offset-canvas pointer-events-none"
                    />
                    <span className="text-sm text-ink-muted truncate flex-1">{db}</span>
                  </div>
                ))
             )}
          </div>
        </div>

        <div className="p-4 border-t border-border flex justify-end space-x-3 bg-surface-1/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-ink-muted hover:text-ink-inverse hover:bg-surface-2 rounded-md transition-colors"
          >
            {t.common.cancel}
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium text-ink-inverse bg-accent hover:bg-accent-hover rounded-md shadow-sm transition-colors"
          >
            {t.common.confirm}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DatabaseFilterDialog;
