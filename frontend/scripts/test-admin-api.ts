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

async function run() {
  console.log("Admin API 测试:");
  const mod = await import("../lib/api");
  mod.setAuthToken("test-jwt-token");
  const origFetch = (globalThis as any).fetch;

  // 1. listAdminLeads 401
  (globalThis as any).fetch = async () => ({ ok: false, status: 401 });
  try { await mod.listAdminLeads(); assert(false, "401"); } catch (e: any) { assert(e.message === "请先登录", "401→请先登录"); }

  // 2. 403
  (globalThis as any).fetch = async () => ({ ok: false, status: 403 });
  try { await mod.getAdminLeadDetail("x"); assert(false, "403"); } catch (e: any) { assert(e.message === "无权访问顾问后台", "403→无权访问"); }

  // 3. 404
  (globalThis as any).fetch = async () => ({ ok: false, status: 404 });
  try { await mod.getAdminLeadDetail("x"); assert(false, "404"); } catch (e: any) { assert(e.message === "线索不存在", "404→线索不存在"); }

  // 4. 200 with followup_status
  const mockList = [{ submission_id: "1", assessment_id: "a", contact_name: "t", phone: "1", wechat_id: null, company_name: null, created_at: "", tag: null, feasibility_score: null, display_score: null, lead_priority: null, used_template_report: false, report_completed_at: null, followup_status: "未联系" }];
  (globalThis as any).fetch = async () => ({ ok: true, json: async () => mockList });
  const r = await mod.listAdminLeads();
  assert(r[0].followup_status === "未联系", "list 含 followup_status");

  // 5. detail 200 with lead_report
  const mockDetail = { submission_id: "1", assessment_id: "a", contact_name: "t", phone: "1", wechat_id: null, company_name: null, note: null, created_at: "", tag: null, feasibility_score: null, display_score: null, lead_priority: null, used_template_report: false, followup_status: "未联系", followup_note: null, user_report: {} as any, lead_report: { lead_score: 30, lead_priority: "P2", tag: "x", sales_followup: "x", consultant_notes: "x" } };
  (globalThis as any).fetch = async () => ({ ok: true, json: async () => mockDetail });
  const d = await mod.getAdminLeadDetail("1");
  assert(d.lead_report.lead_score === 30, "detail 含 lead_report");

  // 6. Auth header 断言
  let capturedHeaders: any = {};
  (globalThis as any).fetch = async (_url: string, init: any) => {
    capturedHeaders = init?.headers || {};
    return { ok: true, json: async () => mockDetail };
  };
  await mod.listAdminLeads();
  assert(capturedHeaders.Authorization === "Bearer test-jwt-token", "list 带 Authorization");
  await mod.getAdminLeadDetail("1");
  assert(capturedHeaders.Authorization === "Bearer test-jwt-token", "detail 带 Authorization");

  // 7. updateAdminLeadFollowup PATCH
  let patchedUrl = ""; let patchedBody = "";
  (globalThis as any).fetch = async (url: string, init: any) => {
    capturedHeaders = init?.headers || {};
    patchedUrl = url.toString(); patchedBody = init.body;
    return { ok: true, json: async () => mockDetail };
  };
  await mod.updateAdminLeadFollowup("1", { followup_status: "已联系", followup_note: "ok" });
  assert(capturedHeaders.Authorization === "Bearer test-jwt-token", "PATCH 带 Authorization");
  assert(patchedUrl.includes("/followup"), "PATCH URL 含 /followup");
  assert(patchedBody.includes("已联系"), "PATCH body 含 已联系");

  // 9. filter param in URL
  let filterUrl = "";
  (globalThis as any).fetch = async (url: string, init: any) => {
    filterUrl = url.toString();
    capturedHeaders = init?.headers || {};
    return { ok: true, json: async () => mockList };
  };
  await mod.listAdminLeads({ followup_status: "已联系" });
  assert(filterUrl.includes("followup_status=") && filterUrl.includes(encodeURIComponent("已联系")), "filter URL 含 followup_status");
  await mod.listAdminLeads();
  assert(!filterUrl.includes("followup_status"), "无 filter 时 URL 不含 followup_status");

  // 10. 422
  (globalThis as any).fetch = async () => ({ ok: false, status: 422 });
  try { await mod.updateAdminLeadFollowup("x", { followup_status: "未联系" }); } catch (e: any) { assert(e.message === "请检查跟进信息", "422→请检查跟进信息"); }

  (globalThis as any).fetch = origFetch;
  console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}
run();
