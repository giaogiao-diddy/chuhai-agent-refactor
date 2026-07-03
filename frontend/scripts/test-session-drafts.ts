// polyfill localStorage for Node.js
(globalThis as any).localStorage = {
  _data: {} as Record<string, string>,
  getItem(k: string) { return this._data[k] ?? null; },
  setItem(k: string, v: string) { this._data[k] = v; },
  removeItem(k: string) { delete this._data[k]; },
  clear() { this._data = {}; },
};

import {
  listDrafts, saveDraft, getDraft, deleteDraft,
  getActiveDraftId, setActiveDraftId, getActiveDraft,
  makeDraftTitle, createDraftId,
} from "../lib/sessionDrafts";
import type { DiagnosisDraft } from "../lib/sessionDrafts";

let passed = 0;
let failed = 0;

function assert(cond: boolean, msg: string) {
  if (cond) { passed++; }
  else { console.error(`✗ ${msg}`); failed++; }
}

function _clear() { (localStorage as any)._data = {}; }

function _makeState(msgs: Array<{ role: string; content: string }>) {
  return {
    messages: msgs as any[],
    slots: {},
    answers: {},
    branch: null as any,
    status: "active",
    conversation_round: msgs.filter(m => m.role === "user").length,
    ai_failure_count: 0,
    validation_errors: [],
    used_template_report: false,
    public_error: null,
    provider_id: null,
    model_name: null,
    readiness: null,
  };
}

function _makeDraft(overrides: Partial<DiagnosisDraft> = {}): DiagnosisDraft {
  return {
    id: createDraftId(),
    title: "test",
    state: _makeState([{ role: "user", content: "hello" }]),
    selectedProviderId: null, lockedProviderId: null, lockedModelName: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_active_at: new Date().toISOString(),
    ...overrides,
  };
}

// ── Tests ──

console.log("sessionDrafts 测试:");

// 1. save + list
_clear();
const d1 = _makeDraft();
saveDraft(d1);
const list1 = listDrafts();
assert(list1.length === 1, "save + list: 1 draft");
assert(list1[0].id === d1.id, "save + list: correct id");

// 2. get
const got = getDraft(d1.id);
assert(got !== null, "get: found");
assert(got!.id === d1.id, "get: correct id");

// 3. delete
deleteDraft(d1.id);
assert(listDrafts().length === 0, "delete: removed");

// 4. update via save
const d2 = _makeDraft({ title: "original" });
saveDraft(d2);
d2.title = "updated";
d2.updated_at = new Date(Date.now() + 1000).toISOString();
saveDraft(d2);
const updated = getDraft(d2.id);
assert(updated !== null && updated.title === "updated", "save: updates title");

// 5. set/get active
setActiveDraftId(d2.id);
assert(getActiveDraftId() === d2.id, "setActiveDraftId / getActiveDraftId");
const active = getActiveDraft();
assert(active !== null && active.id === d2.id, "getActiveDraft: correct");

// 6. delete active clears active
deleteDraft(d2.id);
assert(getActiveDraftId() === null, "delete active: clears active id");
assert(getActiveDraft() === null, "delete active: getActiveDraft returns null");

// 7. title from first user message
const s1 = _makeState([{ role: "user", content: "我们公司想做东南亚市场" }]);
assert(makeDraftTitle(s1) === "我们公司想做东南亚市场", "title: first message");

// 8. title truncation
const longMsg = "我们是一家做智能健身器材的源头工厂主要产品有哑铃杠铃和力量训练设备目前有少量东南亚客户想做独立站出海";
const s2 = _makeState([{ role: "user", content: longMsg }]);
const t2 = makeDraftTitle(s2);
assert(t2.endsWith("…") && t2.length <= 33, `title: truncate (length=${t2.length})`);

// 9. title fallback
const s3 = _makeState([{ role: "assistant", content: "你好" }]);
assert(makeDraftTitle(s3) === "未命名诊断", "title: fallback when no user message");

// 10. no report fields in saved draft
const s4 = _makeState([{ role: "user", content: "hi" }]);
(s4 as any).report_summary = { feasibility_score: 99 };
(s4 as any).user_report = { summary_conclusion: "x" };
(s4 as any).lead_report = { sales_followup: "x" };
const d3 = _makeDraft({ state: s4 as any });
saveDraft(d3);
const raw = localStorage.getItem("chuhai_diagnosis_drafts") || "[]";
assert(!raw.includes("lead_report"), "storage: no lead_report");
assert(!raw.includes("sales_followup"), "storage: no sales_followup");

// 11. multiple drafts list sorted by last_active_at
_clear();
const older = _makeDraft({ last_active_at: "2025-01-01T00:00:00.000Z" });
const newer = _makeDraft({ last_active_at: "2025-06-01T00:00:00.000Z" });
saveDraft(older);
saveDraft(newer);
const sorted = listDrafts();
assert(sorted[0].id === newer.id, "sort: newest first");
assert(sorted[1].id === older.id, "sort: oldest second");

// 12. delete one draft should not affect others (restoreDraft-like safety)
_clear();
const a = _makeDraft({ title: "draft-a" });
const b = _makeDraft({ title: "draft-b" });
saveDraft(a);
saveDraft(b);
assert(listDrafts().length === 2, "two drafts saved");
deleteDraft(a.id);
const remaining = listDrafts();
assert(remaining.length === 1, "delete one: 1 remains");
assert(remaining[0].title === "draft-b", "delete one: correct draft remains");

// 13. setActiveDraftId survives delete of non-active draft
_clear();
const draftActive = _makeDraft();
const draftInactive = _makeDraft();
saveDraft(draftActive);
saveDraft(draftInactive);
setActiveDraftId(draftActive.id);
deleteDraft(draftInactive.id);
assert(getActiveDraftId() === draftActive.id, "active draft not cleared when deleting non-active");

// Cleanup
_clear();

console.log(`\n${passed} tests: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
