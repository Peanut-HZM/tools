# Community Knowledge Research: Cloudflare Hyperdrive

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-hyperdrive/SKILL.md
**Packages Researched**: wrangler@4.59.3, pg@8.16.3+, postgres@3.4.8+, mysql2@3.16.0+
**Official Repo**: cloudflare/workers-sdk
**Time Window**: July 2024 - January 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 6 |
| TIER 2 (High-Quality Community) | 5 |
| TIER 3 (Community Consensus) | 3 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 3 |
| Recommended to Add | 9 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Windows Local Development - Hostname Resolution Failure

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11556](https://github.com/cloudflare/workers-sdk/issues/11556)
**Date**: 2025-12-08
**Verified**: Yes (Multiple platform confirmations)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Hyperdrive local development fails on Windows (and confirmed on macOS 26 Tahoe and Ubuntu 24.04 LTS) with wrangler@4.54.0+. The connection string gets rewritten to a hostname like `e7df180253d62d5f290c4c0338e2a09e.hyperdrive.local` which fails to resolve.

**Reproduction**:
```bash
# On Windows, macOS 26, or Ubuntu 24.04 LTS
npx wrangler@4.58.0 dev
# Connection fails with hostname resolution error
```

**Solution/Workaround**:
Currently open issue. Workaround is to use `wrangler dev --remote` (connects to production) or downgrade wrangler.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects: wrangler@4.54.0+
- Platforms: Windows, macOS 26 Tahoe, Ubuntu 24.04 LTS
- Related PR: https://github.com/cloudflare/workers-sdk/commits/25f66726d3b2f55a6139273e8f307f0cf3c44422/packages/miniflare/src/plugins/hyperdrive/hyperdrive-proxy.ts

---

### Finding 1.2: postgres.js Hangs with IP Addresses Instead of Hostnames

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6179](https://github.com/cloudflare/workers-sdk/issues/6179)
**Date**: 2024-07-02
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Using an IP address directly in the connection string instead of a hostname causes postgres.js to hang indefinitely. This is an obscure failure mode that doesn't produce clear error messages.

**Reproduction**:
```typescript
// ❌ WRONG - Using IP address directly
const connection = "postgres://user:password@192.168.1.100:5432/db"

// This will hang indefinitely with no clear error
const sql = postgres(connection);
const result = await sql`SELECT 1`;
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - Use hostname
const connection = "postgres://user:password@db-host.example.com:5432/db"

const sql = postgres(connection);
const result = await sql`SELECT 1`;
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (Hyperdrive requires hostnames)
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related issue: Poor error visibility in Hyperdrive logs
- Additional gotcha: Miniflare doesn't support special characters in passwords (A-z0-9 only), despite Postgres supporting them

---

### Finding 1.3: MySQL 8.0.43 Authentication Plugin Not Supported

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #10617](https://github.com/cloudflare/workers-sdk/issues/10617)
**Date**: 2025-09-11
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions caching_sha2_password and mysql_native_password)

**Description**:
MySQL 8.0.43 introduces a new authentication method that Hyperdrive doesn't support. Only `caching_sha2_password` and `mysql_native_password` are supported.

**Reproduction**:
```bash
# Create Hyperdrive with MySQL 8.0.43 database
npx wrangler hyperdrive create my-db \
  --connection-string="mysql://user:password@host:3306/db"

# Error: unsupported authentication method
```

**Solution/Workaround**:
Use MySQL 8.0.40 or earlier, or configure user to use supported auth plugin:
```sql
ALTER USER 'username'@'%' IDENTIFIED WITH caching_sha2_password BY 'password';
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Tracked internally: CFSQL-1392
- Also affects: TiDB Starter users

---

### Finding 1.4: Local SSL/TLS Not Supported for Remote Databases

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #10124](https://github.com/cloudflare/workers-sdk/issues/10124)
**Date**: 2025-07-29
**Verified**: Yes (Cloudflare team confirmed)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using local development with Hyperdrive pointing to a remote SSL-required database (e.g., Neon), local connections fail because Hyperdrive local mode doesn't support SSL. This makes local development impossible for databases that require SSL.

**Reproduction**:
```jsonc
// wrangler.jsonc
{
  "hyperdrive": [{
    "binding": "HYPERDRIVE",
    "id": "xxx",
    "localConnectionString": "postgres://user:password@db.neon.tech:5432/db"
  }]
}
```

```bash
npx wrangler dev
# Fails: SSL required but not supported in local mode
```

**Solution/Workaround**:
Use conditional connection in code:
```typescript
const url = env.isLocal ? env.DB_URL : env.HYPERDRIVE.connectionString;
const client = postgres(url, {
  fetch_types: false,
  max: 2,
});
```

Or use `wrangler dev --remote` (but this affects production data).

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Tracked internally: SQC-645
- Timeline: Earliest fix is 2026 due to workerd and Workers runtime changes needed
- Affected providers: Neon, any database requiring SSL

---

### Finding 1.5: Transaction Mode Resets SET Statements Between Queries

**Trust Score**: TIER 1 - Official
**Source**: [Cloudflare Hyperdrive Docs - How Hyperdrive Works](https://developers.cloudflare.com/hyperdrive/configuration/how-hyperdrive-works/)
**Date**: 2025 (official docs)
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Hyperdrive operates in transaction mode, where connections are returned to the pool after each transaction. When a connection is returned, it is RESET, so SET commands won't persist. A single Worker invocation may obtain multiple connections and need to SET configurations for every query or transaction.

**Reproduction**:
```typescript
// ❌ WRONG - SET won't persist across queries
await client.query('SET search_path TO myschema');
await client.query('SELECT * FROM mytable'); // Uses default search_path!
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - SET within transaction
await client.query('BEGIN');
await client.query('SET search_path TO myschema');
await client.query('SELECT * FROM mytable'); // Now uses myschema
await client.query('COMMIT');
```

**WARNING**: Wrapping multiple database operations in a single transaction to maintain SET state will affect Hyperdrive's performance and scaling.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related: Connection multiplexing limitations
- Impact on: Connection pooling efficiency

---

### Finding 1.6: Wrangler Proposes Unsupported Remote Binding Configuration

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11674](https://github.com/cloudflare/workers-sdk/issues/11674)
**Date**: 2025-12-16
**Verified**: Yes
**Impact**: LOW (confusing UX, not a runtime issue)
**Already in Skill**: No

**Description**:
When running `wrangler dev`, the CLI suggests configuring Hyperdrive binding with `--remote` flag, but this configuration is not actually supported by Hyperdrive. This creates confusion during setup.

**Reproduction**:
```bash
npx wrangler dev
# Suggests: "Configure Hyperdrive with --remote"
# But this doesn't work as expected
```

**Solution/Workaround**:
Ignore the suggestion. Use proper local development setup via environment variable or localConnectionString.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue (UX improvement needed)
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Prisma Client Reuse Causes Hangs in Workers

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #28193](https://github.com/prisma/prisma/issues/28193)
**Date**: 2025-09-01 (estimated)
**Verified**: Multiple users confirmed
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Reusing a Prisma client instance across requests in Cloudflare Workers causes the Worker to hang and timeout. The first request sometimes works, but subsequent requests hang. This is because Prisma's connection pool attempts to reuse connections across request contexts, which violates Workers' I/O isolation.

**Reproduction**:
```typescript
// ❌ WRONG - Global Prisma client reused across requests
const prisma = new PrismaClient({ adapter });

export default {
  async fetch(request: Request, env: Bindings) {
    // First request: works
    // Subsequent requests: hang indefinitely
    const users = await prisma.user.findMany();
    return Response.json({ users });
  }
};
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - Create new client per request
export default {
  async fetch(request: Request, env: Bindings, ctx: ExecutionContext) {
    const pool = new Pool({
      connectionString: env.HYPERDRIVE.connectionString,
      max: 5
    });
    const adapter = new PrismaPg(pool);
    const prisma = new PrismaClient({ adapter });

    try {
      const users = await prisma.user.findMany();
      return Response.json({ users });
    } finally {
      ctx.waitUntil(pool.end());
    }
  }
};
```

**Community Validation**:
- Multiple users confirm this issue
- Official Prisma docs now recommend per-request client creation for Workers
- Related to: Workers' request isolation model

**Cross-Reference**:
- Related: "Cannot perform I/O on behalf of a different request" error
- See also: Prisma Edge runtime documentation

---

### Finding 2.2: Neon Serverless Driver Incompatible with Hyperdrive

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Neon GitHub Repo](https://github.com/neondatabase/serverless), [Cloudflare Docs](https://developers.cloudflare.com/workers/databases/third-party-integrations/neon/)
**Date**: 2025
**Verified**: Official recommendation from both Neon and Cloudflare
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Neon's serverless driver uses WebSockets instead of TCP, which bypasses Hyperdrive's connection pooling and caching. Using the Neon serverless driver with Hyperdrive provides no benefit and may be slower than direct connection.

**Reproduction**:
```typescript
// ❌ WRONG - Neon serverless driver bypasses Hyperdrive
import { neon } from '@neondatabase/serverless';

const sql = neon(env.HYPERDRIVE.connectionString);
// This uses WebSockets, not TCP - Hyperdrive doesn't help
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - Use traditional TCP driver with Hyperdrive
import postgres from 'postgres';

const sql = postgres(env.HYPERDRIVE.connectionString, {
  prepare: true,
  max: 5
});
```

**Community Validation**:
- Neon GitHub repo explicitly states: "On Cloudflare Workers, consider using Cloudflare Hyperdrive instead of this driver"
- Cloudflare docs recommend: "use a driver like node-postgres (pg) or Postgres.js to connect directly to the underlying database instead of the Neon serverless driver"

**Cross-Reference**:
- Related: Hyperdrive requires TCP connections
- Also applies to: Any WebSocket-based database driver

---

### Finding 2.3: Supabase - Use Direct Connection String, Not Pooled

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Cloudflare Docs - Supabase](https://developers.cloudflare.com/hyperdrive/examples/connect-to-postgres/postgres-database-providers/supabase/)
**Date**: 2025
**Verified**: Official Cloudflare documentation
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When connecting to Supabase via Hyperdrive, you must use the Direct connection string, not the pooled connection string (Supavisor). Using the pooled connection creates double-pooling which can cause issues.

**Reproduction**:
```bash
# ❌ WRONG - Using Supabase pooled connection (Supavisor)
npx wrangler hyperdrive create my-supabase \
  --connection-string="postgres://user:password@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
```

**Solution/Workaround**:
```bash
# ✅ CORRECT - Use Supabase direct connection
npx wrangler hyperdrive create my-supabase \
  --connection-string="postgres://user:password@db.projectref.supabase.co:5432/postgres"
```

**Community Validation**:
- Official Cloudflare Hyperdrive documentation
- Reason: Hyperdrive provides its own pooling, double-pooling causes issues

**Cross-Reference**:
- Related: Connection pooling architecture
- Note: Supavisor doesn't support prepared statements, which breaks Hyperdrive caching

---

### Finding 2.4: Drizzle ORM with Nitro 3 - 95% Failure Rate with useDatabase

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #3893](https://github.com/nitrojs/nitro/issues/3893)
**Date**: 2025
**Verified**: Reproduced by multiple users
**Impact**: HIGH (for Nitro 3 users)
**Already in Skill**: No

**Description**:
Using Drizzle ORM with Nitro 3's built-in `useDatabase` (db0/integrations/drizzle) fails with 500 errors approximately 95% of the time when deployed to Cloudflare Workers with Hyperdrive.

**Reproduction**:
```typescript
// In Nitro 3 app with db0/integrations/drizzle
import { useDatabase } from 'db0';
import { drizzle } from 'db0/integrations/drizzle';

export default eventHandler(async () => {
  const db = useDatabase();
  const users = await drizzle(db).select().from(usersTable);
  // Fails ~95% of the time with 500 error
});
```

**Solution/Workaround**:
Create Drizzle client directly without Nitro's useDatabase:
```typescript
import postgres from 'postgres';
import { drizzle } from 'drizzle-orm/postgres-js';

export default eventHandler(async (event) => {
  const sql = postgres(event.context.cloudflare.env.HYPERDRIVE.connectionString, {
    max: 5,
    prepare: true
  });
  const db = drizzle(sql);
  const users = await db.select().from(usersTable);
  event.context.cloudflare.ctx.waitUntil(sql.end());
  return { users };
});
```

**Community Validation**:
- Multiple users report the same ~95% failure rate
- Error: "Cannot perform I/O on behalf of a different request"
- Workaround confirmed working by issue reporters

---

### Finding 2.5: postgres.js Minimum Version 3.4.5 for Hyperdrive Caching

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Cloudflare Docs](https://developers.cloudflare.com/hyperdrive/examples/connect-to-postgres/postgres-drivers-and-libraries/postgres-js/), GitHub issues
**Date**: 2025
**Verified**: Official documentation
**Impact**: MEDIUM
**Already in Skill**: Partially (skill says 3.4.8, should clarify minimum)

**Description**:
postgres.js requires version 3.4.5+ for Hyperdrive compatibility. Earlier versions may work but don't support prepared statement caching properly. Current skill recommends 3.4.8 but doesn't explain why minimum version matters.

**Reproduction**:
```bash
npm install postgres@3.4.0
# Caching may not work properly
```

**Solution/Workaround**:
```bash
npm install postgres@3.4.8
```

**Community Validation**:
- Official Cloudflare documentation specifies 3.4.5 minimum
- Related to: May 2025 prepared statement caching improvements

**Cross-Reference**:
- Skill currently says: "postgres@3.4.8" without explaining minimum version requirement

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Case-Sensitive Table Names Migration Gotcha

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Mats' Blog - Migrating from D1 to Hyperdrive](https://mats.coffee/blog/d1-to-hyperdrive)
**Date**: 2025
**Verified**: Blog post (single source)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When migrating from D1 to Hyperdrive (PostgreSQL), developers encounter issues with case-sensitive table names. D1 (SQLite) is case-insensitive by default, but PostgreSQL is case-sensitive with identifiers.

**Solution**:
```sql
-- SQLite/D1 (case-insensitive)
SELECT * FROM MyTable;
SELECT * FROM mytable;  -- Same result

-- PostgreSQL (case-sensitive)
SELECT * FROM MyTable;   -- Error if table is "mytable"
SELECT * FROM "MyTable"; -- Correct if table created with quotes
SELECT * FROM mytable;   -- Correct if table created without quotes (lowercased)
```

**Consensus Evidence**:
- Blog post mentions: "prepared to spend an afternoon wrestling with case-sensitive table names"
- Common PostgreSQL migration issue (not Hyperdrive-specific)

**Recommendation**: Add to Community Tips section as PostgreSQL migration gotcha

---

### Finding 3.2: PlanetScale/Vitess - No Database-Level Foreign Keys

**Trust Score**: TIER 3 - Community Consensus
**Source**: [PlanetScale MySQL Compatibility Docs](https://planetscale.com/docs/vitess/troubleshooting/mysql-compatibility)
**Date**: 2025
**Verified**: PlanetScale official documentation
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using Hyperdrive with PlanetScale (Vitess-based), database-level foreign keys are not supported. This is a Vitess limitation, not a Hyperdrive limitation, but affects Hyperdrive users connecting to PlanetScale.

**Solution**:
Enforce referential integrity in application code or services:
```typescript
// Instead of database foreign key constraint:
// CREATE TABLE orders (user_id INT FOREIGN KEY REFERENCES users(id));

// Enforce in application:
async function createOrder(userId: number, orderData: any) {
  const user = await db.query('SELECT id FROM users WHERE id = $1', [userId]);
  if (!user.rows.length) {
    throw new Error('User not found');
  }
  await db.query('INSERT INTO orders (user_id, ...) VALUES ($1, ...)', [userId, ...]);
}
```

**Consensus Evidence**:
- PlanetScale documentation explicitly states this limitation
- Vitess 23 release notes confirm (2025)
- Affects all Vitess-based databases

**Recommendation**: Add to database-specific limitations section for MySQL/PlanetScale

---

### Finding 3.3: Two Workers on Same Process - Localhost Port Conflict

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #9485](https://github.com/cloudflare/workers-sdk/issues/9485)
**Date**: 2025-06-05
**Verified**: Open issue
**Impact**: LOW (specific use case)
**Already in Skill**: No

**Description**:
When running two Workers in the same wrangler dev process, both using Hyperdrive to localhost databases, the second Worker fails due to Hyperdrive's localhost proxy binding to the same port.

**Reproduction**:
```bash
# wrangler.jsonc with multiple Workers, both using Hyperdrive
npx wrangler dev
# Second Worker fails: port already in use
```

**Solution/Workaround**:
Run Workers in separate processes or use different local databases on different ports.

**Consensus Evidence**:
- GitHub issue open since June 2025
- Specific to local development with multiple Workers

**Recommendation**: Low priority - edge case for local development

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: SECP521R1 Certificate Not Supported

**Trust Score**: TIER 4 - Low Confidence
**Source**: [GitHub Issue #8671](https://github.com/cloudflare/workers-sdk/issues/8671)
**Date**: 2025-03-25
**Verified**: No (open issue, no resolution)
**Impact**: Unknown

**Why Flagged**:
- [x] Single source only
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [x] May be version-specific (old)
- [ ] Outdated (pre-2024)

**Description**:
SECP521R1 elliptic curve not supported for Hyperdrive TLS certificates. Unclear if this is still an issue or has been resolved.

**Recommendation**: Manual verification required. DO NOT add to skill without human review and testing.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| nodejs_compat flag required | Critical Rules | Fully covered |
| Connection pool max: 5 | Connection Patterns | Fully covered |
| mysql2 disableEval required | Quick Start / Error table | Fully covered |
| Unsupported MySQL auth plugins | Unsupported Features | Partially covered (mentions caching_sha2_password) |
| postgres.js minimum version | Latest Versions | Partially covered (says 3.4.8 without explaining minimum) |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Windows local hostname | Known Issues Prevention | Add as Issue #11 with platform-specific workarounds |
| 1.2 postgres.js IP address hang | Known Issues Prevention | Add as Issue #12 with clear "use hostname" guidance |
| 1.4 Local SSL not supported | Local Development section | Expand with conditional connection pattern |
| 1.5 Transaction mode SET resets | Critical Rules / Performance Best Practices | Add warning about SET statement persistence |
| 2.1 Prisma client reuse | ORM Integration / Prisma section | Add warning and per-request pattern |
| 2.2 Neon serverless driver | ORM Integration / Known Issues | Add to "Never Do" rules |
| 2.3 Supabase direct connection | Connection String Formats | Add Supabase-specific guidance |
| 2.4 Drizzle with Nitro 3 | ORM Integration / Drizzle section | Add Nitro-specific workaround |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 MySQL 8.0.43 auth | Supported Databases / Troubleshooting | Update MySQL version compatibility |
| 2.5 postgres.js version | Latest Versions | Clarify minimum version requirement |
| 3.1 Case-sensitive tables | Community Tips (new section) | PostgreSQL migration gotcha |
| 3.2 PlanetScale foreign keys | Supported Databases / MySQL section | Vitess-specific limitation |

### Priority 3: Monitor (TIER 4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 4.1 SECP521R1 cert | Old issue, unclear status | Test with current version |
| 3.3 Localhost port conflict | Edge case, low impact | Monitor for additional reports |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "hyperdrive" in workers-sdk (2024+) | 50+ | 15 |
| Issues with "hyperdrive" label | 30+ | 8 |
| "postgres.js" + "hyperdrive" | 12 | 3 |
| "prisma" + "hyperdrive" | 8 | 2 |
| "drizzle" + "hyperdrive" | 6 | 1 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "hyperdrive cloudflare 2025" | 0 | N/A |
| Related searches directed to GitHub issues instead | - | - |

### Other Sources

| Source | Notes |
|--------|-------|
| [Cloudflare Blog](https://blog.cloudflare.com) | 2 relevant posts on Hyperdrive improvements |
| [Cloudflare Docs](https://developers.cloudflare.com/hyperdrive/) | Primary reference for transaction mode, local dev |
| [Neon Blog](https://neon.com/blog/hyperdrive-neon-faq) | Hyperdrive + Neon FAQ |
| [PlanetScale Docs](https://planetscale.com/docs) | Vitess limitations |
| [Mats' Blog](https://mats.coffee/blog/d1-to-hyperdrive) | D1 to Hyperdrive migration |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `WebSearch` for Stack Overflow, blogs, and official docs
- `gh release list` for version history

**Limitations**:
- Stack Overflow has very limited Hyperdrive content (service too new, most issues on GitHub)
- Some Cloudflare internal tracking (JIRA tickets) not publicly accessible
- Windows hostname issue still open, no official fix timeline

**Time Spent**: ~45 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that Finding 1.5 (transaction mode SET resets) matches current Cloudflare official documentation before adding to skill.

**For api-method-checker**: Verify postgres.js version 3.4.5+ supports the `prepare: true` configuration option.

**For code-example-validator**: Validate Prisma per-request client pattern in Finding 2.1 works with current Prisma ORM version.

---

## Integration Guide

### Adding TIER 1-2 Findings to SKILL.md

**For Known Issues Prevention section:**

```markdown
### Issue #11: Windows/macOS Local Development - Hostname Resolution Failure

**Error**: Connection fails with hostname like `xxx.hyperdrive.local`
**Source**: [GitHub Issue #11556](https://github.com/cloudflare/workers-sdk/issues/11556)
**Platforms**: Windows, macOS 26 Tahoe, Ubuntu 24.04 LTS (wrangler@4.54.0+)
**Why It Happens**: Hyperdrive local proxy hostname fails to resolve on certain platforms
**Prevention**:

Use environment variable for local development:
```bash
export CLOUDFLARE_HYPERDRIVE_LOCAL_CONNECTION_STRING_HYPERDRIVE="postgres://user:password@localhost:5432/db"
npx wrangler dev
```

Or use `wrangler dev --remote` (caution: uses production database)

**Status**: Open issue, workaround available

---

### Issue #12: postgres.js Hangs with IP Addresses

**Error**: Connection hangs indefinitely with no error message
**Source**: [GitHub Issue #6179](https://github.com/cloudflare/workers-sdk/issues/6179)
**Why It Happens**: Using IP address instead of hostname in connection string
**Prevention**:

```typescript
// ❌ WRONG - IP address
const connection = "postgres://user:password@192.168.1.100:5432/db"

// ✅ CORRECT - Hostname
const connection = "postgres://user:password@db.example.com:5432/db"
```

**Additional Gotcha**: Miniflare (local dev) only supports A-z0-9 characters in passwords, despite Postgres allowing special characters. Use simple passwords for local development.
```

**For Never Do section:**

```markdown
❌ Use Neon serverless driver with Hyperdrive (uses WebSockets, bypasses Hyperdrive pooling)
❌ Use Supabase pooled connection string (Supavisor) with Hyperdrive (double-pooling causes issues)
❌ Reuse Prisma client instances across requests in Workers (causes hangs and timeouts)
❌ Use IP addresses in connection strings instead of hostnames (causes postgres.js to hang)
❌ Expect SET statements to persist across queries (transaction mode resets connections)
```

**For ORM Integration / Prisma section:**

```markdown
### Prisma ORM

**CRITICAL**: Do NOT reuse Prisma client across requests in Workers. Create new client per request.

```typescript
// ❌ WRONG - Global client causes hangs
const prisma = new PrismaClient({ adapter });

export default {
  async fetch(request: Request, env: Bindings) {
    const users = await prisma.user.findMany(); // Hangs after first request
    return Response.json({ users });
  }
};

// ✅ CORRECT - Per-request client
export default {
  async fetch(request: Request, env: Bindings, ctx: ExecutionContext) {
    const pool = new Pool({
      connectionString: env.HYPERDRIVE.connectionString,
      max: 5
    });
    const adapter = new PrismaPg(pool);
    const prisma = new PrismaClient({ adapter });

    try {
      const users = await prisma.user.findMany();
      return Response.json({ users });
    } finally {
      ctx.waitUntil(pool.end());
    }
  }
};
```

**Source**: [GitHub Issue #28193](https://github.com/prisma/prisma/issues/28193)
```

**For Local Development section:**

```markdown
### SSL/TLS Limitations in Local Development

**Important**: Local Hyperdrive connections do NOT support SSL. This affects databases that require SSL (e.g., Neon, most cloud providers).

**Workaround - Conditional Connection**:
```typescript
const url = env.isLocal ? env.DB_URL : env.HYPERDRIVE.connectionString;
const client = postgres(url, {
  fetch_types: false,
  max: 2,
});
```

**Alternative**: Use `wrangler dev --remote` (⚠️ connects to production database)

**Timeline**: SSL support planned for 2026 (requires workerd/Workers runtime changes)
**Source**: [GitHub Issue #10124](https://github.com/cloudflare/workers-sdk/issues/10124), tracked as SQC-645
```

---

**Research Completed**: 2026-01-21 10:30
**Next Research Due**: After Hyperdrive major update or Q2 2026 (whichever comes first)

---

## Sources

- [Cloudflare Hyperdrive Documentation](https://developers.cloudflare.com/hyperdrive/)
- [Cloudflare Workers SDK GitHub](https://github.com/cloudflare/workers-sdk)
- [Mats' blog - Migrating from Cloudflare D1 to Hyperdrive](https://mats.coffee/blog/d1-to-hyperdrive)
- [Supabase Hyperdrive Integration](https://developers.cloudflare.com/hyperdrive/examples/connect-to-postgres/postgres-database-providers/supabase/)
- [Neon Hyperdrive Guide](https://neon.com/docs/guides/cloudflare-hyperdrive)
- [Using Hyperdrive with Neon: FAQ](https://neon.com/blog/hyperdrive-neon-faq)
- [Cloudflare vs. Deno: The Truth About Edge Computing in 2025](https://dev.to/dataformathub/cloudflare-vs-deno-the-truth-about-edge-computing-in-2025-1afj)
- [PlanetScale MySQL Compatibility](https://planetscale.com/docs/vitess/troubleshooting/mysql-compatibility)
- [Prisma ORM Hyperdrive Documentation](https://developers.cloudflare.com/hyperdrive/examples/connect-to-postgres/postgres-drivers-and-libraries/prisma-orm/)
- [Better Auth Issue #2274](https://github.com/better-auth/better-auth/issues/2274)
- [Nitro Issue #3893](https://github.com/nitrojs/nitro/issues/3893)
