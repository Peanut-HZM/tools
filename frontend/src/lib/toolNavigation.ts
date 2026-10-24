const STANDALONE_TOOL_PATHS: Record<string, string> = {
  'course-platform': '/courses',
  'tech-contents': '/tech-contents',
};

export function getStandaloneToolPath(toolId: string): string | null {
  return STANDALONE_TOOL_PATHS[toolId] ?? null;
}
