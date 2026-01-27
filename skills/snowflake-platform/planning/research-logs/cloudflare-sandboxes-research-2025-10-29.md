# Cloudflare Sandboxes Research Report

**Date**: 2025-10-29
**Researcher**: Claude (via Claude Code CLI)
**Purpose**: Comprehensive research on Cloudflare Sandboxes for potential skill creation

---

## Executive Summary

**What They Are**: Cloudflare Sandboxes are container-based isolated code execution environments that run on Cloudflare's edge network. They allow Cloudflare Workers to execute arbitrary commands, manage files, run background processes, and expose services in a secure, stateful container.

**Key Innovation**: Sandboxes solve the fundamental limitation of Workers - they can now run full OS processes (Python scripts, Node.js, system commands, git operations) that require filesystem access, process spawning, and state persistence.

**Status**: Open Beta (announced June 24, 2025) - API stable but evolving. Production-ready.

**Critical Finding**: Sandboxes use **Durable Objects with Containers** - a new Cloudflare primitive that extends Durable Objects with container support. This is NOT just Workers. The container runs Ubuntu 22.04 with Python, Node.js, Bun, and common tools.

---

## 1. What Are Cloudflare Sandboxes?

### Architecture Overview

Cloudflare Sandboxes are built on three layers:

1. **Worker Layer**: Your Cloudflare Worker (standard Workers runtime)
2. **Durable Object Layer**: `Sandbox` class extends `Container` (Durable Object with container support)
3. **Container Layer**: Ubuntu 22.04 container running Bun HTTP server (port 3000)

```
Worker fetch() → Sandbox Durable Object → Container HTTP API → Shell/Filesystem
```

### How They Differ from Workers

| Feature | Workers | Sandboxes |
|---------|---------|-----------|
| Runtime | V8 isolate | Full Ubuntu container |
| Process spawning | ❌ No | ✅ Yes |
| Filesystem | ❌ No (only KV/R2/D1) | ✅ Yes (full POSIX filesystem) |
| Python/Node execution | ❌ Limited (Pyodide/Polyfills) | ✅ Native |
| State persistence | ❌ No | ✅ Yes (per sandbox instance) |
| Git operations | ❌ No | ✅ Yes (native git) |
| Background processes | ❌ No | ✅ Yes (with PID tracking) |
| Cold start | ~0-50ms | ~2-3 minutes (first run, <1s after) |
| Max duration | 30s (free), 15min (paid) | 10min+ (configurable) |

**Critical Distinction**: Sandboxes are NOT a replacement for Workers. They're a **capability extension** for use cases requiring full OS-level execution.

---

## 2. Technical Capabilities

### SDK Package

- **Package**: `@cloudflare/sandbox@0.4.12` (npm)
- **Container Helper**: `@cloudflare/containers@0.0.30` (base class)
- **GitHub**: https://github.com/cloudflare/sandbox-sdk (446 stars)
- **Docs**: https://developers.cloudflare.com/sandbox/

### Container Runtime

**Base Image**: `cloudflare/sandbox:0.4.12` (Docker Hub)

**Installed Software**:
- **Python**: 3.11 (with matplotlib, numpy, pandas, ipython)
- **Node.js**: 20 LTS
- **Bun**: 1.x (powers container HTTP server)
- **System Tools**: git, curl, wget, jq, zip, unzip, file, procps
- **Workspace**: `/workspace` (user code directory)

**Image Size**: 1.03GB (down from 2.63GB in v0.3)

### Core API Methods

#### Command Execution
```typescript
// Execute command and wait for result
const result = await sandbox.exec('python3 -c "print(2 + 2)"');
// result: { stdout: "4\n", stderr: "", exitCode: 0, success: true }

// Stream command output (for long-running)
const stream = await sandbox.execStream('npm install');
```

