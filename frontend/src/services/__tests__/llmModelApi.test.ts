import { describe, expect, it } from 'vitest';
import type { ModelCategory, LLMModel } from '../llmModelApi';

describe('ModelCategory 类型', () => {
  it('应包含全部 6 个分类', () => {
    const categories: ModelCategory[] = [
      'text',
      'voice',
      'vision',
      'embedding',
      'image_gen',
      'ocr',
    ];
    expect(categories).toHaveLength(6);
  });
});

describe('LLMModel 类型', () => {
  it('应包含 priority 字段', () => {
    const model: LLMModel = {
      id: 'x',
      name: 'test',
      model_name: 'gpt-4',
      provider_id: 'p',
      category: 'text',
      is_default: false,
      is_default_for_category: false,
      is_active: true,
      created_at: '2026-01-01',
      priority: 100,
    };
    expect(model.priority).toBe(100);
  });
});
