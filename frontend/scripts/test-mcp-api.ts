const store = new Map<string, string>();
(globalThis as any).window = {};
(globalThis as any).sessionStorage = {
  getItem(k: string) { return store.get(k) ?? null; },
  setItem(k: string, v: string) { store.set(k, v); },
  removeItem(k: string) { store.delete(k); },
};

let passed = 0;
let failed = 0;

function assert(condition: boolean, name: string) {
  if (condition) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ FAIL: ${name}`); }
}

async function run() {
  console.log("MCP API 测试:");
  const mod = await import("../lib/api");
  mod.setAuthToken("test-jwt-token");

  const mockServer = {
    id: "mcp1",
    name: "Tariff",
    transport: "http",
    url: "https://mcp.example.com",
    command: null,
    enabled: true,
    tools_count: 2,
    connected: true,
    error_message: null,
    created_at: "2026-01-01",
  };

  let capturedHeaders: any = {};
  (globalThis as any).fetch = async (_url: string, init: any) => {
    capturedHeaders = init?.headers || {};
    return { ok: true, status: 200, json: async () => [mockServer] };
  };
  const list = await mod.listMcpServers();
  assert(list[0].id === "mcp1", "listMcpServers 返回数据");
  assert(capturedHeaders.Authorization === "Bearer test-jwt-token", "listMcpServers 带 Authorization");

  let method = "";
  let body = "";
  (globalThis as any).fetch = async (_url: string, init: any) => {
    method = init?.method || "GET";
    body = init?.body || "";
    return { ok: true, status: 201, json: async () => mockServer };
  };
  await mod.createMcpServer({ name: "Tariff", transport: "http", url: "https://mcp.example.com" });
  assert(method === "POST", "createMcpServer method POST");
  assert(body.includes("\"transport\":\"http\""), "createMcpServer body 含 http transport");

  (globalThis as any).fetch = async (_url: string, init: any) => {
    method = init?.method || "GET";
    body = init?.body || "";
    return { ok: true, status: 200, json: async () => ({ ...mockServer, enabled: false }) };
  };
  await mod.updateMcpServer("mcp1", { enabled: false });
  assert(method === "PATCH", "updateMcpServer method PATCH");
  assert(body.includes("\"enabled\":false"), "updateMcpServer body 含 enabled=false");

  let testUrl = "";
  (globalThis as any).fetch = async (url: string, init: any) => {
    testUrl = url.toString();
    method = init?.method || "GET";
    return { ok: true, status: 200, json: async () => mockServer };
  };
  const tested = await mod.testMcpServer("mcp1");
  assert(method === "POST", "testMcpServer method POST");
  assert(testUrl.endsWith("/mcp-servers/mcp1/test"), "testMcpServer URL 正确");
  assert(tested.tools_count === 2, "testMcpServer 返回 tools_count");

  (globalThis as any).fetch = async () => ({ ok: false, status: 401 });
  try { await mod.listMcpServers(); assert(false, "401 should throw"); } catch (e: any) { assert(e.message === "请先登录", "401→请先登录"); }

  (globalThis as any).fetch = async () => ({ ok: false, status: 403 });
  try { await mod.listMcpServers(); assert(false, "403 should throw"); } catch (e: any) { assert(e.message === "无权访问 MCP 设置", "403→无权访问 MCP 设置"); }

  (globalThis as any).fetch = async () => ({ ok: false, status: 422 });
  try { await mod.createMcpServer({ name: "", transport: "http" }); assert(false, "422 should throw"); } catch (e: any) { assert(e.message === "请检查 MCP 配置", "422→请检查 MCP 配置"); }

  console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

run();
