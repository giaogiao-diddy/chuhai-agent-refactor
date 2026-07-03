// 报告解锁 + RAG 匹配 API 契约测试

const store = new Map<string, string>();
(globalThis as any).window = {};
(globalThis as any).sessionStorage = {
  getItem(k: string) { return store.get(k) ?? null; },
  setItem(k: string, v: string) { store.set(k, v); },
  removeItem(k: string) { store.delete(k); },
};
(globalThis as any).localStorage = {
  getItem(k: string) { return store.get(k) ?? null; },
  setItem(k: string, v: string) { store.set(k, v); },
  removeItem(k: string) { store.delete(k); },
};

let passed = 0; let failed = 0;
function assert(condition: boolean, name: string) {
  if (condition) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ FAIL: ${name}`); }
}

function mockFetch(ok: boolean, status: number, data?: any) {
  (globalThis as any).fetch = async (_url: string, init: any) => {
    const body = data ? { ...data } : {};
    return { ok, status, json: async () => body, headers: new Map() };
  };
}

async function run() {
  console.log("Report Unlock 测试:");
  const mod = await import("../lib/api");
  mod.setAuthToken("test-jwt");
  store.set("anonymous_user_id", "anon-test-123");

  // 1. submitLead Authorization
  let capturedHeaders: any = {};
  (globalThis as any).fetch = async (_url: string, init: any) => {
    capturedHeaders = init?.headers || {};
    return { ok: true, status: 200, json: async () => ({ submission_id: "s1", assessment_id: "a1", submitted: true, created_at: "" }), headers: new Map() };
  };
  await mod.submitLead("a1", { contact_name: "张三", phone: "13800138000" });
  assert(capturedHeaders.Authorization === "Bearer test-jwt", "submitLead 带 Authorization");

  // 2. submitLead body 含 anonymous_user_id
  let submitBody: any = {};
  (globalThis as any).fetch = async (_url: string, init: any) => {
    submitBody = JSON.parse(init?.body || "{}");
    return { ok: true, status: 200, json: async () => ({ submission_id: "s1", assessment_id: "a1", submitted: true, created_at: "" })};
  };
  await mod.submitLead("a1", { contact_name: "李四", phone: "13900139000" });
  assert(submitBody.anonymous_user_id === "anon-test-123", "submitLead body 含 anonymous_user_id");

  // 3. submitLead 400/422
  mockFetch(false, 400);
  try { await mod.submitLead("a1", { contact_name: "", phone: "" }); } catch (e: any) { assert(e.message === "请检查联系方式", "400→请检查联系方式"); }
  mockFetch(false, 422);
  try { await mod.submitLead("a1", { contact_name: "", phone: "" }); } catch (e: any) { assert(e.message === "请检查联系方式", "422→请检查联系方式"); }

  // 4. submitLead 404
  mockFetch(false, 404);
  try { await mod.submitLead("a1", { contact_name: "x", phone: "1" }); } catch (e: any) { assert(e.message === "报告不存在或无权提交", "404→报告不存在或无权提交"); }

  // 5. getReportDetail is_unlocked=false → user_report=null
  const summaryReport = { feasibility_score: 50, display_score: 50, tag: "t", tag_explanation: "x", preliminary_judgment: "x", strengths: [], risks: [], unlock_hint: "x" };
  mockFetch(true, 200, { assessment_id: "a1", status: "completed", is_unlocked: false, report_summary: summaryReport, user_report: null, used_template_report: false, created_at: "", completed_at: null, wechat_qr_url: null, followup_status: null, provider_id: null, model_name: null, rag_matches: null, branch: "experienced" });
  const d1 = await mod.getReportDetail("a1");
  assert(d1.is_unlocked === false, "is_unlocked=false");
  assert(d1.user_report === null, "is_unlocked=false 时 user_report=null");

  // 6. getReportDetail is_unlocked=true → user_report 存在
  const fullReport = { ...summaryReport, summary_conclusion: "sc", positioning_assessment: "pa", content_assessment: "ca", conversion_assessment: "va", dimension_scores: [], recommended_path: "rp", risk_reminder: "rr", action_plan_30days: ["1","2","3","4"], consultant_guide: "cg", unlock_hint: "x" };
  mockFetch(true, 200, { assessment_id: "a1", status: "completed", is_unlocked: true, report_summary: summaryReport, user_report: fullReport, used_template_report: false, created_at: "", completed_at: null, wechat_qr_url: null, followup_status: "已联系", provider_id: null, model_name: null, rag_matches: [{ title: "t1", source: "s", distance: 0.1, content_preview: "p..." }], branch: "experienced" });
  const d2 = await mod.getReportDetail("a1");
  assert(d2.is_unlocked === true, "is_unlocked=true");
  assert(d2.user_report !== null, "is_unlocked=true 时 user_report 存在");
  assert(d2.rag_matches !== null && d2.rag_matches[0].title === "t1", "detail 含 rag_matches");

  // 7. rag_matches 只作为 detail 字段，不进入 list item（list item 类型不含 rag_matches 字段验证通过编译即通过）

  // 8. report detail 404
  mockFetch(false, 404);
  try { await mod.getReportDetail("bad-id"); } catch (e: any) { assert(e.message === "报告不存在", "404→报告不存在"); }

  console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}
run();