#### File Operations
```typescript
// Write file
await sandbox.writeFile('/workspace/app.py', 'print("Hello")', { encoding: 'utf-8' });

// Read file
const file = await sandbox.readFile('/workspace/app.py');
// file: { content: 'print("Hello")', encoding: 'utf-8' }

// Check existence
const exists = await sandbox.exists('/workspace/app.py'); // boolean

// Directory operations
await sandbox.mkdir('/workspace/data', { recursive: true });
await sandbox.deleteFile('/workspace/old.txt');
await sandbox.renameFile('/workspace/old.txt', '/workspace/new.txt');
```

#### Git Operations
```typescript
// Clone repository
await sandbox.gitCheckout('https://github.com/user/repo', {
  targetDir: 'my-project',
  branch: 'main'
});
```

#### Background Processes
```typescript
// Start long-running process
const process = await sandbox.startProcess('python3 server.py', {
  processId: 'web-server',
  sessionId: 'default'
});
// process: { id: 'web-server', status: 'running', pid: 1234 }

// List processes
const processes = await sandbox.listProcesses();

// Kill process
await sandbox.killProcess('web-server');

// Stream process logs
const logs = await sandbox.streamProcessLogs('web-server');
```

#### Port Exposure (Preview URLs)
```typescript
// Expose internal port to public URL
const result = await sandbox.exposePort(3000, {
  hostname: request.headers.get('host') // e.g., my-worker.workers.dev
});
// result: { url: 'https://3000-token.my-worker.workers.dev' }

// List exposed ports
const ports = await sandbox.getExposedPorts(hostname);

// Close port
await sandbox.unexposePort(3000);
```

**Production Requirement**: Preview URLs require custom domain with wildcard DNS (`*.yourdomain.com`). `.workers.dev` domains do NOT support subdomain patterns.

#### Code Interpreter
```typescript
// High-level API for Python/JavaScript execution
const interpreter = new CodeInterpreter(sandbox);

// Create execution context
const context = await interpreter.createCodeContext({ language: 'python' });

// Run code with structured output
const execution = await interpreter.runCode('import matplotlib.pyplot as plt; plt.plot([1,2,3])', {
  context,
  language: 'python'
});
// execution: { results: [...], logs: { stdout: [...], stderr: [...] }, error?: ... }
```

**Key Feature**: Code interpreter returns structured outputs (text, HTML, images) similar to Jupyter notebooks, but 90%+ faster cold start.

#### Session Management
```typescript
// Sessions isolate execution contexts (cwd, env vars)
await sandbox.setEnvVars({ API_KEY: 'secret' });

// Commands persist state within same sandbox
await sandbox.exec('cd /workspace/app');
await sandbox.exec('export MY_VAR=value');
await sandbox.exec('pwd'); // returns /workspace/app
await sandbox.exec('echo $MY_VAR'); // returns value
```

---

## 3. Can It Run Node.js/Python SDKs?

### ✅ YES - Full SDK Compatibility

Sandboxes run **native** Python and Node.js, so **any SDK that works on Ubuntu 22.04 works in Sandboxes**.

#### Proven Examples

**1. Claude Code CLI** (Node.js SDK):
```typescript
// From examples/claude-code/src/index.ts
await sandbox.setEnvVars({ ANTHROPIC_API_KEY: env.ANTHROPIC_API_KEY });
const cmd = `cd ${repo} && claude -p "${task}" --permission-mode acceptEdits`;
await sandbox.exec(cmd);
```

**2. OpenAI SDK** (Python):
```typescript
// From examples/code-interpreter/src/index.ts
// Uses @cf/openai/gpt-oss-120b model with sandbox as code interpreter tool
await sandbox.runCode('import numpy as np; np.array([1,2,3]).sum()');
```

**3. Python Packages**:
```bash
# Install any PyPI package
await sandbox.exec('pip3 install requests anthropic openai langchain');
```

**4. npm Packages**:
```bash
# Install any npm package
await sandbox.exec('npm install @anthropic-ai/sdk @openai/api openai-agents');
```

### SDK Compatibility Matrix

