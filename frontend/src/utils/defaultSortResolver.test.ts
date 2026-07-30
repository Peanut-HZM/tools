import { describe, it, expect } from 'vitest';
import { resolveDefaultSort } from './defaultSortResolver';
import type { TableSchema } from '../types/databaseTool';

const makeSchema = (columns: string[], primaryKey?: string[]): TableSchema => ({
  table_name: 'test_table',
  columns: columns.map(name => ({ name, type: 'VARCHAR', nullable: true, comment: null, primary_key: false, auto_increment: false })),
  primary_key: primaryKey,
});

describe('resolveDefaultSort', () => {
  describe('优先级 1：创建时间字段', () => {
    it('匹配 create_time', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'create_time', 'name'])))
        .toBe('create_time DESC');
    });

    it('匹配 created_at', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'created_at', 'name'])))
        .toBe('created_at DESC');
    });

    it('匹配 createTime（驼峰）', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'createTime'])))
        .toBe('createTime DESC');
    });

    it('匹配 createdAt（驼峰）', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'createdAt'])))
        .toBe('createdAt DESC');
    });

    it('大小写不敏感：CREATE_TIME', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'CREATE_TIME'])))
        .toBe('CREATE_TIME DESC');
    });
  });

  describe('优先级 2：更新时间字段（无创建时间时）', () => {
    it('匹配 update_time', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'update_time', 'name'])))
        .toBe('update_time DESC');
    });

    it('匹配 updated_at', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'updated_at'])))
        .toBe('updated_at DESC');
    });

    it('匹配 updateTime', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'updateTime'])))
        .toBe('updateTime DESC');
    });

    it('匹配 updatedAt', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'updatedAt'])))
        .toBe('updatedAt DESC');
    });

    it('同时有 create_time 和 update_time 时优先 create_time', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'create_time', 'update_time'])))
        .toBe('create_time DESC');
    });
  });

  describe('优先级 3：主键 ID', () => {
    it('主键为 id 时返回 id DESC', () => {
      expect(resolveDefaultSort(makeSchema(['id', 'name'], ['id'])))
        .toBe('id DESC');
    });

    it('主键为 ID（大写）时返回 ID DESC', () => {
      expect(resolveDefaultSort(makeSchema(['ID', 'name'], ['ID'])))
        .toBe('ID DESC');
    });

    it('主键为 user_id 时不匹配（不含 "id" 子串？实际含 "id"，应匹配）', () => {
      // 主键名包含 "id" 子串即匹配
      expect(resolveDefaultSort(makeSchema(['user_id', 'name'], ['user_id'])))
        .toBe('user_id DESC');
    });

    it('主键不含 id 时不匹配', () => {
      expect(resolveDefaultSort(makeSchema(['code', 'name'], ['code'])))
        .toBe('');
    });

    it('无时间列且无主键时返回空字符串', () => {
      expect(resolveDefaultSort(makeSchema(['code', 'name'])))
        .toBe('');
    });
  });

  describe('边界情况', () => {
    it('空 columns 返回空字符串', () => {
      expect(resolveDefaultSort(makeSchema([]))).toBe('');
    });

    it('primaryKey 为空数组视为无主键', () => {
      expect(resolveDefaultSort(makeSchema(['code', 'name'], []))).toBe('');
    });

    it('primaryKey 多列时，任一列名含 id 即匹配', () => {
      expect(resolveDefaultSort(makeSchema(['a', 'b'], ['a', 'b_id'])))
        .toBe('b_id DESC');
    });
  });
});
