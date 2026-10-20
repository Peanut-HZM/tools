import { describe, expect, it } from 'vitest';
import {
  parseK8sWorkspaceSearch,
  serializeK8sWorkspaceSearch,
} from './k8sWorkspaceUrl';

describe('K8s 工作台 URL 上下文', () => {
  it('仅接受支持的资源类型，并去重、清理命名空间参数', () => {
    expect(
      parseK8sWorkspaceSearch(
        '?cluster=prod-a&resource=invalid&namespaces=default,,team-a,default'
      )
    ).toEqual({
      connectionId: 'prod-a',
      resourceType: 'pods',
      namespaces: ['default', 'team-a'],
    });
  });

  it('序列化后可恢复集群、资源类型和命名空间选择', () => {
    const search = serializeK8sWorkspaceSearch({
      connectionId: 'cluster-1',
      resourceType: 'workloads',
      namespaces: ['team-a', 'team-b'],
    });

    expect(search).toBe('?cluster=cluster-1&resource=workloads&namespaces=team-a%2Cteam-b');
    expect(parseK8sWorkspaceSearch(search)).toEqual({
      connectionId: 'cluster-1',
      resourceType: 'workloads',
      namespaces: ['team-a', 'team-b'],
    });
  });

  it('用空命名空间表达“所有命名空间”', () => {
    expect(
      serializeK8sWorkspaceSearch({
        connectionId: 'cluster-1',
        resourceType: 'nodes',
        namespaces: [],
      })
    ).toBe('?cluster=cluster-1&resource=nodes');
  });

  it('回写 K8s 上下文时保留其他工具的查询参数', () => {
    expect(
      serializeK8sWorkspaceSearch(
        {
          connectionId: 'cluster-2',
          resourceType: 'events',
          namespaces: ['team-a'],
        },
        '?pmConversation=conversation-1&cluster=old&resource=pods',
      ),
    ).toBe(
      '?pmConversation=conversation-1&cluster=cluster-2&resource=events&namespaces=team-a',
    );
  });
});
