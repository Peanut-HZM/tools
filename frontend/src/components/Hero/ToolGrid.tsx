import { Tool } from '../../types';
import ToolCard from '../ToolCard/ToolCard';

interface ToolGridProps {
  tools: Tool[];
  onToolClick?: (toolId: string) => void;
}

export default function ToolGrid({ tools, onToolClick }: ToolGridProps) {
  const handleToolClick = (tool: Tool) => {
    if (onToolClick) {
      onToolClick(tool.id);
    } else {
      alert(`跳转到 ${tool.title} 工具页面`);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {tools.map((tool) => (
        <ToolCard
          key={tool.id}
          id={tool.id}
          icon={tool.icon}
          iconColor={tool.iconColor}
          title={tool.title}
          description={tool.description}
          rating={tool.rating}
          usageCount={tool.usageCount}
          onClick={() => handleToolClick(tool)}
        />
      ))}
    </div>
  );
}
