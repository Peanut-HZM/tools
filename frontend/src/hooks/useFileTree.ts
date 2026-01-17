/**
 * useFileTree Hook - Manages file tree state and operations
 */
import { useState, useCallback, useMemo } from 'react';
import type { FileNode } from '../types/markdownEditor';

interface UseFileTreeOptions {
  initialExpandedPaths?: string[];
}

export function useFileTree(options: UseFileTreeOptions = {}) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(
    new Set(options.initialExpandedPaths || [])
  );

  // Toggle node expansion
  const toggleNode = useCallback((path: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // Expand a node
  const expandNode = useCallback((path: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      next.add(path);
      return next;
    });
  }, []);

  // Collapse a node
  const collapseNode = useCallback((path: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      next.delete(path);
      return next;
    });
  }, []);

  // Expand all nodes
  const expandAll = useCallback((tree: FileNode | null) => {
    if (!tree) return;

    const paths: string[] = [];
    const collectPaths = (node: FileNode) => {
      if (node.type === 'directory') {
        paths.push(node.path);
        node.children?.forEach(collectPaths);
      }
    };
    collectPaths(tree);
    setExpandedNodes(new Set(paths));
  }, []);

  // Collapse all nodes
  const collapseAll = useCallback(() => {
    setExpandedNodes(new Set());
  }, []);

  // Check if a node is expanded
  const isExpanded = useCallback((path: string) => {
    return expandedNodes.has(path);
  }, [expandedNodes]);

  // Expand path to a specific file
  const expandToFile = useCallback((filePath: string) => {
    const parts = filePath.split('/');
    const paths: string[] = [];
    
    for (let i = 0; i < parts.length - 1; i++) {
      paths.push(parts.slice(0, i + 1).join('/'));
    }
    
    setExpandedNodes(prev => {
      const next = new Set(prev);
      paths.forEach(p => next.add(p));
      return next;
    });
  }, []);

  return {
    expandedNodes,
    toggleNode,
    expandNode,
    collapseNode,
    expandAll,
    collapseAll,
    isExpanded,
    expandToFile
  };
}

export default useFileTree;
