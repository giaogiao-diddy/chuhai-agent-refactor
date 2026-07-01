// 测试 setAuthToken/getAuthToken/clearAuthToken + OAuth state 流程

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

  // ── OAuth state 流程 ──

  // 4. getWechatLoginUrl 保存 state
  (globalThis as any).fetch = async (url: string) => ({
    ok: true,
    json: async () => ({ url: "https://open.weixin.qq.com/connect/qrconnect?appid=wx&state=test-oauth-state-456#wechat_redirect", state: "test-oauth-state-456" }),
  });

  const loginData = await mod.getWechatLoginUrl();
  assert(typeof loginData.url === "string", "getWechatLoginUrl 返回 url");
  assert(typeof loginData.state === "string", "getWechatLoginUrl 返回 state");
  assert(store.get("oauth_state") === "test-oauth-state-456", "getWechatLoginUrl 将 state 保存到 sessionStorage");

  // 5. handleWechatCallback state 一致时调后端 callback 且成功后清除 state
  let capturedUrl = "";
  (globalThis as any).fetch = async (url: string) => {
    capturedUrl = url.toString();
    return { ok: true, json: async () => ({ access_token: "mock-jwt", token_type: "bearer", user: { id: "1", nickname: "test", role: "user" } }) };
  };

  const cb = await mod.handleWechatCallback("auth-code-123", "test-oauth-state-456");
  assert(capturedUrl.includes("code=auth-code-123"), "handleWechatCallback URL 包含 code");
  assert(capturedUrl.includes("state=test-oauth-state-456"), "handleWechatCallback URL 包含 state");
  assert(cb.access_token === "mock-jwt", "handleWechatCallback 返回 token");
  assert(store.get("auth_token") === "mock-jwt", "handleWechatCallback 成功后保存 token");
  assert(store.get("oauth_state") === null || store.get("oauth_state") === undefined, "handleWechatCallback 成功后清除 oauth_state");

  // 6. handleWechatCallback state 不一致时抛安全错误（不调后端）
  // 重新保存一个不同的 state
  store.set("oauth_state", "expected-state");
  let fetchWasCalled = false;
  (globalThis as any).fetch = async () => { fetchWasCalled = true; return { ok: true, json: async () => ({}) }; };
  try {
    await mod.handleWechatCallback("code", "wrong-state");
    assert(false, "handleWechatCallback state 不一致应抛错");
  } catch (e: any) {
    assert(e.message === "安全校验失败，请重新登录", "state 不一致抛固定安全文案");
  }
  assert(!fetchWasCalled, "state 不一致时不调用后端");

  // 7. handleWechatCallback 没有保存 state 时抛安全错误
  store.delete("oauth_state");
  try {
    await mod.handleWechatCallback("code", "any-state");
    assert(false, "handleWechatCallback 无保存 state 应抛错");
  } catch (e: any) {
    assert(e.message === "安全校验失败，请重新登录", "无保存 state 时抛固定安全文案");
  }

  // 8. handleWechatCallback 后端失败不泄露原始错误（且不清除 oauth_state）
  store.set("oauth_state", "state-match");
  (globalThis as any).fetch = async () => ({ ok: false, status: 400 });
  try {
    await mod.handleWechatCallback("code", "state-match");
    assert(false, "handleWechatCallback 失败应抛错");
  } catch (e: any) {
    assert(e.message === "微信登录失败", "handleWechatCallback 失败抛固定文案");
    assert(!e.message.includes("400"), "失败不泄露状态码");
  }
  // 后端失败时不清除 oauth_state（用户可刷新 callback 页重试）
  assert(store.get("oauth_state") === "state-match", "后端失败时保留 oauth_state 用于重试");

  console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

run();
