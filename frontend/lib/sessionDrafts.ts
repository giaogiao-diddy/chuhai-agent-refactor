import type { ConversationClientState } from "./api";

const STORAGE_KEY = "chuhai_diagnosis_drafts";
const ACTIVE_KEY = "chuhai_active_draft_id";

export type DiagnosisDraft = {
  id: string;
  title: string;
  state: ConversationClientState;
  selectedProviderId: string | null;
  lockedProviderId: string | null;
  lockedModelName: string | null;
  created_at: string;
  updated_at: string;
  last_active_at: string;
};

function _all(): DiagnosisDraft[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as DiagnosisDraft[];
  } catch {
    return [];
  }
}

function _saveAll(drafts: DiagnosisDraft[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts));
  } catch { /* quota exceeded */ }
}

function _now(): string {
  return new Date().toISOString();
}

export function listDrafts(): DiagnosisDraft[] {
  return _all().sort((a, b) => b.last_active_at.localeCompare(a.last_active_at));
}

export function getDraft(id: string): DiagnosisDraft | null {
  return _all().find(d => d.id === id) || null;
}

export function saveDraft(draft: DiagnosisDraft): void {
  const drafts = _all().filter(d => d.id !== draft.id);
  draft.updated_at = _now();
  // 只保留安全的 state 字段，不保存 report/lead 等对象
  const safeDraft = { ...draft };
  if (safeDraft.state) {
    const s = safeDraft.state as Record<string, unknown>;
    const { messages, slots, answers, branch, status, conversation_round, validation_errors, used_template_report, provider_id, model_name, readiness } = s;
    safeDraft.state = { messages, slots, answers, branch, status, conversation_round, validation_errors: validation_errors ?? [], used_template_report: used_template_report ?? false, provider_id: provider_id ?? null, model_name: model_name ?? null, readiness: readiness ?? null, public_error: null, ai_failure_count: s.ai_failure_count ?? 0 } as ConversationClientState;
  }
  drafts.push(safeDraft);
  _saveAll(drafts);
}

export function deleteDraft(id: string): void {
  const drafts = _all().filter(d => d.id !== id);
  _saveAll(drafts);
  if (getActiveDraftId() === id) {
    try { localStorage.removeItem(ACTIVE_KEY); } catch { /* */ }
  }
}

export function getActiveDraftId(): string | null {
  try { return localStorage.getItem(ACTIVE_KEY); } catch { return null; }
}

export function setActiveDraftId(id: string | null): void {
  if (id) {
    try { localStorage.setItem(ACTIVE_KEY, id); } catch { /* */ }
  } else {
    try { localStorage.removeItem(ACTIVE_KEY); } catch { /* */ }
  }
}

export function getActiveDraft(): DiagnosisDraft | null {
  const id = getActiveDraftId();
  if (!id) return null;
  return getDraft(id);
}

export function makeDraftTitle(state: ConversationClientState): string {
  const firstUser = state.messages?.find(m => m.role === "user");
  if (firstUser && firstUser.content.trim()) {
    const t = firstUser.content.trim();
    return t.length > 30 ? t.slice(0, 30) + "…" : t;
  }
  return "未命名诊断";
}

export function createDraftId(): string {
  return `draft_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