| SDK Type | Workers | Sandboxes |
|----------|---------|-----------|
| **Claude Agent SDK** | ❌ No (needs fs, process) | ✅ Yes (native Node.js) |
| **OpenAI SDK** | ✅ Partial (REST only) | ✅ Full (assistants, files, etc.) |
| **Python AI SDKs** | ❌ No (Pyodide limited) | ✅ Yes (native Python) |
| **Node.js file SDKs** | ❌ No (no fs) | ✅ Yes (full fs access) |
| **System CLIs** | ❌ No | ✅ Yes (ffmpeg, imagemagick, etc.) |

**Critical Advantage**: Sandboxes unlock the entire npm/PyPI ecosystem that requires filesystem/process access.

---

## 4. Use Cases

### When to Use Sandboxes (NOT Workers)

1. **AI Code Execution**: LLM-generated Python/JavaScript that needs safe isolation
2. **AI Agent Orchestration**: Running Claude Agent SDK, OpenAI Agents API
3. **Data Analysis**: Pandas, NumPy, matplotlib workflows
4. **Git Operations**: Clone repos, run git commands, analyze codebases
5. **File Processing**: Convert, compress, extract, manipulate files
6. **Build Tools**: Run npm/pip install, compile code, run tests
7. **System Commands**: Use grep, sed, awk, jq, curl, wget
8. **Interactive Environments**: Jupyter-like code interpretation
9. **CI/CD Pipelines**: Run automated tests, linting, builds
10. **Claude Code CLI**: Automate Claude Code tasks (see example)

### When to Use Workers (NOT Sandboxes)

1. **API Routes**: Fast HTTP request/response
2. **Edge Caching**: CDN, static assets
3. **Authentication**: JWT validation, OAuth flows
4. **Database Queries**: D1, KV, R2 access
5. **Webhooks**: Event handlers
6. **Short-lived Logic**: < 50ms execution

**Rule of Thumb**: If it needs `fs`, `child_process`, or native binaries → Sandboxes. If it's stateless HTTP → Workers.

---

## 5. Deployment & Configuration

### wrangler.jsonc Setup

```jsonc
{
  "name": "my-sandbox-worker",
  "main": "src/index.ts",
  "compatibility_date": "2025-05-06",
  "compatibility_flags": ["nodejs_compat"],
  
  // Container configuration
  "containers": [
    {
      "class_name": "Sandbox",
      "image": "./Dockerfile", // or "cloudflare/sandbox:0.4.12"
      "instance_type": "lite", // or "standard", "premium"
      "max_instances": 1 // limit concurrent containers
    }
  ],
  
  // Durable Objects binding
  "durable_objects": {
    "bindings": [
      {
        "class_name": "Sandbox",
        "name": "Sandbox"
      }
    ]
  },
  
  // Required for DO with containers
  "migrations": [
    {
      "new_sqlite_classes": ["Sandbox"],
      "tag": "v1"
    }
  ]
}
```

### Dockerfile

**Minimal** (use official image):
```dockerfile
FROM docker.io/cloudflare/sandbox:0.4.12
EXPOSE 8080  # Required for local dev only
```

**Custom** (extend with additional tools):
```dockerfile
FROM docker.io/cloudflare/sandbox:0.4.12

# Install additional packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    anthropic \
    openai \
    langchain

EXPOSE 8080
```

### Local Development

```bash
# First run builds Docker image (2-3 min)
npm run dev

# Subsequent runs are fast (<10s)
npm run dev

# Test endpoints
curl http://localhost:8787/api/execute -d '{"command": "ls -la"}'
```

**Gotcha**: Docker must be running locally for `wrangler dev`.

### Production Deployment

```bash
# Deploy Worker + Container
npx wrangler deploy

# Wait 2-3 minutes for container provisioning (first deploy only)
# Subsequent deploys are faster
```

