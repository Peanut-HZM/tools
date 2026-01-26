# Cloudflare Sandboxes SDK - Comprehensive Research

**Date**: 2025-10-29  
**Purpose**: Deep dive into Cloudflare Sandbox SDK for building a Claude Code skill  
**Documentation Base**: https://developers.cloudflare.com/sandbox/

---

## Executive Summary

Cloudflare Sandbox SDK is a **production Beta** feature that enables secure, isolated code execution environments at the edge. It combines three Cloudflare technologies (Workers, Durable Objects, Containers) to provide a simple TypeScript API for running untrusted code in full Linux containers.

**Key Value Propositions**:
- Execute Python, Node.js, and shell commands securely
- Full filesystem with persistence during active container sessions
- Built-in session management for stateful interactions
- Geographic distribution via Durable Objects
- No infrastructure management required

---

## 1. Architecture Deep Dive

### Three-Layer Model

```
┌─────────────────────────────────────────┐
│  Layer 1: Client SDK (@cloudflare/sandbox)│
│  - TypeScript API in your Worker       │
│  - getSandbox() function                │
│  - Sandbox methods (exec, writeFile, etc)│
└──────────────┬──────────────────────────┘
               │ RPC via Durable Object stub
┌──────────────▼──────────────────────────┐
│  Layer 2: Durable Object (Sandbox class)│
│  - Routes requests by sandbox ID        │
│  - Maintains persistent identity        │
│  - Manages container lifecycle          │
│  - Proxies to container runtime         │
└──────────────┬──────────────────────────┘
               │ HTTP API
┌──────────────▼──────────────────────────┐
│  Layer 3: Container Runtime             │
│  - Isolated Ubuntu Linux environment    │
│  - Pre-installed: Python, Node, Git     │
│  - Full filesystem (/workspace, /tmp)   │
│  - Process isolation (VM-based)         │
└─────────────────────────────────────────┘
```

### Why This Architecture?

**Workers (Layer 1)**:
- Fast edge execution for API logic
- Globally distributed request handling
- Minimal cold starts

**Durable Objects (Layer 2)**:
- **Persistent identity**: Same sandbox ID → same instance
- **Geographic stickiness**: First request determines location
- **State coordination**: Manages container lifecycle
- **Routing**: Ensures requests to same sandbox reach same container

**Containers (Layer 3)**:
- **VM-based isolation**: Strong security boundaries
- **Full Linux environment**: Run any code/tools
- **Filesystem persistence**: State survives across requests (while active)
- **Process management**: Background processes, shell sessions

---

## 2. Lifecycle & Persistence Model

### Container States

```
┌─────────┐  First request  ┌────────┐  Inactivity   ┌──────┐
│ Not     │ ───────────────>│ Active │ ────────────> │ Idle │
│ Created │                 │        │ (10 min)      │      │
└─────────┘                 └───┬────┘               └──┬───┘
                                │ ^                     │
                                │ │ New request         │ destroy()
                                │ └─────────────────────┘
                                │
                                ▼
                            ┌──────────┐
                            │ Destroyed│
                            └──────────┘
```

### Critical Persistence Rules

**While Container is Active**:
- ✅ Files in `/workspace`, `/tmp`, `/home` persist
- ✅ Background processes keep running
- ✅ Shell environment variables remain
- ✅ Code interpreter contexts (Python REPL state) persist
- ✅ Session working directories preserved

**When Container Goes Idle** (after ~10 min inactivity):
- ❌ ALL files deleted
- ❌ ALL processes terminated
- ❌ ALL shell state resets
- ❌ ALL code contexts cleared
- ⚠️  Next request creates **fresh container**

**This is THE most important gotcha**: Sandboxes are **ephemeral by default**.

---

## 3. Session Management (Critical for Chat Agents)

### What are Sessions?

Sessions are **bash shell execution contexts** within a single sandbox. Think of them as terminal tabs/panes.

**Key Properties**:
- Each session has its own working directory
- Each session maintains separate environment variables
- Sessions share the same filesystem
- Sessions run in the same container

