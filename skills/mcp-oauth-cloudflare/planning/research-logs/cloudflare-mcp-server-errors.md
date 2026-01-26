# Cloudflare MCP Server - Known Errors

**Research Date**: 2025-11-04
**SDK Version**: @modelcontextprotocol/sdk@1.21.0
**OAuth Provider**: @cloudflare/workers-oauth-provider@0.0.13
**Agents SDK**: agents@0.2.20

---

## 15 Known Errors with Solutions

### 1. **McpAgent Class Not Exported**

**Error**:
```
TypeError: Cannot read properties of undefined (reading 'serve')
```

**Cause**: Forgot to export McpAgent class from Worker

**Solution**:
```typescript
export class MyMCP extends McpAgent { ... }
export default { fetch(request, env, ctx) { ... } }
```

**Source**: Common mistake in Cloudflare Workers + MCP setup

---

### 2. **Transport Mismatch**

**Error**:
```
Connection failed: Unexpected response format
```

**Cause**: Client expects SSE (`/sse`) but server only serves `/mcp`, or vice versa

**Solution**: Serve both transports
```typescript
if (pathname.startsWith('/sse')) return MyMCP.serveSSE('/sse').fetch(request, env, ctx);
if (pathname.startsWith('/mcp')) return MyMCP.serve('/mcp').fetch(request, env, ctx);
```

**Source**: https://developers.cloudflare.com/agents/model-context-protocol/transport/

---

### 3. **OAuth Redirect URI Mismatch**

**Error**:
```
OAuth error: redirect_uri does not match
```

**Cause**: Client configured with `http://localhost:8788` but deployed to `https://my-mcp.workers.dev`

**Solution**: Update client configuration after deployment, or use environment-aware URLs

**Source**: https://developers.cloudflare.com/agents/model-context-protocol/authorization/

---

### 4. **WebSocket Hibernation State Loss**

**Error**: Tool calls fail after WebSocket reconnect with "state not found"

**Cause**: In-memory state cleared when hibernation wakes up

**Solution**: Use Durable Objects `storage` API instead of instance properties
```typescript
await this.state.storage.put('key', value);
const value = await this.state.storage.get('key');
```

**Source**: https://developers.cloudflare.com/durable-objects/api/websockets/#websocket-hibernation-api

---

### 5. **Durable Objects Binding Missing**

**Error**:
```
Error: Cannot read properties of undefined (reading 'idFromName')
```

**Cause**: Forgot to add DO binding in `wrangler.jsonc`

**Solution**:
```jsonc
{
  "durable_objects": {
    "bindings": [
      { "name": "MY_MCP", "class_name": "MyMCP", "script_name": "cloudflare-mcp-server" }
    ]
  }
}
```

**Source**: https://developers.cloudflare.com/durable-objects/get-started/

---

### 6. **Migration Not Defined**

**Error**:
```
Error: Durable Object class MyMCP has no migration defined
```

**Cause**: First deployment of DO requires migration configuration

**Solution**:
```jsonc
{
  "migrations": [
    { "tag": "v1", "new_classes": ["MyMCP"] }
  ]
}
```

**Source**: https://developers.cloudflare.com/durable-objects/reference/durable-objects-migrations/

---

### 7. **CORS Errors on Remote MCP**

**Error**:
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Cause**: MCP server doesn't return CORS headers

**Solution**: Add CORS headers to responses (or use OAuthProvider which handles this)
```typescript
return new Response(body, {
  headers: {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  }
});
```

**Source**: Standard CORS requirements for remote servers

---

### 8. **Client Configuration Format Error**

**Error**: Claude Desktop doesn't recognize MCP server

**Cause**: Wrong JSON format in `claude_desktop_config.json`

**Solution**:
```json
{
  "mcpServers": {
    "my-mcp": {
      "url": "https://my-mcp.workers.dev/sse"
    }
  }
}
```

**Source**: https://modelcontextprotocol.io/quickstart/user

---

### 9. **serializeAttachment() Not Used**

**Error**: WebSocket metadata lost on hibernation wake

