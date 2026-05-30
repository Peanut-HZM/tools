import sqlparse, json, sys

sql = """-- Author: Peanut
-- Created: 2026-05-30
-- Purpose: 初始化 DeepSeek coding plan 渠道配置
-- 执行后需手动更新 key 字段为实际的 DeepSeek API Key

INSERT INTO channels (
    type,
    name,
    status,
    weight,
    created_time,
    test_time,
    response_time,
    base_url,
    other_info,
    models,
    model_mapping,
    priority,
    used_quota,
    "group",
    tag,
    key
) VALUES (
    43,                                    -- type = ChannelTypeDeepSeek
    'DeepSeek Coding Plan',                -- name
    1,                                     -- status = enabled
    0,                                     -- weight
    EXTRACT(EPOCH FROM NOW()),             -- created_time (bigint unix timestamp)
    0,                                     -- test_time
    0,                                     -- response_time
    'deepseek-coding-plan',                -- base_url (对应 ChannelSpecialBases key)
    '',                                    -- other_info
    'coding-plan,deepseek-v4-pro',         -- models
    '{"coding-plan":"deepseek-v4-pro"}',   -- model_mapping: 将 coding-plan 映射为 deepseek-v4-pro
    3,                                     -- priority (Ali=10 > Kimi=5 > DeepSeek=3)
    0,                                     -- used_quota
    'default',                             -- group
    'coding-plan',                         -- tag
    'YOUR_DEEPSEEK_API_KEY_HERE'           -- key (请手动更新为实际 API Key)
);"""

statements = sqlparse.split(sql)
for i, s in enumerate(statements):
    stripped = s.strip()
    is_empty = not stripped
    is_semi = stripped == ';'
    is_comment = stripped.startswith('--')
    print(f'Statement {i}:')
    print(f'  len={len(stripped)}, is_empty={is_empty}, is_semi={is_semi}, is_comment={is_comment}')
    if not is_empty:
        print(f'  content: {stripped[:200]}')
    print()

# Apply the filter from sql_executor.py
filtered = [s for s in statements if s.strip() and s.strip() != ';' and not s.strip().startswith('--')]
print(f'Total statements: {len(statements)}')
print(f'After filter: {len(filtered)}')
for i, s in enumerate(filtered):
    print(f'  Filtered {i}: {s.strip()[:100]}...')
