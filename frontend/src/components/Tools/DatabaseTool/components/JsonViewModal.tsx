import React, { useEffect, useState } from 'react';
import { useI18n } from '../../../../i18n';

interface JsonViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: any;
  title?: string;
}

const JsonViewModal: React.FC<JsonViewModalProps> = ({ isOpen, onClose, data, title }) => {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setCopied(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy", err);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100]">
      <div className="bg-surface-1 rounded-lg shadow-md w-full max-w-3xl border border-border flex flex-col max-h-[85vh]">
        <div className="flex justify-between items-center p-4 border-b border-border bg-surface-1">
          <h3 className="text-lg font-medium text-ink flex items-center gap-2">
             <i className="fas fa-code text-accent-info"></i>
             {title || "JSON Viewer"}
          </h3>
          <button onClick={onClose} className="text-ink-muted hover:text-ink">
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="flex-1 overflow-auto p-0 bg-canvas">
           <pre className="p-4 text-sm font-mono text-accent-info whitespace-pre-wrap break-all">
             {jsonString}
           </pre>
        </div>

        <div className="p-4 border-t border-border flex justify-end space-x-3 bg-surface-1">
          <button
            onClick={handleCopy}
            className="px-4 py-2 text-sm font-medium text-ink-muted hover:text-ink-inverse bg-surface-2 hover:bg-surface-3 rounded-md transition-colors flex items-center gap-2"
          >
            {copied ? <i className="fas fa-check text-green-400"></i> : <i className="fas fa-copy"></i>}
            {copied ? "Copied" : "Copy JSON"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-ink-inverse bg-accent hover:bg-accent-hover rounded-md shadow-sm transition-colors"
          >
            {t.common.close || "Close"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default JsonViewModal;
