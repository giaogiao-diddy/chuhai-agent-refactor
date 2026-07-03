// Provider API + model selection 契约测试

const store = new Map<string, string>();
(globalThis as any).window = {};
(globalThis as any).sessionStorage = {
  getItem(k: string) { return store.get(k) ?? null; },
  setItem(k: string, v: string) { store.set(k, v); },
  removeItem(k: string) { store.delete(k); },
};

let passed = 0; let failed = 0;
function assert(condition: boolean, name: string) {
  if (condition) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ FAIL: ${name}`); }
}

// track HTTP method
let lastMethod = "";

const mockProvider = { id: "p1", name: "DeepSeek", provider_type: "openai_compatible", base_url: "https://api.ds.com", masked_key: "sk-...abcd", default_model: "m1", enabled: true, context_window: 128000, created_at: "2026-01-01", updated_at: "2026-01-01" };

function mockFetch(ok: boolean, status: number, data?: any) {
  (globalThis as any).fetch = async (_url: string, init: any) => {
    lastMethod = init?.method || "GET";
    return { ok, status, json: async () => data, headers: new Map() };
  };
}

async function run() {
  console.log("Provider API 测试:");
  const mod = await import("../lib/api");
  mod.setAuthToken("test-jwt");

  // 1. listModelProviders Authorization
  mockFetch(true, 200, [mockProvider]);
  const list = await mod.listModelProviders();
  assert(list[0].id === "p1", "listModelProviders 返回数据");

  // 2. createModelProvider
  let body1 = "";
  (globalThis as any).fetch = async (_url: string, init: any) => {
    lastMethod = init?.method || "GET";
    body1 = init?.body || "";
    return { ok: true, status: 201, json: async () => mockProvider, headers: new Map() };
  };
  await mod.createModelProvider({ name: "t", base_url: "https://x.com", api_key: "sk-123", default_model: "m" });
  assert(lastMethod === "POST", "createModelProvider method POST");
  assert(body1.includes("sk-123"), "createModelProvider body 含 api_key");

  // 3. updateModelProvider
  mockFetch(true, 200, mockProvider);
  await mod.updateModelProvider("p1", { default_model: "v2" });
  assert(lastMethod === "PATCH", "updateModelProvider method PATCH");

  // 4. deleteModelProvider
  mockFetch(true, 200);
  await mod.deleteModelProvider("p1");
  assert(lastMethod === "DELETE", "deleteModelProvider method DELETE");

  // 5. testModelProvider
  mockFetch(true, 200, { success: true, message: "ok" });
  const tr = await mod.testModelProvider("p1");
  assert(tr.success === true, "testModelProvider 返回 success");

  // 6. 401
  mockFetch(false, 401);
  try { await mod.listModelProviders(); } catch (e: any) { assert(e.message === "请先登录", "401→请先登录"); }

  // 7. 403
  mockFetch(false, 403);
  try { await mod.listModelProviders(); } catch (e: any) { assert(e.message === "无权访问模型设置", "403→无权访问模型设置"); }

  // 8. public provider list
  const mockPublic = [{ id: "p2", name: "OpenAI", default_model: "gpt-4", context_window: 128000 }];
  let pubNoAuth = true;
  (globalThis as any).fetch = async (_url: string, init: any) => {
    if (init?.headers?.Authorization) pubNoAuth = false;
    return { ok: true, status: 200, json: async () => mockPublic, headers: new Map() };
  };
  const pubList = await mod.listPublicModelProviders();
  assert(pubList[0].id === "p2", "listPublicModelProviders 返回数据");
  assert(!("api_key" in (pubList[0] as any)), "public list 不含 api_key");
  assert(pubNoAuth, "public list 不带 Authorization");

  // 9. public provider list 500
  mockFetch(false, 500);
  try { await mod.listPublicModelProviders(); } catch (e: any) { assert(e.message === "服务器错误", "public 500→服务器错误"); }

  // 10. startConversation 默认 body
  let startBody: any = {};
  (globalThis as any).fetch = async (_url: string, init: any) => {
    startBody = JSON.parse(init?.body || "{}");
    return { ok: true, status: 200, json: async () => ({
      state: { messages: [], slots: {}, answers: {}, branch: null, status: "active", conversation_round: 0, ai_failure_count: 0, validation_errors: [], used_template_report: false, public_error: null, provider_id: "p-lock", model_name: "m-lock", readiness: null },
      assistant_message: "hi", provider_id: "p-lock", model_name: "m-lock",
    })};
  };
  const r1 = await mod.startConversation();
  assert(startBody.provider_id === undefined, "startConversation default 不含 provider_id");
  assert(r1.provider_id === "p-lock", "startConversation 返回 provider_id");
  assert(r1.state.provider_id === "p-lock", "state 保留 provider_id");

  // 11. startConversation 带 provider_id
  const r2 = await mod.startConversation({ provider_id: "p-custom", model_name: "custom-m" });
  assert(startBody.provider_id === "p-custom", "startConversation body 含 provider_id");

  // 12. startConversation 400
  mockFetch(false, 400, { detail: "请先配置可用模型" });
  try { await mod.startConversation(); } catch (e: any) { assert(e.message === "请先配置可用模型", "startConversation 400→提示配置模型"); }

  console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}
run();
