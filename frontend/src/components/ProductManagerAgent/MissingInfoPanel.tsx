import React, { useState } from 'react';

export interface MissingSection {
  section: string;
  key: string;
  suggested_questions: string[];
}

interface MissingInfoPanelProps {
  missingSections: MissingSection[];
  onQuestionClick?: (question: string) => void;
  collapsed?: boolean;
}

const MissingInfoPanel: React.FC<MissingInfoPanelProps> = ({
  missingSections,
  onQuestionClick,
  collapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(collapsed);

  if (!missingSections || missingSections.length === 0) {
    return (
      <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
        <div className="flex items-center">
          <svg className="w-5 h-5 text-green-600 dark:text-green-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <span className="text-green-800 dark:text-green-300 font-medium">
            文档结构完整，没有发现缺失的关键信息
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 bg-amber-50 dark:bg-amber-900/20 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-amber-600 dark:text-amber-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <span className="text-amber-800 dark:text-amber-300 font-medium">
            缺失 {missingSections.length} 个关键章节
          </span>
        </div>
        <svg
          className={`w-5 h-5 text-amber-600 dark:text-amber-400 transform transition-transform ${
            isCollapsed ? '' : 'rotate-180'
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-4 bg-white dark:bg-slate-800">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            为了生成更完整的 PRD，建议您补充以下信息。点击问题可以快速发送到对话框：
          </p>

          <div className="space-y-4">
            {missingSections.map((missing, index) => (
              <div
                key={missing.key}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
              >
                {/* Section Title */}
                <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-2">
                  {index + 1}. {missing.section}
                </h4>

                {/* Suggested Questions */}
                <div className="space-y-2">
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    建议问题：
                  </p>
                  <ul className="space-y-1">
                    {missing.suggested_questions.map((question, qIndex) => (
                      <li key={qIndex}>
                        <button
                          onClick={() => onQuestionClick?.(question)}
                          className="text-left text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline transition-colors flex items-start"
                        >
                          <svg className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                          </svg>
                          {question}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>

          {/* Help Text */}
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <p className="text-xs text-blue-700 dark:text-blue-300">
              💡 <strong>提示：</strong>点击任意问题，它将自动发送到对话框中，AI 助手会根据您的问题提供详细的指导。
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MissingInfoPanel;
