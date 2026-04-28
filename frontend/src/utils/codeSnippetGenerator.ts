/**
 * 代码片段生成器 - 将 HTTP 请求转换为各语言代码
 */

import { HttpRequest } from '../services/httpClientApi';

type Language = 'curl' | 'python' | 'javascript' | 'go';

function resolveVariables(text: string, variables: Record<string, string>): string {
  if (!text) return text;
  return text.replace(/\{\{(.+?)\}\}/g, (_, name) => variables[name.trim()] || `{{${name}}}`);
}

function escapeShell(str: string): string {
  return str.replace(/'/g, "'\\''");
}

export function generateCurl(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(request.url, variables);
  let cmd = `curl -X ${request.method} '${escapeShell(url)}'`;

  // Headers
  const headers = { ...request.headers };
  if (request.body_type === 'json') {
    headers['Content-Type'] = 'application/json';
  }
  for (const [key, value] of Object.entries(headers)) {
    if (key && value) {
      cmd += ` \\\n  -H '${escapeShell(`${key}: ${resolveVariables(value, variables)}`)}'`;
    }
  }

  // Body
  if (request.body && request.body_type !== 'none') {
    cmd += ` \\\n  -d '${escapeShell(resolveVariables(request.body, variables))}'`;
  }

  return cmd;
}

export function generatePython(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(request.url, variables);
  let code = `import httpx\n\n`;
  code += `url = "${url}"\n`;

  // Headers
  const headers = { ...request.headers };
  if (request.body_type === 'json') {
    headers['Content-Type'] = 'application/json';
  }
  const headerEntries = Object.entries(headers).filter(([k, v]) => k && v);
  if (headerEntries.length > 0) {
    code += `headers = {\n`;
    for (const [key, value] of headerEntries) {
      code += `    "${key}": "${resolveVariables(value, variables)}",\n`;
    }
    code += `}\n`;
  }

  // Body
  if (request.body && request.body_type === 'json') {
    try {
      const parsed = JSON.parse(resolveVariables(request.body, variables));
      code += `payload = ${JSON.stringify(parsed, null, 4).replace(/"([^"]+)":/g, '$1:').replace(/"/g, '"')}\n`;
    } catch {
      code += `payload = """${resolveVariables(request.body, variables)}"""\n`;
    }
  }

  // Request
  const method = request.method.toLowerCase();
  code += `\nresponse = httpx.${method}(\n    url,\n`;
  if (headerEntries.length > 0) code += `    headers=headers,\n`;
  if (request.body && request.body_type === 'json') code += `    json=payload,\n`;
  else if (request.body && request.body_type !== 'none') code += `    content=payload,\n`;
  code += `)\n\nprint(response.status_code)\nprint(response.text)`;

  return code;
}

export function generateJavaScript(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(request.url, variables);
  let code = `const url = "${url}";\n`;
  code += `const options = {\n`;
  code += `  method: "${request.method}",\n`;

  // Headers
  const headers = { ...request.headers };
  if (request.body_type === 'json') {
    headers['Content-Type'] = 'application/json';
  }
  const headerEntries = Object.entries(headers).filter(([k, v]) => k && v);
  if (headerEntries.length > 0) {
    code += `  headers: {\n`;
    for (const [key, value] of headerEntries) {
      code += `    "${key}": "${resolveVariables(value, variables)}",\n`;
    }
    code += `  },\n`;
  }

  // Body
  if (request.body && request.body_type === 'json') {
    const resolvedBody = resolveVariables(request.body, variables);
    code += `  body: JSON.stringify(${resolvedBody}),\n`;
  } else if (request.body && request.body_type !== 'none') {
    code += `  body: \`${resolveVariables(request.body, variables)}\`,\n`;
  }

  code += `};\n\n`;
  code += `fetch(url, options)\n`;
  code += `  .then(res => res.text())\n`;
  code += `  .then(data => console.log(data))\n`;
  code += `  .catch(err => console.error(err));`;

  return code;
}

export function generateGo(request: HttpRequest, variables: Record<string, string> = {}): string {
  const url = resolveVariables(request.url, variables);
  let code = `package main\n\n`;
  code += `import (\n`;
  code += `    "fmt"\n`;
  code += `    "io"\n`;
  code += `    "net/http"\n`;
  code += `    "strings"\n`;
  code += `)\n\n`;
  code += `func main() {\n`;
  code += `    url := "${url}"\n`;

  if (request.body && request.body_type !== 'none') {
    code += `    payload := strings.NewReader(\`${resolveVariables(request.body, variables)}\`)\n\n`;
    code += `    req, _ := http.NewRequest("${request.method}", url, payload)\n`;
  } else {
    code += `\n    req, _ := http.NewRequest("${request.method}", url, nil)\n`;
  }

  // Headers
  const headers = { ...request.headers };
  if (request.body_type === 'json') {
    headers['Content-Type'] = 'application/json';
  }
  for (const [key, value] of Object.entries(headers)) {
    if (key && value) {
      code += `    req.Header.Add("${key}", "${resolveVariables(value, variables)}")\n`;
    }
  }

  code += `\n    res, _ := http.DefaultClient.Do(req)\n`;
  code += `    defer res.Body.Close()\n`;
  code += `    body, _ := io.ReadAll(res.Body)\n\n`;
  code += `    fmt.Println(res.StatusCode)\n`;
  code += `    fmt.Println(string(body))\n`;
  code += `}`;

  return code;
}

export function generateSnippet(request: HttpRequest, language: Language, variables: Record<string, string> = {}): string {
  switch (language) {
    case 'curl': return generateCurl(request, variables);
    case 'python': return generatePython(request, variables);
    case 'javascript': return generateJavaScript(request, variables);
    case 'go': return generateGo(request, variables);
    default: return generateCurl(request, variables);
  }
}
