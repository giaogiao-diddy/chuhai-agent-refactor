// 测试 setAuthToken/getAuthToken/clearAuthToken（模拟 sessionStorage）

let passed = 0;
let failed = 0;

function assert(condition: boolean, name: string) {
  if (condition) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ FAIL: ${name}`); }
}

async function run() {
  console.log("Auth API 测试:");

  // 模拟 sessionStorage + window（Node 环境 window 不存在）
  const store = new Map<string, string>();
  (globalThis as any).window = {}; // typeof window !== "undefined" 通道
  (globalThis as any).sessionStorage = {
    getItem(k: string) { return store.get(k) ?? null; },
    setItem(k: string, v: string) { store.set(k, v); },
    removeItem(k: string) { store.delete(k); },
  };

  const mod = await import("../lib/api");

  // 1. 初始无 token
  assert(mod.getAuthToken() === "", "初始 getAuthToken 返回空");
  assert(mod.isLoggedIn() === false, "初始 isLoggedIn 为 false");

  // 2. setAuthToken 后读写
  mod.setAuthToken("test-jwt-token-123");
  assert(mod.getAuthToken() === "test-jwt-token-123", "setAuthToken 后可读取");
  assert(mod.isLoggedIn() === true, "setAuthToken 后 isLoggedIn 为 true");

  // 3. clearAuthToken 后清除
  mod.clearAuthToken();
  assert(mod.getAuthToken() === "", "clearAuthToken 后返回空");
  assert(mod.isLoggedIn() === false, "clearAuthToken 后 isLoggedIn 为 false");

  // 4. handleWechatCallback URL 拼接
  const originalFetch = (globalThis as any).fetch;
  let capturedUrl = "";
  (globalThis as any).fetch = async (url: string) => {
    capturedUrl = url.toString();
    return { ok: true, json: async () => ({ access_token: "mock-jwt", token_type: "bearer", user: { id: "1", nickname: "test", role: "user" } }) };
  };

  const cb = await mod.handleWechatCallback("auth-code-123", "state-456");
  assert(capturedUrl.includes("code=auth-code-123"), "handleWechatCallback URL 包含 code");
  assert(capturedUrl.includes("state=state-456"), "handleWechatCallback URL 包含 state");
  assert(cb.access_token === "mock-jwt", "handleWechatCallback 返回 token");

  // 5. handleWechatCallback 失败不泄露原始错误
  (globalThis as any).fetch = async () => ({ ok: false, status: 400 });
  try {
    await mod.handleWechatCallback("code", "state");
    assert(false, "handleWechatCallback 失败应抛错");
  } catch (e: any) {
    assert(e.message === "微信登录失败", "handleWechatCallback 失败抛固定文案");
    assert(!e.message.includes("400"), "失败不泄露状态码");
  }

  (globalThis as any).fetch = originalFetch;

  console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

run();