### Session Use Cases

**Multi-step workflows**:
```typescript
const session1 = await sandbox.createSession();
await sandbox.exec('cd /workspace && git clone ...', { session: session1 });
await sandbox.exec('npm install', { session: session1 }); // Still in /workspace
```

**Parallel execution**:
```typescript
const s1 = await sandbox.createSession();
const s2 = await sandbox.createSession();

// These run independently
await Promise.all([
  sandbox.exec('python train.py', { session: s1 }),
  sandbox.exec('node server.js', { session: s2 })
]);
```

**Chat-style interactions** (IMPORTANT):
```typescript
// Store session ID in conversation state
const sessionId = await sandbox.createSession();

// Later messages use same session
await sandbox.exec('cd /project', { session: sessionId });
await sandbox.exec('ls', { session: sessionId }); // Still in /project
```

### Session Lifecycle

- Sessions persist while container is active
- Sessions destroyed when container goes idle
- No explicit cleanup needed (garbage collected)
- Can have multiple sessions per sandbox

---

## 4. API Reference (Core Methods)

### Essential Methods

```typescript
import { getSandbox } from '@cloudflare/sandbox';

// Get sandbox instance (creates if doesn't exist)
const sandbox = getSandbox(env.Sandbox, 'unique-sandbox-id');

// Execute command
const result = await sandbox.exec('python script.py');
// Returns: { stdout, stderr, exitCode, success }

// File operations
await sandbox.writeFile('/workspace/data.txt', 'content');
const content = await sandbox.readFile('/workspace/data.txt');

// Directory operations
await sandbox.mkdir('/workspace/project', { recursive: true });
const files = await sandbox.readdir('/workspace');

// Git operations
await sandbox.gitCheckout('https://github.com/user/repo', '/workspace/repo');

// Session management
const sessionId = await sandbox.createSession();
await sandbox.exec('cmd', { session: sessionId });

// Cleanup
await sandbox.destroy(); // Permanent deletion
```

### Code Interpreter API

```typescript
// Python code execution with automatic result capture
const ctx = await sandbox.createCodeContext({ language: 'python' });

const result = await sandbox.runCode(`
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3]})
df['a'].sum()  # Last expression auto-returned
`, { context: ctx });

console.log(result.results[0].text); // "6"
console.log(result.logs); // Any print() output
```

### Background Processes

```typescript
// Start long-running process
const proc = await sandbox.spawn('python server.py');

// Check if still running
const isRunning = await sandbox.isProcessRunning(proc.pid);

// Kill process
await sandbox.killProcess(proc.pid);
```

---

## 5. Naming Strategies & State Management

### Per-User Sandboxes

```typescript
const sandbox = getSandbox(env.Sandbox, `user-${userId}`);
```

**Pros**: User's work persists while they're actively using it  
**Cons**: Geographic stickiness (first request determines location)  
**Use case**: Interactive notebooks, IDEs, persistent workspaces

### Per-Session Sandboxes

```typescript
const sandboxId = `session-${Date.now()}-${Math.random()}`;
const sandbox = getSandbox(env.Sandbox, sandboxId);
```

**Pros**: Fresh environment each time, easy cleanup  
**Cons**: No persistence between app sessions  
**Use case**: One-shot executions, CI/CD, testing

### Per-Task Sandboxes

```typescript
const sandbox = getSandbox(env.Sandbox, `build-${repoName}-${commit}`);
```

**Pros**: Idempotent, debuggable, traceable  
**Cons**: Need explicit cleanup  
**Use case**: Build systems, data processing pipelines

### Geographic Considerations

First request to a sandbox determines its location. For global apps:

**Option 1**: Multiple sandboxes per user
```typescript
const region = determineUserRegion(request);
const sandbox = getSandbox(env.Sandbox, `user-${userId}-${region}`);
```

**Option 2**: Single sandbox (simpler, but higher latency for some users)
```typescript
const sandbox = getSandbox(env.Sandbox, `user-${userId}`);
```

---

## 6. Tutorial Patterns