**Container Lifecycle**:
- **Cold Start**: ~2-3 min (first deploy or after long idle)
- **Warm Start**: <1s (after initial provision)
- **Sleep After**: 10min default (configurable via `sleepAfter` option)
- **Keep Alive**: Optional flag to prevent sleep

---

## 6. Integration with Existing Cloudflare Services

### ✅ Compatible Services

- **D1**: Yes - use Workers AI SDK or REST API from container
- **KV**: Yes - REST API or SDK
- **R2**: Yes - S3-compatible API or SDK
- **Vectorize**: Yes - REST API
- **Workers AI**: Yes - REST API
- **Queues**: Yes - REST API
- **Workflows**: Yes - can trigger from Worker
- **Analytics Engine**: Yes - REST API

**Pattern**: Use Worker for Cloudflare bindings, pass data to Sandbox for processing.

```typescript
export default {
  async fetch(request: Request, env: Env) {
    // Worker handles Cloudflare services
    const data = await env.DB.prepare('SELECT * FROM users').all();
    
    // Sandbox processes data
    const sandbox = getSandbox(env.Sandbox, 'processor');
    await sandbox.writeFile('/tmp/users.json', JSON.stringify(data));
    const result = await sandbox.exec('python3 process.py /tmp/users.json');
    
    return Response.json({ result });
  }
};
```

### ❌ Incompatible / Limited

- **Durable Objects Storage API**: Container can't directly call `state.storage` (must proxy through Worker)
- **Workers Bindings**: Container doesn't have access to `env` object (must use REST APIs)
- **WebSockets**: Limited (can expose WebSocket server via preview URL, but complex)

---

## 7. Security & Isolation

### Process Isolation (v0.3+)

- **PID Namespace Isolation**: Sandboxed commands run in isolated namespaces
- **Control Plane Protection**: Container's Bun server (port 3000) hidden from sandboxed code
- **Secret Protection**: Platform secrets in `/proc/1/environ` inaccessible
- **Port Protection**: Internal ports (3000, 8888) can't be hijacked

### Session Isolation

- Each sandbox instance has its own session
- Working directory, env vars, background processes persist per sandbox
- Different sandbox IDs = completely isolated environments

### Container Security

- Ubuntu 22.04 base (regular security updates)
- No root access from sandboxed commands (enforced by container runtime)
- Network egress allowed (can call external APIs)
- Filesystem limited to `/workspace` and `/tmp` (best practice)

---

## 8. Known Issues & Limitations

### From GitHub Issues (as of 2025-10-29)

**Open Issues**:
1. **#166**: Listing files hangs indefinitely (file operations bug)
2. **#165**: Type definitions from `@repo/shared` not accessible (TypeScript issue)
3. **#158**: DOs/containers reset during deployment/rollouts (stability issue)
4. **#145**: Cloudflare root certificate not installed by default (HTTPS issue)
5. **#144**: Env vars passed to individual exec commands not being used (config bug)
6. **#139**: Heredoc commands fail in `exec()` (shell escaping issue)
7. **#130**: No S3 bucket mounting (feature request)

