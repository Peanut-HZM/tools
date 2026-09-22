/**
 * 代码片段生成器 - 将 HTTP 请求转换为各语言代码
 *
 * 支持：cURL / Fetch(JavaScript) / Python(httpx) / Go / 原始 HTTP 报文
 * 适配 list 格式的 headers/params（含启用/禁用），发送时认证注入
 */

import { HttpRequest, KeyValueItem } from '../services/httpClientApi';

export type Language = 'curl' | 'javascript' | 'python' | 'go' | 'http';

function resolveVariables(text: string, variables: Record<string, string>): string {
  if (!text) return text;
  return text.replace(/\{\{(.+?)\}\}/g, (_, name) => variables[name.trim()] || `{{${name}}}`);
}

function escapeShell(str: string): string {
  return str.replace(/'/g, "'\\''");
}

/** 获取启用的 headers（含自动 Content-Type 与认证注入后的等效头） */
function effectiveHeaders(request: HttpRequest, variables: Record<string, string>): { key: string; value: string }[] {
  const headers: { key: string; value: string }[] = [];
  const seen = new Set<string>();
  for (const item of (request.headers || []) as KeyValueItem[]) {
    if (!item.enabled || !item.key.trim()) continue;
    const key = resolveVariables(item.key.trim(), variables);
    headers.push({ key, value: resolveVariables(item.value, variables) });
    seen.add(key.toLowerCase());
  }
  // Content-Type 按需补齐
  if (request.body_type === 'json' && !seen.has('content-type')) {
    headers.push({ key: 'Content-Type', value: 'application/json' });
  } else if (request.body_type === 'xml' && !seen.has('content-type')) {
    headers.push({ key: 'Content-Type', value: 'application/xml' });
  } else if (request.body_type === 'form' && !seen.has('content-type')) {
    headers.push({ key: 'Content-Type', value: 'application/x-www-form-urlencoded' });
  }
  // 认证注入（basic 用 -u 表示，不在头中体现）
  if (request.auth_type === 'bearer' && request.auth_config?.token && !seen.has('authorization')) {
    headers.push({ key: 'Authorization', value: `Bearer ${resolveVariables(String(request.auth_config.token), variables)}` });
  } else if (request.auth_type === 'apikey' && request.auth_config?.key && (request.auth_config?.in || 'header') === 'header') {
    const key = String(request.auth_config.key);
    if (key && !seen.has(key.toLowerCase())) {
      headers.push({ key, value: resolveVariables(String(request.auth_config.value || ''), variables) });
    }
  }
  return headers;
}

/** 组装完整 URL（含启用的 query 参数） */
function effectiveUrl(request: HttpRequest, variables: Record<string, string>): string {
  const base = resolveVariables(request.url, variables);
  const enabledParams = (request.params || []).filter(p => p.enabled && p.key.trim());
  if (enabledParams.length === 0) return base;
  const qs = enabledParams.map(p => `${resolveVariables(p.key, variables)}=${resolveVariables(p.value, variables)}`).join('&');
  return base.includes('?') ? `${base}&${qs}` : `${base}?${qs}`;
}

/** 请求体文本（json/xml/raw/form/graphql） */
function effectiveBody(request: HttpRequest, variables: Record<string, string>): string | null {
  if (request.body_type === 'none' || request.body_type === 'form-data' || request.body_type === 'binary') return null;
  if (!request.body) return null;
  return resolveVariables(request.body, variables);
}

export function generateCurl(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(effectiveUrl(request, variables), variables);
  let cmd = `curl -X ${request.method} '${escapeShell(url)}'`;

  // Basic 认证用 -u 表示
  if (request.auth_type === 'basic' && request.auth_config?.username) {
    const user = resolveVariables(String(request.auth_config.username), variables);
    const pass = resolveVariables(String(request.auth_config.password || ''), variables);
    cmd += ` \\\n  -u '${escapeShell(`${user}:${pass}`)}'`;
  }

  for (const h of effectiveHeaders(request, variables)) {
    cmd += ` \\\n  -H '${escapeShell(`${h.key}: ${h.value}`)}'`;
  }

  const body = effectiveBody(request, variables);
  if (body) {
    cmd += ` \\\n  -d '${escapeShell(body)}'`;
  }
  return cmd;
}

export function generateJavaScript(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(effectiveUrl(request, variables), variables);
  const headers = effectiveHeaders(request, variables);
  const body = effectiveBody(request, variables);

  let code = '';
  if (headers.length > 0 || body) {
    code += `const options = {\n`;
    code += `  method: '${request.method}',\n`;
    if (headers.length > 0) {
      code += `  headers: {\n`;
      for (const h of headers) {
        code += `    '${h.key}': '${h.value}',\n`;
      }
      code += `  },\n`;
    }
    if (body) {
      code += `  body: ${JSON.stringify(body)},\n`;
    }
    code += `};\n\n`;
    code += `fetch('${url}', options)\n`;
  } else {
    code += `fetch('${url}', { method: '${request.method}' })\n`;
  }
  code += `  .then(res => res.text())\n`;
  code += `  .then(data => console.log(data))\n`;
  code += `  .catch(err => console.error(err));`;
  return code;
}

export function generatePython(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(effectiveUrl(request, variables), variables);
  const headers = effectiveHeaders(request, variables);
  const body = effectiveBody(request, variables);

  let code = `import httpx\n\n`;
  code += `url = "${url}"\n`;

  if (headers.length > 0) {
    code += `headers = {\n`;
    for (const h of headers) {
      code += `    "${h.key}": "${h.value}",\n`;
    }
    code += `}\n`;
  }

  let payloadArg = '';
  if (body && request.body_type === 'json') {
    try {
      const pretty = JSON.stringify(JSON.parse(body), null, 4);
      code += `payload = ${pretty}\n`;
      payloadArg = '    json=payload,\n';
    } catch {
      code += `payload = """${body}"""\n`;
      payloadArg = '    content=payload,\n';
    }
  } else if (body) {
    code += `payload = """${body}"""\n`;
    payloadArg = '    content=payload,\n';
  }

  const method = request.method.toLowerCase();
  code += `\nresponse = httpx.${method}(\n    url,\n`;
  if (headers.length > 0) code += `    headers=headers,\n`;
  if (payloadArg) code += payloadArg;
  code += `)\n\nprint(response.status_code)\nprint(response.text)`;
  return code;
}

export function generateGo(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(effectiveUrl(request, variables), variables);
  const headers = effectiveHeaders(request, variables);
  const body = effectiveBody(request, variables);

  let code = `package main\n\n`;
  code += `import (\n`;
  code += `    "fmt"\n`;
  code += `    "io"\n`;
  code += `    "net/http"\n`;
  code += `    "strings"\n`;
  code += `)\n\n`;
  code += `func main() {\n`;
  code += `    url := "${url}"\n`;

  if (body) {
    code += `    payload := strings.NewReader(\`${body}\`)\n\n`;
    code += `    req, _ := http.NewRequest("${request.method}", url, payload)\n`;
  } else {
    code += `\n    req, _ := http.NewRequest("${request.method}", url, nil)\n`;
  }

  for (const h of headers) {
    code += `    req.Header.Add("${h.key}", "${h.value}")\n`;
  }

  code += `\n    res, _ := http.DefaultClient.Do(req)\n`;
  code += `    defer res.Body.Close()\n`;
  code += `    responseBody, _ := io.ReadAll(res.Body)\n\n`;
  code += `    fmt.Println(res.StatusCode)\n`;
  code += `    fmt.Println(string(responseBody))\n`;
  code += `}`;
  return code;
}

export function generateHttp(request: HttpRequest, variables: Record<string, string> = {}): string {
  const headers = effectiveHeaders(request, variables);
  const body = effectiveBody(request, variables);
  let code = `${request.method} ${resolveVariables(effectiveUrl(request, variables), variables)} HTTP/1.1\n`;
  for (const h of headers) {
    code += `${h.key}: ${h.value}\n`;
  }
  if (body) {
    code += `Content-Length: ${new TextEncoder().encode(body).length}\n\n`;
    code += body;
  }
  return code;
}

export function generateSnippet(request: HttpRequest, language: Language, variables: Record<string, string> = {}): string {
  switch (language) {
    case 'curl': return generateCurl(request, variables);
    case 'javascript': return generateJavaScript(request, variables);
    case 'python': return generatePython(request, variables);
    case 'go': return generateGo(request, variables);
    case 'http': return generateHttp(request, variables);
    default: return generateCurl(request, variables);
  }
}
