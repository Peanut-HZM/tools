# Community Knowledge Research: cloudflare-d1

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-d1/SKILL.md
**Packages Researched**: @cloudflare/workers-types@4.20260109.0, wrangler@4.59.2
**Official Repo**: cloudflare/workers-sdk
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 4 |
| TIER 3 (Community Consensus) | 3 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 12 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Multi-line SQL in D1Database.exec() Causes Parse Errors

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #9133](https://github.com/cloudflare/workers-sdk/issues/9133)
**Date**: 2025-05-03
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using `D1Database.exec()` with multi-line SQL statements (especially CREATE TABLE with newlines), D1 throws "incomplete input" errors even though the SQL is valid.

**Reproduction**:
```typescript
await env.DB.exec(`CREATE TABLE my_cool_table (
  id TEXT
);`);
// Error: D1_EXEC_ERROR: incomplete input
```

**Solution/Workaround**:
1. Always `await` the exec call to see the error
2. Use prepared statements instead of exec() for dynamic SQL
3. Keep migrations in external `.sql` files instead of inline strings

```typescript
// Better: Use prepared statement
await env.DB.prepare(`CREATE TABLE my_cool_table (id TEXT)`).run();

// Best: Use migration files
// migrations/0001_create_table.sql
```

**Official Status**:
- [x] Known issue, workaround required
- [ ] Won't fix (workerd parsing limitation)

**Cross-Reference**:
- Related to: Error Handling section (exec() limitations)

---

### Finding 1.2: Lowercase BEGIN in Triggers Fails Remote but Works Local

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #10998](https://github.com/cloudflare/workers-sdk/issues/10998)
**Date**: 2025-10-16
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
SQL triggers with lowercase `begin` keyword work in local D1 but fail when applied to remote databases. The remote backend doesn't tolerate lowercase `begin` in trigger definitions.

**Reproduction**:
```sql
-- This works locally but FAILS remotely
CREATE TRIGGER update_timestamp
AFTER UPDATE ON users
FOR EACH ROW
begin
  UPDATE users SET updated_at = unixepoch() WHERE user_id = NEW.user_id;
end;
```

**Solution/Workaround**:
Use uppercase `BEGIN` and `END` keywords in trigger definitions:

```sql
-- Works both locally and remotely
CREATE TRIGGER update_timestamp
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
  UPDATE users SET updated_at = unixepoch() WHERE user_id = NEW.user_id;
END;
```

**Official Status**:
- [x] Known issue, workaround required
- [x] Tracking internally (CFSQL-1402)

**Cross-Reference**:
- Related to: Migration Best Practices section

---

### Finding 1.3: D1 Remote vs Local Execute Divergence (Windows Specific)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11708](https://github.com/cloudflare/workers-sdk/issues/11708)
**Date**: 2025-12-18
**Verified**: Yes (platform-specific)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
On Windows 11 (and some WSL environments), executing D1 SQL files with `wrangler d1 execute --file` fails with "HashIndex detected hash table inconsistency" error. The same file exported directly from D1 remote using `wrangler d1 export` causes the error when re-imported. The issue appears when cached SQL statements exceed 1 MB.

**Reproduction**:
```bash
# Export from remote D1
npx wrangler d1 export db-name --remote --output=./database.sql

# Try to execute locally - FAILS on Windows
npx wrangler d1 execute db-name --file=database.sql
# Error: HashIndex detected hash table inconsistency
```

**Solution/Workaround**:
1. Use WSL (if it works on your WSL version)
2. Break large SQL files into smaller chunks (<1 MB per statement)
3. Delete `.wrangler` directory before executing
4. Wait for workerd fix (tracked internally as CFSQL-1461)

```bash
# Delete cache before executing
rm -rf .wrangler
npx wrangler d1 execute db-name --file=database.sql
```

**Official Status**:
- [ ] Fix in progress (workerd cache bug)
- [x] Known issue, workaround required
- [x] Platform-specific (Windows + some WSL environments)

**Cross-Reference**:
- Related to: Local Development section
- Internal ticket: CFSQL-1461

---

### Finding 1.4: D1 Remote Bindings Connection Timeout After 1 Hour

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #10801](https://github.com/cloudflare/workers-sdk/issues/10801)
**Date**: 2025-09-29
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using remote D1 bindings (via `wrangler dev` or vite-plugin with `experimental.remoteBindings: true`), the connection times out after exactly 1 hour of inactivity. This causes `D1_ERROR: Failed to parse body as JSON, got: error code: 1031` errors. The timeout is based on server start time, not last interaction.