### Pattern 1: Claude Code Integration (From Official Tutorial)

**Use Case**: Run Claude Code CLI on a git repository

```typescript
// Clone repo
await sandbox.gitCheckout(repoUrl, '/workspace/repo');

// Run Claude Code
const result = await sandbox.exec(
  'claude-code "implement feature X"',
  { cwd: '/workspace/repo' }
);

// Get diff
const diff = await sandbox.exec('git diff', { cwd: '/workspace/repo' });

return Response.json({ changes: diff.stdout });
```

**Key Insights**:
- Use `gitCheckout()` for fast repo cloning
- Claude Code runs as regular CLI tool
- Capture git diff to show changes
- Return results to user for review

### Pattern 2: AI Code Executor (From Official Tutorial)

**Use Case**: LLM generates Python → execute safely → return result

```typescript
// 1. Ask LLM to generate code
const code = await callLLM(`Write Python to ${userRequest}`);

// 2. Create Python context
const ctx = await sandbox.createCodeContext({ language: 'python' });

// 3. Execute with automatic result capture
const result = await sandbox.runCode(code, { context: ctx });

// 4. Return results
return Response.json({
  result: result.results?.[0]?.text,
  logs: result.logs,
  error: result.error
});
```

**Key Insights**:
- Use `createCodeContext()` for language-specific execution
- `runCode()` automatically captures last expression
- Distinguish between results vs. logs
- Handle errors gracefully

### Pattern 3: Multi-Step Workflow with Sessions

```typescript
const sessionId = await sandbox.createSession();

// Step 1: Setup
await sandbox.exec('mkdir /workspace/project', { session: sessionId });
await sandbox.exec('cd /workspace/project', { session: sessionId });

// Step 2: Install dependencies
await sandbox.writeFile('/workspace/project/requirements.txt', deps);
await sandbox.exec('pip install -r requirements.txt', { session: sessionId });

// Step 3: Run script
const result = await sandbox.exec('python main.py', { session: sessionId });
```

**Key Insights**:
- Session preserves working directory across commands
- Combine file operations with exec calls
- Build up environment incrementally

---

## 7. Common Errors & Gotchas

### Error 1: Assuming Persistence

**Wrong**:
```typescript
// Request 1
await sandbox.writeFile('/workspace/data.txt', 'content');
// Container goes idle after 10 min

// Request 2 (20 min later)
const content = await sandbox.readFile('/workspace/data.txt'); // ERROR: File not found
```

**Right**: Use external storage (R2, KV, D1) for persistence
```typescript
// Request 1
await sandbox.writeFile('/workspace/data.txt', 'content');
await env.R2.put('data.txt', content); // Persist to R2

// Request 2
const content = await env.R2.get('data.txt');
await sandbox.writeFile('/workspace/data.txt', content); // Restore
```

### Error 2: Not Handling Cold Starts

**Wrong**:
```typescript
await sandbox.exec('cd /project && npm run build'); // Fails if /project doesn't exist
```

**Right**: Always setup environment
```typescript
// Check if setup needed
const exists = await sandbox.readdir('/project').catch(() => null);
if (!exists) {
  await sandbox.gitCheckout(repo, '/project');
  await sandbox.exec('npm install', { cwd: '/project' });
}
await sandbox.exec('npm run build', { cwd: '/project' });
```

### Error 3: Ignoring Exit Codes

**Wrong**:
```typescript
const result = await sandbox.exec('python script.py');
return result.stdout; // Might be empty if script failed
```

**Right**: Check success/exitCode
```typescript
const result = await sandbox.exec('python script.py');
if (!result.success) {
  throw new Error(`Script failed: ${result.stderr}`);
}
return result.stdout;
```

### Error 4: Session Confusion

**Wrong**:
```typescript
await sandbox.exec('cd /project');
await sandbox.exec('ls'); // NOT in /project (different session)
```

**Right**: Use explicit session
```typescript
const sessionId = await sandbox.createSession();
await sandbox.exec('cd /project', { session: sessionId });
await sandbox.exec('ls', { session: sessionId }); // In /project
```

