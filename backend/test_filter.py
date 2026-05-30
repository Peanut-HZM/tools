import sqlparse

sql = """-- Author: Peanut
-- Created: 2026-05-30

INSERT INTO channels (type, name, key) VALUES (43, 'DeepSeek', 'YOUR_KEY');

-- 单独的分号测试
;

-- 纯注释
-- 这是一条纯注释
"""

statements = sqlparse.split(sql)
print(f'Before filter: {len(statements)}')

# Filter 1: empty and semicolon-only
filtered = [s for s in statements if s.strip() and s.strip() != ';']
print(f'After filter1: {len(filtered)}')

# Filter 2: only statements with SQL keywords
sql_kw = {'INSERT', 'SELECT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'SET', 'BEGIN', 'COMMIT', 'ROLLBACK', 'TRUNCATE'}
final = [s for s in filtered if any(kw in s.upper() for kw in sql_kw)]
print(f'After filter2: {len(final)}')

for i, s in enumerate(final):
    print(f'  Final {i}: {s.strip()[:100]}...')