**Reproduction**:
```jsonc
// wrangler.jsonc
{
  "d1_databases": [{
    "binding": "DB",
    "remote": true,
    "database_id": "..."
  }]
}
```

After 60+ minutes: Next D1 query fails with error code 1031

**Solution/Workaround**:
1. Restart dev server every hour
2. Implement periodic background query to keep connection alive
3. Wait for Wrangler/Vite-plugin to auto-recreate connections (planned)
4. Remove `global_fetch_strictly_public` compatibility flag (may help)

```typescript
// Workaround: Keep connection alive
setInterval(async () => {
  try {
    await env.DB.prepare('SELECT 1').first();
  } catch (e) {
    console.log('Connection keepalive failed:', e);
  }
}, 30 * 60 * 1000); // Every 30 minutes
```

**Official Status**:
- [x] Expected behavior (1 hour timeout)
- [x] Enhancement planned (auto-reconnect)
- [x] Undocumented limitation

**Cross-Reference**:
- Related to: Local Development section
- Should add to Known Issues

---

### Finding 1.5: D1 Not Available with Service Bindings Locally

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11121](https://github.com/cloudflare/workers-sdk/issues/11121)
**Date**: 2025-10-29
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When running multiple Workers with service bindings in a single `wrangler dev` process, the auxiliary worker cannot access its D1 binding because both workers share the same persistence path. The D1 data for worker2 is stored in worker2's `.wrangler` directory, but Miniflare looks for it in worker1's directory.

**Solution/Workaround**:
Use `--persist-to` flag when applying migrations to point all workers to the same persistence store:

```bash
# Apply worker2 migrations to worker1's persistence path
cd worker2
npx wrangler d1 migrations apply DB --local --persist-to=../worker1/.wrangler/state

# Now both workers share the same D1 data
cd ../worker1
npx wrangler dev  # Both workers can access D1
```

**Official Status**:
- [x] Documented behavior (Miniflare limitation)
- [x] Workaround available

**Cross-Reference**:
- Related to: Local Development section
- Add to Multi-Worker Development subsection

---

### Finding 1.6: Network Connection Lost with Large D1 Import

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11958](https://github.com/cloudflare/workers-sdk/issues/11958)
**Date**: 2026-01-17
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Partial (mentions "Statement too long")

**Description**:
Importing large SQL dumps via `wrangler d1 execute --remote --file` fails with "Network connection lost" errors, especially for files with thousands of INSERT statements. The issue is exacerbated by large individual statements.

**Reproduction**:
```bash
# Large SQL file with 10,000+ INSERT statements
npx wrangler d1 execute my-db --remote --file=large-dump.sql
# Error: D1_ERROR: Network connection lost
```

**Solution/Workaround**:
1. Break large files into smaller chunks (<5000 statements per file)
2. Use batch() API from Worker instead of wrangler CLI
3. Import to local first, then use Time Travel to restore to remote
4. Reduce individual statement size (100-250 rows per INSERT)

**Official Status**:
- [x] Known issue (network timeout)
- [x] Workaround required

**Cross-Reference**:
- Related to: Known Issues Prevented #1 ("Statement too long")
- Expand with network timeout context

---

### Finding 1.7: Transient D1 Errors Are Expected Behavior

**Trust Score**: TIER 1 - Official
**Source**: [Cloudflare D1 FAQ](https://developers.cloudflare.com/d1/reference/faq/)
**Date**: 2025 (documented behavior)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Partial (Error Handling section mentions retries)

**Description**:
D1 queries fail transiently with errors like "Network connection lost", "storage operation exceeded timeout", "isolate exceeded its memory limit", or "object to be reset". Cloudflare documentation states "a handful of errors every several hours is not unexpected" and that applications should implement retry logic as standard practice.

**Common Transient Errors**:
- `D1_ERROR: Network connection lost`
- `D1 DB storage operation exceeded timeout which caused object to be reset`
- `Internal error while starting up D1 DB storage caused object to be reset`
- `D1 DB's isolate exceeded its memory limit and was reset`

**Solution/Workaround**:
Implement exponential backoff retry logic for all D1 operations:

```typescript
async function queryWithRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 100
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      const isTransient = error.message?.includes('Network connection lost') ||
                         error.message?.includes('exceeded timeout') ||
                         error.message?.includes('exceeded its memory limit');

      if (!isTransient || i === maxRetries - 1) throw error;

      await new Promise(r => setTimeout(r, baseDelay * Math.pow(2, i)));
    }
  }
  throw new Error('Max retries exceeded');
}

// Usage
const user = await queryWithRetry(() =>
  env.DB.prepare('SELECT * FROM users WHERE email = ?').bind(email).first()
);
```

**Official Status**:
- [x] Documented behavior (expected transient failures)
- [x] Retry logic recommended by Cloudflare
- [x] Automatic retries for read-only queries (Sept 2025)

**Cross-Reference**:
- Related to: Error Handling section
- Note: Sept 2025 update added automatic retries for SELECT queries (up to 2 attempts)

---

### Finding 1.8: FTS5 Virtual Tables Break D1 Export

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #9519](https://github.com/cloudflare/workers-sdk/issues/9519), [Cloudflare D1 Docs](https://developers.cloudflare.com/d1/best-practices/import-export-data/)
**Date**: 2025-06-07
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Databases with FTS5 virtual tables (for full-text search) cannot be exported using `wrangler d1 export`. The export command crashes indefinitely with no useful error message.

**Reproduction**:
```sql
-- Create FTS5 virtual table
CREATE VIRTUAL TABLE files_fts USING fts5(name, publisher);

-- Try to export
npx wrangler d1 export my-db --remote
-- Hangs indefinitely or crashes
```

**Solution/Workaround**:
1. Drop virtual tables before export
2. Export the database
3. Recreate virtual tables after import

**Official Status**:
- [x] Documented limitation
- [x] Workaround available

**Cross-Reference**:
- Add to: Import/Export section (currently not covered)
- Related to: FTS5 support

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: 10 GB Database Size Limit Workaround via Sharding

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [DEV.to Article](https://dev.to/araldhafeeri/scaling-your-cloudflare-d1-database-from-the-10-gb-limit-to-tbs-4a16)
**Date**: 2025
**Verified**: Logical Architecture
**Impact**: HIGH
**Already in Skill**: No

**Description**:
D1 has a hard 10 GB per database limit. For applications that need more storage, Cloudflare supports up to 50,000 databases per Worker, enabling sharding strategies. Hash-based sharding can scale to 100+ GB.

**Solution/Workaround**:
Implement database sharding by tenant or hash:

```typescript
// Hash-based sharding with 10 databases = 100 GB capacity
function getShardId(userId: string): number {
  const hash = Array.from(userId).reduce((acc, char) =>
    ((acc << 5) - acc) + char.charCodeAt(0), 0
  );
  return Math.abs(hash) % 10;
}

// wrangler.jsonc - Define 10 database shards
{
  "d1_databases": [
    { "binding": "DB_SHARD_0", "database_id": "..." },
    { "binding": "DB_SHARD_1", "database_id": "..." },
    // ... up to DB_SHARD_9
  ]
}

// Get correct shard for user
function getUserDb(env: Env, userId: string): D1Database {
  const shardId = getShardId(userId);
  return env[`DB_SHARD_${shardId}`];
}

// Query user's data
const db = getUserDb(env, userId);
const user = await db.prepare('SELECT * FROM users WHERE user_id = ?')
  .bind(userId).first();
```

**Community Validation**:
- Article provides working implementation
- Multiple Cloudflare community references
- Aligns with Cloudflare's 50,000 database support

**Cross-Reference**:
- Add to: Best Practices or Scaling section
- Related to: Known Issues (10 GB limit not currently documented as workaround-able)

---

### Finding 2.2: 2 MB Row Size Limit - Hybrid D1 + R2 Pattern

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [DEV.to Article](https://dev.to/morphinewan/when-cloudflare-d1s-2mb-limit-taught-me-a-hard-lesson-about-database-design-3edb)
**Date**: 2025
**Verified**: Code Review
**Impact**: HIGH
**Already in Skill**: No

**Description**:
D1 has a 2 MB row size limit. Applications storing large content (HTML, JSON, images) hit "database row size exceeded maximum allowed size" errors. The recommended pattern is to store metadata in D1 and large content in R2.

**Reproduction**:
```typescript
// This FAILS when htmlContent > 2 MB
await env.DB.prepare(
  'INSERT INTO pages (url, html_content) VALUES (?, ?)'
).bind(url, largeHtmlContent).run();
// Error: database row size exceeded maximum allowed size
```

**Solution/Workaround**:
Hybrid D1 + R2 storage pattern:

```typescript
// 1. Store large content in R2
const contentKey = `pages/${crypto.randomUUID()}.html`;
await env.R2_BUCKET.put(contentKey, htmlContent);

// 2. Store metadata in D1
await env.DB.prepare(`
  INSERT INTO pages (url, r2_key, size, created_at)
  VALUES (?, ?, ?, ?)
`).bind(url, contentKey, htmlContent.length, Date.now()).run();

// 3. Retrieve content
const page = await env.DB.prepare('SELECT * FROM pages WHERE url = ?')
  .bind(url).first();

if (page) {
  const content = await env.R2_BUCKET.get(page.r2_key);
  const html = await content.text();
}
```

**Community Validation**:
- Multiple users report hitting 2 MB limit
- Pattern aligns with Cloudflare's multi-service architecture
- R2 has no row size limit

**Cross-Reference**:
- Add to: Best Practices or Limitations section

---

### Finding 2.3: Case Sensitivity When Migrating D1 to PostgreSQL

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Mats' Blog](https://mats.coffee/blog/d1-to-hyperdrive)
**Date**: 2025
**Verified**: Documented SQLite/Postgres Difference
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
SQLite (D1's underlying engine) is case-insensitive for table and column names, while PostgreSQL is case-sensitive. When migrating from D1 to Hyperdrive (PostgreSQL), queries fail if table/column names have inconsistent casing.

**Reproduction**:
```sql
-- Works in D1 (SQLite)
CREATE TABLE Users (UserId INTEGER, Email TEXT);
SELECT * FROM users WHERE userid = 1;  -- case doesn't matter

-- FAILS in PostgreSQL (Hyperdrive)
SELECT * FROM users WHERE userid = 1;
-- Error: column "userid" does not exist
```

**Solution/Workaround**:
Use consistent lowercase naming in D1 schemas to maintain PostgreSQL compatibility:

```sql
-- Always use lowercase
CREATE TABLE users (user_id INTEGER, email TEXT);
CREATE INDEX idx_users_email ON users(email);

-- Queries work in both D1 and PostgreSQL
SELECT * FROM users WHERE user_id = 1;
```

**Community Validation**:
- Blog post documents real migration pain point
- Aligns with PostgreSQL documentation
- Multiple SQL best practices recommend lowercase

**Cross-Reference**:
- Add to: Best Practices (database portability)
- Add note: If planning to migrate to Hyperdrive later

---

### Finding 2.4: FTS5 Case Sensitivity - Use Lowercase "fts5"

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Cloudflare Community Forum](https://community.cloudflare.com/t/d1-support-for-virtual-tables/607277), [D1 Manager GitHub](https://github.com/neverinfamous/d1-manager)
**Date**: 2025
**Verified**: Multiple Community Reports
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When creating FTS5 virtual tables in D1, using uppercase "FTS5" may cause "not authorized" errors. Using lowercase "fts5" works consistently.

**Reproduction**:
```sql
-- May fail with "not authorized"
CREATE VIRTUAL TABLE files_fts USING FTS5(name, publisher);

-- Works reliably
CREATE VIRTUAL TABLE files_fts USING fts5(name, publisher);
```

**Solution/Workaround**:
Always use lowercase "fts5" in virtual table definitions:

```sql
-- Correct pattern
CREATE VIRTUAL TABLE search_index USING fts5(
  title,
  content,
  tokenize = 'porter unicode61'
);

-- Query the index
SELECT * FROM search_index WHERE search_index MATCH 'query terms';
```

**Community Validation**:
- Multiple forum users confirm lowercase works
- D1 Manager tool (updated Jan 2026) uses lowercase
- No official docs specify case sensitivity

**Cross-Reference**:
- Add to: D1 with FTS5 section

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Parameter Binding Limit of 100 Prevents Large Batch Inserts

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Cloudflare Community Forum](https://community.cloudflare.com/t/got-7500-error-when-using-d1-http-api-to-run-sqls-in-batch-mode/774673)
**Date**: 2025
**Verified**: SQLite Behavior
**Impact**: MEDIUM
**Already in Skill**: Partial (mentions 100-250 rows per batch)

**Description**:
SQLite and D1 limit bound parameters to 100 per query. With 10 columns, you can only insert 10 rows per prepared statement. Exceeding this causes "Wrong number of parameter bindings" errors.

**Recommendation**: Add explicit parameter limit documentation to batch insert examples

**Cross-Reference**:
- Related to: Query Patterns - Batch inserts

---

### Finding 3.2: Batched Statements Are Not True Transactions

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Cloudflare D1 Worker API Docs](https://developers.cloudflare.com/d1/worker-api/d1-database/)
**Date**: 2025
**Verified**: Documented Behavior
**Impact**: HIGH
**Already in Skill**: Partial (mentions "pseudo-transactions")

**Description**:
D1's `batch()` API executes statements sequentially and atomically per statement (auto-commit mode), but does NOT provide rollback if a later statement fails. If statement 3 of 5 fails, statements 1-2 have already committed.

**Recommendation**: Update "Batch Pattern (Pseudo-Transactions)" section with clearer warning about partial commit behavior

**Cross-Reference**:
- Related to: Query Patterns - Batch section

---

### Finding 3.3: D1 Migrations Fail Silently in CI Without Useful Logs

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #221](https://github.com/cloudflare/wrangler-action/issues/221)
**Date**: 2025
**Verified**: Multiple Reports
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
D1 migrations that work locally can fail silently in CI/CD environments (GitHub Actions, etc.) with error code 1 and no useful log output.

**Recommendation**: Add CI/CD troubleshooting section or note in Migrations section

**Cross-Reference**:
- Add to: Migrations section (CI considerations)

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Statement too long (large INSERTs) | Known Issues #1 | Fully covered with batching solution |
| Type mismatch (undefined vs null) | Known Issues #6 | Fully covered |
| Automatic retries for read-only queries | Recent Updates (Sept 2025) | Already documented |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.2 Lowercase BEGIN in triggers | Migration Best Practices | Add gotcha with uppercase requirement |
| 1.4 Remote bindings timeout (1 hour) | Local Development | Add warning + keepalive pattern |
| 1.5 Service bindings persistence path | Local Development | Add Multi-Worker subsection with --persist-to pattern |
| 1.7 Transient errors are expected | Error Handling | Expand with retry pattern + official guidance |
| 1.8 FTS5 breaks export | Best Practices | Add Import/Export section with FTS5 workaround |
| 2.1 10 GB limit sharding pattern | Best Practices | Add Scaling section with sharding example |
| 2.2 2 MB row limit + R2 hybrid | Best Practices | Add to Limitations with hybrid storage pattern |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.1 Multi-line SQL exec() issue | Error Handling | Add to error table |
| 1.3 Windows HashIndex bug | Known Issues | Add platform-specific warning |
| 1.6 Large import network timeout | Known Issues #1 | Expand existing "Statement too long" |
| 2.3 Case sensitivity (SQLite → Postgres) | Best Practices | Add database portability note |
| 2.4 FTS5 case sensitivity | D1 with FTS5 | Add brief note about lowercase "fts5" |
| 3.1 Parameter binding limit (100) | Query Patterns | Clarify in batch insert examples |
| 3.2 Batch is not transaction | Query Patterns | Strengthen warning in Batch section |
| 3.3 CI migrations fail silently | Migrations | Add CI troubleshooting note |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "d1" created after May 2025 | 30 | 8 |
| Direct issue views | 11 | 8 |

### Web Search

| Query | Results | Useful |
|-------|---------|--------|
| d1 migration gotcha 2025 2026 | 10 | 3 |
| d1 workaround limitation 2025 | 5 | 3 |
| d1 batch query error 2025 | 10 | 2 |
| d1 remote bindings 2025 | 10 | 2 |
| d1 fts5 full text search 2025 | 9 | 2 |

**Time Spent**: ~18 minutes

---

## Sources

- [GitHub Issue #9133](https://github.com/cloudflare/workers-sdk/issues/9133)
- [GitHub Issue #10998](https://github.com/cloudflare/workers-sdk/issues/10998)
- [GitHub Issue #11708](https://github.com/cloudflare/workers-sdk/issues/11708)
- [GitHub Issue #10801](https://github.com/cloudflare/workers-sdk/issues/10801)
- [GitHub Issue #11121](https://github.com/cloudflare/workers-sdk/issues/11121)
- [GitHub Issue #11958](https://github.com/cloudflare/workers-sdk/issues/11958)
- [GitHub Issue #9519](https://github.com/cloudflare/workers-sdk/issues/9519)
- [Cloudflare D1 FAQ](https://developers.cloudflare.com/d1/reference/faq/)
- [Scaling Your Cloudflare D1 Database: From the 10 GB Limit to TBs](https://dev.to/araldhafeeri/scaling-your-cloudflare-d1-database-from-the-10-gb-limit-to-tbs-4a16)
- [When Cloudflare D1's 2MB Limit Taught Me a Hard Lesson](https://dev.to/morphinewan/when-cloudflare-d1s-2mb-limit-taught-me-a-hard-lesson-about-database-design-3edb)
- [Migrating from Cloudflare D1 to Hyperdrive](https://mats.coffee/blog/d1-to-hyperdrive)
- [D1 Support for Virtual Tables - Cloudflare Community](https://community.cloudflare.com/t/d1-support-for-virtual-tables/607277)
- [D1 Manager GitHub](https://github.com/neverinfamous/d1-manager)
- [Cloudflare D1 Worker API Documentation](https://developers.cloudflare.com/d1/worker-api/)

---

**Research Completed**: 2026-01-20 05:15 UTC
**Next Research Due**: After next major D1 feature release (Q2 2026)
