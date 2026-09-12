import { Tool } from '../../types';
import ToolCard from '../ToolCard/ToolCard';
import { useI18n, interpolate } from '../../i18n';

interface ToolGridProps {
  tools: Tool[];
  onToolClick?: (toolId: string) => void;
}

export default function ToolGrid({ tools, onToolClick }: ToolGridProps) {
  const { t } = useI18n();

  const handleToolClick = (tool: Tool) => {
    if (onToolClick) {
      onToolClick(tool.id);
    } else {
      alert(interpolate(t.errors.toolNotImplemented, { toolId: tool.title }));
    }
  };

  // 直接使用 API 返回的数据，确保首页展示与管理后台配置一致
  const getToolInfo = (tool: Tool) => {
    return {
      title: tool.title,
      description: tool.description
    };
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      {tools.map((tool) => {
        const { title, description } = getToolInfo(tool);
        return (
          <ToolCard
            key={tool.id}
            id={tool.id}
            icon={tool.icon}
            iconColor={tool.iconColor}
            title={title}
            description={description}
            rating={tool.rating}
            usageCount={tool.usageCount}
            custom_icon_url={tool.custom_icon_url}
            require_login={tool.require_login}
            onClick={() => handleToolClick(tool)}
          />
        );
      })}
    </div>
  );
}