**Cause**: Not using `serializeAttachment()` to preserve WebSocket metadata

**Solution**:
```typescript
webSocket.serializeAttachment({ userId: '123', sessionId: 'abc' });
```

**Source**: https://developers.cloudflare.com/durable-objects/api/websockets/#websocket-hibernation-api

---

### 10. **OAuth Consent Screen Disabled**

**Security Risk**: Users don't see what permissions they're granting

**Cause**: `allowConsentScreen: false` in production

**Solution**:
```typescript
new OAuthProvider({
  allowConsentScreen: true, // Required for production
  // ...
})
```

**Source**: Security best practice from workers-oauth-provider

---

### 11. **JWT Signing Key Missing**

**Error**:
```
Error: JWT_SIGNING_KEY environment variable not set
```

**Cause**: OAuth Provider requires signing key for tokens

**Solution**:
```bash
# Generate key
openssl rand -base64 32

# Add to wrangler.jsonc
"vars": {
  "JWT_SIGNING_KEY": "your-generated-key-here"
}
```

**Source**: @cloudflare/workers-oauth-provider documentation

---

### 12. **Environment Variables Not Configured**

**Error**: `env.MY_VAR is undefined`

**Cause**: Variables defined in `.dev.vars` but not in `wrangler.jsonc`

**Solution**:
```jsonc
{
  "vars": {
    "MY_VAR": "production-value"
  }
}
```

**Source**: https://developers.cloudflare.com/workers/configuration/environment-variables/

---

### 13. **Tool Schema Validation Error**

**Error**:
```
ZodError: Invalid input type
```

**Cause**: Client sends string, but Zod schema expects number

**Solution**: Use Zod transforms or coerce
```typescript
z.object({
  count: z.string().transform(val => parseInt(val, 10))
})
```

**Source**: Common Zod validation issue

---

### 14. **Multiple Transport Endpoints Conflicting**

**Error**: `/sse` returns 404 after adding `/mcp` endpoint

**Cause**: Incorrect path matching in fetch handler

**Solution**: Use `startsWith()` or exact matches
```typescript
if (pathname === '/sse' || pathname.startsWith('/sse/')) {
  return MyMCP.serveSSE('/sse').fetch(request, env, ctx);
}
```

**Source**: Worker routing logic

---

### 15. **Local Testing with Miniflare Limitations**

**Error**: OAuth flow fails in local development

**Cause**: Miniflare doesn't support all DO features, especially hibernation

**Solution**:
- Test OAuth on deployed Worker
- Use `npx wrangler dev --remote` for full DO support
- Mock OAuth for local testing

**Source**: https://developers.cloudflare.com/workers/testing/local-development-and-testing/

---

## Additional Common Issues

### Init() Not Called

**Error**: Tools not registered

**Cause**: Forgot to call `await this.init()` in constructor or `init()` method not defined

**Solution**: Ensure `init()` is properly invoked by McpAgent base class

---

### Token Expiry Not Handled

**Error**: API calls fail with 401 after token expires

**Cause**: `accessToken` from OAuth props expired, no refresh logic

**Solution**: Implement token refresh in OAuth handler or tool logic

---

### Rate Limiting Not Implemented

**Error**: Upstream API returns 429 Too Many Requests

**Cause**: No rate limiting on MCP server tools

**Solution**: Use Durable Objects Alarms or implement token bucket pattern

---

## Token Savings Analysis

**Without skill** (manual setup, encountering all errors):
- 15 errors × ~2k tokens per error debug = ~30k tokens
- Initial setup research: ~10k tokens
- **Total: ~40k tokens**

**With skill** (instant error prevention):
- Read skill: ~4k tokens
- Copy templates: ~1k tokens
- **Total: ~5k tokens**

**Savings: ~87.5%** (40k → 5k tokens)

---

## Version Information

- @modelcontextprotocol/sdk: 1.21.0
- @cloudflare/workers-oauth-provider: 0.0.13
- agents (Cloudflare Agents SDK): 0.2.20

**Last Verified**: 2025-11-04