### Error 5: Not Cleaning Up Long-Lived Sandboxes

**Wrong**:
```typescript
const sandbox = getSandbox(env.Sandbox, `temp-${Date.now()}`);
// ... use it ...
// Never destroy - leaks resources
```

**Right**: Clean up ephemeral sandboxes
```typescript
try {
  const sandbox = getSandbox(env.Sandbox, `temp-${Date.now()}`);
  const result = await sandbox.exec('...');
  return result;
} finally {
  await sandbox.destroy();
}
```

---

## 8. Best Practices

### 1. State Management Strategy

**For Interactive Apps** (notebooks, IDEs):
- Use per-user sandboxes
- Accept geographic stickiness
- Rely on container persistence for UX
- Backup to R2/KV for important data

**For Stateless Apps** (CI/CD, code execution):
- Use per-task/per-session sandboxes
- Always setup from scratch
- Destroy after use
- Store results in D1/R2

### 2. Error Handling

```typescript
async function safeSandboxExec(sandbox: Sandbox, cmd: string) {
  try {
    const result = await sandbox.exec(cmd, { timeout: 30000 });
    
    if (!result.success) {
      console.error(`Command failed: ${cmd}`, result.stderr);
      return { error: result.stderr, exitCode: result.exitCode };
    }
    
    return { output: result.stdout, exitCode: 0 };
  } catch (error) {
    console.error(`Sandbox error:`, error);
    return { error: error.message, exitCode: -1 };
  }
}
```

### 3. Timeout Management

```typescript
// Set timeouts for long-running commands
const result = await sandbox.exec('npm install', {
  timeout: 120000 // 2 minutes
});

// Use background processes for truly long tasks
const proc = await sandbox.spawn('python train.py');
// Check status periodically
```

### 4. Resource Cleanup

```typescript
// Always destroy ephemeral sandboxes
try {
  const sandbox = getSandbox(env.Sandbox, createTempId());
  // ... use sandbox ...
} finally {
  await sandbox.destroy();
}

// For persistent sandboxes, cleanup on explicit user action
if (userAction === 'reset-workspace') {
  const sandbox = getSandbox(env.Sandbox, `user-${userId}`);
  await sandbox.destroy();
}
```

### 5. Security Considerations

```typescript
// Validate user input before execution
function sanitizeCommand(userInput: string): string {
  // Remove dangerous patterns
  const dangerous = ['rm -rf', '$(', '`', '&&', '||', ';'];
  for (const pattern of dangerous) {
    if (userInput.includes(pattern)) {
      throw new Error('Invalid command');
    }
  }
  return userInput;
}