**Recently Fixed** (in v0.4.x):
- Commands hanging when reading stdin (#141)
- Escaped quotes in file operations (#70)
- Token extraction regex errors (#153)
- Version mismatch detection (#138)

### Current Limitations

1. **Cold Start**: 2-3 min first run (after that <1s)
2. **Image Size**: 1.03GB (impacts cold start)
3. **Preview URLs**: Require custom domain (`.workers.dev` incompatible)
4. **Docker Required**: Local dev needs Docker running
5. **Beta Status**: API may change (but stable since v0.4)
6. **Cost**: Containers are more expensive than Workers (pricing TBD)

---

## 9. Code Examples

### Example 1: AI Code Execution (Python)

```typescript
import { getSandbox, type Sandbox } from '@cloudflare/sandbox';

export { Sandbox } from '@cloudflare/sandbox';

type Env = {
  Sandbox: DurableObjectNamespace<Sandbox>;
};

export default {
  async fetch(request: Request, env: Env) {
    const { code } = await request.json<{ code: string }>();
    
    // Get sandbox (one per user ID)
    const userId = request.headers.get('X-User-ID') || 'anonymous';
    const sandbox = getSandbox(env.Sandbox, userId);
    
    // Execute Python code safely
    const result = await sandbox.exec(`python3 -c "${code.replace(/"/g, '\\"')}"`);
    
    return Response.json({
      stdout: result.stdout,
      stderr: result.stderr,
      success: result.success
    });
  }
};
```

### Example 2: Git Repository Analysis

```typescript
export default {
  async fetch(request: Request, env: Env) {
    const { repo, query } = await request.json<{ repo: string; query: string }>();
    
    const sandbox = getSandbox(env.Sandbox, crypto.randomUUID());
    
    // Clone repo
    await sandbox.gitCheckout(repo, { targetDir: 'repo' });
    
    // Analyze with grep/find
    const result = await sandbox.exec(`cd repo && grep -r "${query}" .`);
    
    return Response.json({ matches: result.stdout });
  }
};
```

### Example 3: Claude Code CLI Automation

```typescript
// From examples/claude-code/src/index.ts
export default {
  async fetch(request: Request, env: Env) {
    const { repo, task } = await request.json<{ repo: string; task: string }>();
    
    const sandbox = getSandbox(env.Sandbox, crypto.randomUUID().slice(0, 8));
    
    // Clone repo
    const name = repo.split('/').pop() || 'tmp';
    await sandbox.gitCheckout(repo, { targetDir: name });
    
    // Set API key
    await sandbox.setEnvVars({ ANTHROPIC_API_KEY: env.ANTHROPIC_API_KEY });
    
    // Run Claude Code CLI
    const cmd = `cd ${name} && claude -p "${task}" --permission-mode acceptEdits`;
    const logs = await sandbox.exec(cmd);
    
    // Get git diff
    const diff = await sandbox.exec('git diff');
    
    return Response.json({ logs: logs.stdout, diff: diff.stdout });
  }
};
```

### Example 4: Code Interpreter with OpenAI

```typescript
// From examples/code-interpreter/src/index.ts
import { getSandbox } from '@cloudflare/sandbox';

