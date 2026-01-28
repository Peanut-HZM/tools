import React, { useRef, useState, useEffect } from 'react';
import { Tooltip } from './Tooltip';

interface TruncatedTextProps {
  text: string;
  className?: string;
  maxLines?: number; // Not implemented yet, assuming single line truncation for now
}

export const TruncatedText: React.FC<TruncatedTextProps> = ({ text, className = '' }) => {
  const [isTruncated, setIsTruncated] = useState(false);
  const textRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkTruncation = () => {
      if (textRef.current) {
        setIsTruncated(textRef.current.scrollWidth > textRef.current.clientWidth);
      }
    };

    checkTruncation();
    // Optional: Add resize observer if needed
    const resizeObserver = new ResizeObserver(checkTruncation);
    if (textRef.current) {
      resizeObserver.observe(textRef.current);
    }
    return () => resizeObserver.disconnect();
  }, [text]);

  return (
    <Tooltip content={isTruncated ? text : null}>
      <div 
        ref={textRef} 
        className={`truncate ${className}`}
      >
        {text}
      </div>
    </Tooltip>
  );
};
