import React from 'react';

interface HighlightTextProps {
  text: string;
  highlight: string;
  className?: string;
}

const HighlightText: React.FC<HighlightTextProps> = ({ text, highlight, className }) => {
  if (!highlight.trim()) {
    return <span className={className}>{text}</span>;
  }

  const escaped = highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);

  return (
    <span className={className}>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-warning/20 text-accent-warning rounded px-0.5">
            {/* 搜索命中高亮：warning 语义 token，双主题联动 */}
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
};

export default HighlightText;
