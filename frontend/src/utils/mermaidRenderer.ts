/**
 * Mermaid 图表渲染工具
 * 用于在前端渲染 Mermaid 语法定义的图表
 */

// Mermaid 图表类型
export type MermaidDiagramType = 
  | 'flowchart'
  | 'sequenceDiagram'
  | 'classDiagram'
  | 'stateDiagram'
  | 'erDiagram'
  | 'gantt'
  | 'pie'
  | 'mindmap'
  | 'journey'
  | 'graph';

/**
 * 解析 Markdown 内容中的 Mermaid 代码块
 * @param content Markdown 内容
 * @returns 解析后的图表列表
 */
export function parseMermaidBlocks(content: string): Array<{ id: string; type: MermaidDiagramType; code: string }> {
  const mermaidBlocks: Array<{ id: string; type: MermaidDiagramType; code: string }> = [];
  
  // 匹配 ```mermaid 代码块
  const regex = /```mermaid\n([\s\S]*?)```/g;
  let match;
  
  while ((match = regex.exec(content)) !== null) {
    const code = match[1].trim();
    const type = detectDiagramType(code);
    const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    mermaidBlocks.push({ id, type, code });
  }
  
  return mermaidBlocks;
}

/**
 * 检测 Mermaid 图表类型
 */
function detectDiagramType(code: string): MermaidDiagramType {
  const lowerCode = code.toLowerCase();
  
  if (lowerCode.startsWith('flowchart') || lowerCode.startsWith('graph')) {
    return 'flowchart';
  }
  if (lowerCode.startsWith('sequencediagram')) {
    return 'sequenceDiagram';
  }
  if (lowerCode.startsWith('classdiagram')) {
    return 'classDiagram';
  }
  if (lowerCode.startsWith('statediagram') || lowerCode.startsWith('state')) {
    return 'stateDiagram';
  }
  if (lowerCode.startsWith('erdiagram') || lowerCode.startsWith('er')) {
    return 'erDiagram';
  }
  if (lowerCode.startsWith('gantt')) {
    return 'gantt';
  }
  if (lowerCode.startsWith('pie')) {
    return 'pie';
  }
  if (lowerCode.startsWith('mindmap')) {
    return 'mindmap';
  }
  if (lowerCode.startsWith('journey')) {
    return 'journey';
  }
  
  return 'flowchart';
}

/**
 * 渲染 Mermaid 图表为 SVG
 * @param code Mermaid 代码
 * @param type 图表类型
 * @returns SVG 字符串
 */
export async function renderMermaidToSvg(code: string, type?: MermaidDiagramType): Promise<string> {
  // 使用 mermaid 库的全局对象
  if (typeof window !== 'undefined' && (window as any).mermaid) {
    const mermaid = (window as any).mermaid;
    
    try {
      // 生成唯一 ID
      const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // 渲染图表
      const { svg } = await mermaid.render(id, code);
      return svg;
    } catch (error) {
      console.error('Mermaid 渲染失败:', error);
      return `<div class="text-red-500">图表渲染失败</div>`;
    }
  }
  
  // 如果 mermaid 未加载，返回占位符
  return `<div class="text-gray-500">图表加载中...</div>`;
}

/**
 * 初始化 Mermaid
 * 需要在应用入口调用
 */
export function initMermaid(): void {
  if (typeof window !== 'undefined' && (window as any).mermaid) {
    const mermaid = (window as any).mermaid;
    
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      },
      sequence: {
        useMaxWidth: true,
        diagramMarginX: 50,
        diagramMarginY: 10,
        actorMargin: 50,
        noteMargin: 10,
        messageMargin: 35
      }
    });
  }
}

/**
 * 将 Mermaid 代码转换为图片 URL (可选方案)
 * @param code Mermaid 代码
 * @returns data URL
 */
export async function mermaidToDataUrl(code: string): Promise<string> {
  const svg = await renderMermaidToSvg(code);
  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`;
}

/**
 * 生成流程图代码
 * @param nodes 节点列表
 * @param edges 边列表
 * @returns Mermaid 流程图代码
 */
export function generateFlowchart(
  nodes: Array<{ id: string; label: string; shape?: string }>,
  edges: Array<{ from: string; to: string; label?: string }>
): string {
  let code = 'flowchart TD\n';
  
  // 添加节点
  nodes.forEach(node => {
    const shape = node.shape || 'round';
    code += `    ${node.id}["${node.label}"]\n`;
  });
  
  // 添加边
  edges.forEach(edge => {
    if (edge.label) {
      code += `    ${edge.from} -->|${edge.label}| ${edge.to}\n`;
    } else {
      code += `    ${edge.from} --> ${edge.to}\n`;
    }
  });
  
  return code;
}

/**
 * 生成序列图代码
 * @param participants 参与者列表
 * @param interactions 交互列表
 * @returns Mermaid 序列图代码
 */
export function generateSequenceDiagram(
  participants: string[],
  interactions: Array<{ from: string; to: string; message: string }>
): string {
  let code = 'sequenceDiagram\n';
  
  // 添加参与者
  participants.forEach(p => {
    code += `    participant ${p}\n`;
  });
  
  // 添加交互
  interactions.forEach(interaction => {
    code += `    ${interaction.from}->>${interaction.to}: ${interaction.message}\n`;
  });
  
  return code;
}

/**
 * 生成类图代码
 * @param classes 类定义列表
 * @returns Mermaid 类图代码
 */
export function generateClassDiagram(
  classes: Array<{
    name: string;
    properties: string[];
    methods: string[];
  }>
): string {
  let code = 'classDiagram\n';
  
  classes.forEach(cls => {
    code += `    class ${cls.name} {\n`;
    cls.properties.forEach(prop => {
      code += `        +${prop}\n`;
    });
    cls.methods.forEach(method => {
      code += `        +${method}()\n`;
    });
    code += `    }\n`;
  });
  
  return code;
}

/**
 * 生成 ER 图代码
 * @param entities 实体列表
 * @param relationships 关系列表
 * @returns Mermaid ER 图代码
 */
export function generateERDiagram(
  entities: Array<{
    name: string;
    attributes: string[];
  }>,
  relationships: Array<{
    from: string;
    to: string;
    type: string;
    label: string;
  }>
): string {
  let code = 'erDiagram\n';
  
  // 添加实体
  entities.forEach(entity => {
    code += `    ${entity.name} {\n`;
    entity.attributes.forEach(attr => {
      code += `        ${attr}\n`;
    });
    code += `    }\n`;
  });
  
  // 添加关系
  relationships.forEach(rel => {
    code += `    ${rel.from} ${rel.type} ${rel.to} : "${rel.label}"\n`;
  });
  
  return code;
}
