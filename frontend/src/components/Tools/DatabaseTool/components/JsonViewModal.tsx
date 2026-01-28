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
      <div className="bg-slate-800 rounded-lg shadow-xl w-full max-w-3xl border border-slate-700 flex flex-col max-h-[85vh]">
        <div className="flex justify-between items-center p-4 border-b border-slate-700 bg-slate-800">
          <h3 className="text-lg font-medium text-slate-100 flex items-center gap-2">
             <i className="fas fa-code text-blue-400"></i>
             {title || "JSON Viewer"}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="flex-1 overflow-auto p-0 bg-slate-900">
           <pre className="p-4 text-sm font-mono text-blue-100 whitespace-pre-wrap break-all">
             {jsonString}
           </pre>
        </div>

        <div className="p-4 border-t border-slate-700 flex justify-end space-x-3 bg-slate-800">
          <button
            onClick={handleCopy}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-700 hover:bg-slate-600 rounded-md transition-colors flex items-center gap-2"
          >
            {copied ? <i className="fas fa-check text-green-400"></i> : <i className="fas fa-copy"></i>}
            {copied ? "Copied" : "Copy JSON"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-colors"
          >
            {t.common.close || "Close"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default JsonViewModal;
