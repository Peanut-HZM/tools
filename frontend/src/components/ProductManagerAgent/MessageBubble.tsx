import React from 'react';
import { Message } from '../../services/conversationApi';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender_type === 'user';
  const isAgent = message.sender_type === 'agent';
  
  // Format content with basic markdown-like rendering
  const formatContent = (content: string) => {
    if (!content) return null;
    
    // Simple formatting - split by newlines and handle basic markdown
    return content.split('\n').map((line, index) => {
      // Headers
      if (line.startsWith('### ')) {
        return <h4 key={index} className="font-bold text-lg mt-3 mb-2">{line.slice(4)}</h4>;
      }
      if (line.startsWith('## ')) {
        return <h3 key={index} className="font-bold text-xl mt-4 mb-2">{line.slice(3)}</h3>;
      }
      if (line.startsWith('# ')) {
        return <h2 key={index} className="font-bold text-2xl mt-4 mb-2">{line.slice(2)}</h2>;
      }
      
      // List items
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return <li key={index} className="ml-4">{line.slice(2)}</li>;
      }
      if (/^\d+\.\s/.test(line)) {
        return <li key={index} className="ml-4 list-decimal">{line.replace(/^\d+\.\s/, '')}</li>;
      }
      
      // Code blocks
      if (line.startsWith('```')) {
        return <pre key={index} className="bg-gray-100 p-2 rounded my-2 overflow-x-auto">{line.slice(3)}</pre>;
      }
      
      // Inline code
      if (line.includes('`')) {
        const parts = line.split(/(`[^`]+`)/g);
        return (
          <p key={index} className="my-1">
            {parts.map((part, i) => 
              part.startsWith('`') && part.endsWith('`') 
                ? <code key={i} className="bg-gray-100 px-1 rounded">{part.slice(1, -1)}</code>
                : part
            )}
          </p>
        );
      }
      
      // Bold text
      if (line.includes('**')) {
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={index} className="my-1">
            {parts.map((part, i) => 
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={i}>{part.slice(2, -2)}</strong>
                : part
            )}
          </p>
        );
      }
      
      // Empty line
      if (line.trim() === '') {
        return <br key={index} />;
      }
      
      // Regular paragraph
      return <p key={index} className="my-1">{line}</p>;
    });
  };
  
  if (message.message_type === 'structured') {
    // Render structured content (like tables, lists)
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div 
          className={`max-w-[80%] rounded-lg p-4 ${
            isUser 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {formatContent(message.content)}
        </div>
      </div>
    );
  }
  
  if (message.message_type === 'chart') {
    // Render chart/mermaid content
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
        <div 
          className={`max-w-[90%] rounded-lg p-4 ${
            isUser 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          <pre className="text-sm overflow-x-auto">
            {message.content}
          </pre>
        </div>
      </div>
    );
  }
  
  // Regular text message
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div 
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser 
            ? 'bg-blue-500 text-white' 
            : isAgent
              ? 'bg-gray-100 text-gray-800'
              : 'bg-gray-200 text-gray-800'
        }`}
      >
        {isAgent && (
          <div className="text-xs text-gray-500 mb-1">🤖 AI 助手</div>
        )}
        <div className="whitespace-pre-wrap break-words">
          {formatContent(message.content)}
        </div>
        {message.sent_at && (
          <div className={`text-xs mt-1 ${isUser ? 'text-blue-100' : 'text-gray-400'}`}>
            {new Date(message.sent_at).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