async function executePythonCode(env: Env, code: string): Promise<string> {
  const sandbox = getSandbox(env.Sandbox, 'default');
  const pythonCtx = await sandbox.createCodeContext({ language: 'python' });
  const result = await sandbox.runCode(code, { context: pythonCtx });
  
  // Extract output
  if (result.results?.length) {
    return result.results.map(r => r.text || r.html || JSON.stringify(r)).join('\n');
  }
  
  return result.logs?.stdout?.join('\n') || '';
}
```

---

## 10. Skill Feasibility Assessment

### Should We Create a `cloudflare-sandboxes` Skill?

**✅ YES - Strong Case for Skill**

### Reasons

1. **Complexity**: Setup requires understanding Durable Objects + Containers (new primitive)
2. **Configuration**: wrangler.jsonc has specific requirements (containers, migrations, DOs)
3. **Common Errors**: Docker setup, version mismatches, preview URL config
4. **Token Savings**: High (~70%+) - setup documentation is spread across multiple sources
5. **Newness**: Announced June 2025 - many developers unfamiliar
6. **Integration Patterns**: Connecting Workers + Sandboxes + Cloudflare services non-trivial

### Error Prevention Potential

**Common Mistakes Skill Would Prevent**:

1. **Missing `nodejs_compat` flag** → "fetch is not defined" errors
2. **Missing migrations** → "Class not found" errors
3. **Docker not running** → "Failed to build container" errors
4. **Version mismatch** → Package version != Docker image version
5. **Missing EXPOSE in Dockerfile** → "Port not found" errors (local dev)
6. **Using `.workers.dev` for preview URLs** → URLs don't work
7. **Not awaiting container provisioning** → "Container not ready" errors (first deploy)
8. **Forgetting to export Sandbox class** → "Class not found" errors
9. **Wrong instance type** → Performance/cost issues
10. **Not handling cold starts** → Timeout errors

### Skill Scope

**Skill Name**: `cloudflare-sandboxes`

**What It Should Include**:

1. **Setup Guide**:
   - wrangler.jsonc configuration (containers, DOs, migrations)
   - Dockerfile (minimal vs custom)
   - TypeScript types and imports
   - Local dev setup (Docker requirements)

2. **Templates**:
   - Minimal Worker + Sandbox (basic exec)
   - AI code execution (Python/JavaScript)
   - Git operations (clone + analyze)
   - File processing (read/write/transform)
   - Code interpreter integration

3. **Integration Patterns**:
   - Connecting Workers + Sandboxes
   - Using D1/KV/R2 from Sandboxes
   - Session management strategies
   - Preview URL setup (custom domain)

4. **Troubleshooting**:
   - Cold start handling
   - Version sync detection
   - Docker issues
   - Process isolation errors
   - Port exposure errors

5. **References**:
   - Official docs links
   - GitHub SDK repo
   - npm package
   - Common error messages + fixes

### Token Efficiency Estimate

**Without Skill**: ~15-20k tokens
- Read official docs (5k)
- Trial and error with config (5k)
- Fix Docker issues (3k)
- Fix type errors (2k)
- Fix deployment errors (3k)

**With Skill**: ~4-5k tokens
- Read SKILL.md (3k)
- Use template (1k)
- Deploy successfully first try (1k)

**Savings**: ~70-75%

### When NOT to Use

- Simple Workers tasks (API routes, caching, auth)
- Stateless compute (use Workers)
- Need <50ms latency (use Workers)
- Small-scale file operations (use R2 directly)

---

## 11. Comparison to Alternatives

### vs. Workers

| Feature | Workers | Sandboxes |
|---------|---------|-----------|
| Latency | 0-50ms | 500ms-2min (cold start) |
| Process spawning | No | Yes |
| Filesystem | No | Yes |
| Cost | Low | Higher (TBD) |
| Use case | API, edge logic | Code execution, builds |

### vs. Docker on Vultr/VPS

| Feature | VPS Docker | Sandboxes |
|---------|------------|-----------|
| Global edge | No (single region) | Yes (Cloudflare network) |
| Scaling | Manual | Automatic |
| Cold start | N/A (always on) | 2-3 min (first run) |
| Cost | Fixed (even idle) | Pay-per-use (likely) |
| Setup | Complex (server mgmt) | Simple (wrangler deploy) |

### vs. AWS Lambda

| Feature | Lambda | Sandboxes |
|---------|--------|-----------|
| Runtime | Limited (AL2) | Full Ubuntu |
| Container support | Yes | Yes |
| Filesystem | Ephemeral | Persistent (per sandbox) |
| Cold start | 1-10s | 2-3 min (first), <1s after |
| Edge distribution | Limited | Global (Cloudflare) |

**Sandboxes Sweet Spot**: Need full OS capabilities + Cloudflare ecosystem + edge distribution.

---

## 12. Production Examples

### Known Usage

1. **Claude Code Automation** (examples/claude-code):
   - Clone repo → Run Claude Code CLI → Return diff
   - Proves Node.js CLI compatibility

2. **AI Code Interpreter** (examples/code-interpreter):
   - OpenAI GPT model + Python execution tool
   - Proves LLM code execution viability

3. **Full-Stack Sandbox** (examples/basic):
   - File ops, processes, git, ports, notebooks
   - Proves comprehensive API coverage

### Community Adoption

- **446 GitHub stars** (4 months post-launch)
- **Active development** (PRs merged weekly)
- **Production deployments** (confirmed by Cloudflare)

---

## 13. Future Roadmap (Inferred)

### Likely Coming

1. **S3 Bucket Mounting** (Issue #130)
2. **Better Type Definitions** (Issue #165)
3. **Deployment Stability** (Issue #158)
4. **Pricing Clarity** (currently TBD)
5. **More Base Images** (Alpine, different Python versions)
6. **GPU Support** (for AI workloads)

### Gaps to Watch

1. **Cost Model**: No public pricing yet
2. **Scale Limits**: Max concurrent containers unclear
3. **Long-Running Tasks**: Beyond 10min unclear
4. **Stateful Data**: No persistent storage beyond session

---

## 14. Skill Implementation Plan

If we decide to create `cloudflare-sandboxes` skill:

### Phase 1: Core Setup (Day 1)
- SKILL.md with setup guide
- wrangler.jsonc template
- Dockerfile template
- Basic Worker + exec example
- Common errors reference

### Phase 2: Advanced Patterns (Day 2)
- Code interpreter template
- Git operations template
- File processing template
- Session management guide
- Preview URL setup guide

### Phase 3: Integration (Day 3)
- D1 + Sandboxes pattern
- R2 + Sandboxes pattern
- Workers AI + Sandboxes pattern
- Testing guide
- Deployment checklist

### Phase 4: Verification (Day 4)
- Build working example
- Test all templates
- Verify error prevention
- Measure token savings
- Update VERIFICATION_REPORT.md

---

## 15. Key Takeaways

### For Skill Users

1. **Use Sandboxes When**: Need full OS, process spawning, filesystem, or native SDKs
2. **Avoid For**: Simple API routes, edge caching, stateless compute
3. **Key Integration**: Workers (front) + Sandboxes (heavy compute) = powerful combo
4. **SDK Compatibility**: YES - any Node.js/Python SDK works
5. **Cold Start**: Plan for 2-3 min first run (then fast)

### For Skill Creators

1. **High Value**: Complex setup, many gotchas, new primitive
2. **Error Prevention**: ~10 common errors documented
3. **Token Savings**: ~70% (15-20k → 4-5k tokens)
4. **Templates Needed**: 4-5 (minimal, code-exec, git-ops, file-ops, interpreter)
5. **References**: Official docs, SDK repo, examples, troubleshooting

---

## 16. Resources

### Official Documentation
- **Main Docs**: https://developers.cloudflare.com/sandbox/
- **Get Started**: https://developers.cloudflare.com/sandbox/get-started/
- **API Reference**: https://developers.cloudflare.com/sandbox/api/
- **Guides**: https://developers.cloudflare.com/sandbox/guides/
- **Changelog**: https://developers.cloudflare.com/changelog/2025-06-24-announcing-sandboxes/

### SDK & Code
- **npm Package**: https://www.npmjs.com/package/@cloudflare/sandbox
- **GitHub Repo**: https://github.com/cloudflare/sandbox-sdk
- **Docker Image**: https://hub.docker.com/r/cloudflare/sandbox
- **Examples**: https://github.com/cloudflare/sandbox-sdk/tree/main/examples

### Community
- **GitHub Issues**: https://github.com/cloudflare/sandbox-sdk/issues
- **Developer Discord**: https://discord.cloudflare.com

---

## 17. Conclusion

**Verdict**: Cloudflare Sandboxes are a game-changer for edge compute, enabling full OS-level execution on Cloudflare's network. They solve the Workers limitation for AI agents, code execution, and build tools.

**Skill Recommendation**: **Create `cloudflare-sandboxes` skill**. High complexity, new primitive, many gotchas, strong error prevention potential, and excellent token savings.

**Next Steps**:
1. Review this report
2. Decide: Create skill?
3. If yes: Use `templates/skill-skeleton/` to start
4. Build working example to verify templates
5. Test error prevention (try to break it)
6. Measure token savings
7. Commit to repo

---

**Report Completed**: 2025-10-29 15:30 AEDT
**Total Research Time**: ~2 hours
**Sources Reviewed**: 25+ (docs, code, issues, examples)
**Confidence Level**: High (comprehensive primary source research)