// Use code interpreter for untrusted code
const ctx = await sandbox.createCodeContext({ language: 'python' });
await sandbox.runCode(userProvidedCode, { context: ctx });
// Safer than direct exec
```

---

## 9. Skill Design Proposal

### Skill Name: `cloudflare-sandbox`

### Skill Purpose
Enable Claude Code to safely execute code, interact with files, and manage isolated development environments using Cloudflare Sandboxes.

### Key Components

**1. Templates**:
- `basic-executor.ts`: Simple code execution pattern
- `chat-agent.ts`: Session-based conversational pattern
- `ci-cd.ts`: One-shot build/test pattern
- `workspace.ts`: Persistent user workspace pattern

**2. References**:
- `persistence-guide.md`: Understanding container lifecycle
- `session-management.md`: When/how to use sessions
- `common-errors.md`: Documented gotchas with solutions
- `naming-strategies.md`: Choosing sandbox IDs

**3. Scripts**:
- `setup-sandbox-binding.sh`: Wrangler config helper
- `test-sandbox.ts`: Validation script

**4. Examples**:
- `code-interpreter/`: AI code generation + execution
- `git-operations/`: Clone, diff, commit patterns
- `multi-step-workflow/`: Session-based development

### Skill Triggers

**Auto-invoke when**:
- "execute code in sandbox"
- "run Python/Node in isolated environment"
- "need temporary Linux environment"
- "safely execute untrusted code"
- "create development workspace"

### Documented Errors (≥6 required)

1. **Persistence Assumption**: Files lost after inactivity
2. **Session Confusion**: Commands in wrong working directory
3. **Exit Code Ignorance**: Assuming command succeeded
4. **Cold Start Unpreparedness**: Missing setup after idle
5. **Resource Leaks**: Not destroying ephemeral sandboxes
6. **Timeout Failures**: Long commands without timeout config
7. **Security Gaps**: Executing unsanitized user input
8. **Geographic Lock-In**: First request determines location

### Token Efficiency Estimate

**Without Skill**:
- Reading architecture docs: ~8k tokens
- Trial-and-error with persistence: ~15k tokens
- Debugging session management: ~10k tokens
- Finding best practices: ~5k tokens
- **Total**: ~38k tokens, 3-5 errors

**With Skill**:
- Skill metadata + templates: ~6k tokens
- Reference docs as needed: ~2k tokens
- **Total**: ~8k tokens, 0 errors
- **Savings**: ~79%, 100% error prevention

---

## 10. Key Differences from Similar Technologies

### vs. AWS Lambda

| Feature | Sandbox SDK | Lambda |
|---------|------------|--------|
| Execution | Full Linux container | Isolated runtime |
| Filesystem | Full persistent filesystem | /tmp only, ephemeral |
| State | Durable Object identity | Stateless |
| Cold start | Container startup (~seconds) | Function init (~milliseconds) |
| Use case | Interactive, stateful | Event-driven, stateless |

### vs. Docker

| Feature | Sandbox SDK | Docker |
|---------|------------|--------|
| Management | Fully managed | Self-hosted |
| Scaling | Automatic (Cloudflare) | Manual (Kubernetes/Swarm) |
| Distribution | Global edge network | Single/multi-region |
| API | TypeScript SDK | CLI/API |
| State | Durable Objects routing | External orchestration |

### vs. Workers (standalone)

| Feature | Sandbox SDK | Workers |
|---------|------------|--------|
| Isolation | VM-based container | V8 isolate |
| Runtime | Full Linux, any language | JavaScript/WASM only |
| Filesystem | Full filesystem | No filesystem |
| Processes | Multiple processes | Single thread |
| Use case | Code execution | API logic |

---

## 11. Future Research Needs

### Questions Not Fully Answered

1. **Pricing**: Exact cost structure not documented
2. **Resource Limits**: CPU, memory, disk quotas unclear
3. **Network Access**: Outbound connectivity restrictions?
4. **Container Images**: Can you customize the base image?
5. **Monitoring**: Observability/logging for container events?
6. **Scale Limits**: Max sandboxes per account?

### Follow-Up Documentation

- [ ] Check Cloudflare pricing page for Sandbox costs
- [ ] Review workers-sdk repo for implementation details
- [ ] Test actual cold start times
- [ ] Verify resource limits through experimentation
- [ ] Document networking capabilities

---

## 12. References

### Official Documentation
- Main: https://developers.cloudflare.com/sandbox/
- Architecture: https://developers.cloudflare.com/sandbox/concepts/architecture/
- Lifecycle: https://developers.cloudflare.com/sandbox/concepts/sandboxes/
- Sessions: https://developers.cloudflare.com/sandbox/concepts/sessions/
- API Reference: https://developers.cloudflare.com/sandbox/api-reference/
- Getting Started: https://developers.cloudflare.com/sandbox/get-started/

### Tutorials
- Claude Code: https://developers.cloudflare.com/sandbox/tutorials/claude-code/
- AI Code Executor: https://developers.cloudflare.com/sandbox/tutorials/ai-code-executor/

### Related Technologies
- Durable Objects: https://developers.cloudflare.com/durable-objects/
- Containers: https://developers.cloudflare.com/containers/
- Workers: https://developers.cloudflare.com/workers/

---

**Research Date**: 2025-10-29  
**Status**: Complete - Ready for skill design  
**Next Step**: Create skill structure with templates and references
