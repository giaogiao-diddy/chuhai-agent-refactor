const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type AgentMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type SlotValue = {
  value: unknown | null;
  confidence: number;
};

export type ConversationClientState = {
  messages: AgentMessage[];
  slots: Record<string, SlotValue | null>;
  answers: Record<string, string[]>;
  branch: "experienced" | "inexperienced" | null;
  status: string;
  conversation_round: number;
  ai_failure_count: number;
  validation_errors: string[];
  used_template_report: boolean;
  public_error: string | null;
};

export type StartConversationResponse = {
  state: ConversationClientState;
  assistant_message: string;
};

export async function startConversation(): Promise<StartConversationResponse> {
  const res = await fetch(`${API_BASE}/conversation/start`, { method: "POST", headers: { "Content-Type": "application/json" } });
  if (!res.ok) throw new Error("启动失败");
  return res.json();
}

export type DimensionScore = {
  name: string;
  raw_score: number;
  max_score: number;
  normalized_score: number;
};

export type UserReport = {
  feasibility_score: number; display_score: number;
  tag: string; tag_explanation: string; preliminary_judgment: string;
  strengths: string[]; risks: string[];
  summary_conclusion: string; positioning_assessment: string;
  content_assessment: string; conversion_assessment: string;
  dimension_scores: DimensionScore[];
  recommended_path: string; risk_reminder: string;
  action_plan_30days: string[]; consultant_guide: string; unlock_hint: string;
};

export type PublicReportSummary = {
  feasibility_score: number; display_score: number;
  tag: string; tag_explanation: string; preliminary_judgment: string;
  strengths: string[]; risks: string[]; unlock_hint: string;
};

export type FinishConversationResponse = {
  assessment_id: string; state: ConversationClientState;
  report_summary: PublicReportSummary; used_template_report: boolean;
  wechat_qr_url: string | null;
};

const ANON_KEY = "anonymous_user_id";
const AUTH_TOKEN_KEY = "auth_token";
const OAUTH_STATE_KEY = "oauth_state";

export function getAuthToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return !!getAuthToken();
}

function getOAuthState(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(OAUTH_STATE_KEY) || "";
}

function setOAuthState(state: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(OAUTH_STATE_KEY, state);
}

function clearOAuthState(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(OAUTH_STATE_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function getAnonymousUserId(): string {
  if (typeof window === "undefined") return "";
  const existing = localStorage.getItem(ANON_KEY);
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem(ANON_KEY, id);
  return id;
}

export async function finishConversation(state: ConversationClientState): Promise<FinishConversationResponse> {
  const res = await fetch(`${API_BASE}/conversation/finish`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ state, anonymous_user_id: getAnonymousUserId() }),
  });
  if (!res.ok) { if (res.status === 400) throw new Error("对话信息不足，请先补充企业情况"); throw new Error("报告生成失败，请稍后重试"); }
  return res.json();
}

export type ReportListItem = {
  assessment_id: string; status: string;
  branch: "experienced" | "inexperienced" | null;
  tag: string | null; feasibility_score: number | null; display_score: number | null;
  used_template_report: boolean; created_at: string; completed_at: string | null;
  followup_status: string | null;
};

export type ReportDetailResponse = {
  assessment_id: string; status: string;
  branch: "experienced" | "inexperienced" | null;
  used_template_report: boolean; created_at: string; completed_at: string | null;
  is_unlocked: boolean;
  report_summary: PublicReportSummary;
  user_report: UserReport | null;
  wechat_qr_url: string | null;
  followup_status: string | null;
};

export async function listReports(limit = 20): Promise<ReportListItem[]> {
  const anonId = getAnonymousUserId();
  if (!anonId && !getAuthToken()) return [];
  const params = new URLSearchParams({ limit: String(limit) });
  if (anonId) params.set("anonymous_user_id", anonId);
  const res = await fetch(`${API_BASE}/reports?${params}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("加载失败");
  return res.json();
}

export async function getReportDetail(assessmentId: string): Promise<ReportDetailResponse> {
  const anonId = getAnonymousUserId();
  if (!anonId && !getAuthToken()) throw new Error("无法获取用户标识");
  const params = new URLSearchParams();
  if (anonId) params.set("anonymous_user_id", anonId);
  const res = await fetch(`${API_BASE}/reports/${assessmentId}?${params}`, { headers: authHeaders() });
  if (res.status === 404) throw new Error("报告不存在");
  if (!res.ok) throw new Error("加载失败");
  return res.json();
}

export type LeadSubmissionRequest = {
  contact_name: string;
  phone: string;
  wechat_id?: string;
  company_name?: string;
  note?: string;
};

export type LeadSubmissionResponse = {
  submission_id: string;
  assessment_id: string;
  submitted: boolean;
  created_at: string;
};

export async function submitLead(assessmentId: string, payload: LeadSubmissionRequest): Promise<LeadSubmissionResponse> {
  const res = await fetch(`${API_BASE}/reports/${assessmentId}/lead-submission`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ ...payload, anonymous_user_id: getAnonymousUserId() }),
  });
  if (res.status === 400 || res.status === 422) throw new Error("请检查联系方式");
  if (res.status === 404) throw new Error("报告不存在或无权提交");
  if (!res.ok) throw new Error("提交失败，请稍后重试");
  return res.json();
}

export type FollowupStatus = "未联系" | "已联系" | "已预约" | "已成交";

export type LeadReport = {
  lead_score: number; lead_priority: string; tag: string;
  sales_followup: string; consultant_notes: string;
};

export type AdminLeadListItem = {
  submission_id: string; assessment_id: string;
  contact_name: string; phone: string;
  wechat_id: string | null; company_name: string | null;
  created_at: string;
  tag: string | null; feasibility_score: number | null;
  display_score: number | null; lead_priority: string | null;
  used_template_report: boolean; report_completed_at: string | null;
  followup_status: FollowupStatus;
};

export type AdminLeadDetail = {
  submission_id: string; assessment_id: string;
  contact_name: string; phone: string;
  wechat_id: string | null; company_name: string | null;
  note: string | null; created_at: string;
  tag: string | null; feasibility_score: number | null;
  display_score: number | null; lead_priority: string | null;
  used_template_report: boolean;
  followup_status: FollowupStatus; followup_note: string | null;
  user_report: UserReport; lead_report: LeadReport;
};

export async function listAdminLeads(params?: { followup_status?: FollowupStatus }): Promise<AdminLeadListItem[]> {
  const qs = new URLSearchParams();
  if (params?.followup_status) qs.set("followup_status", params.followup_status);
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await fetch(`${API_BASE}/admin/leads${suffix}`, {
    headers: authHeaders(),
  });
  if (res.status === 401) throw new Error("请先登录");
  if (res.status === 403) throw new Error("无权访问顾问后台");
  if (!res.ok) throw new Error("加载失败");
  return res.json();
}

export async function getAdminLeadDetail(submissionId: string): Promise<AdminLeadDetail> {
  const res = await fetch(`${API_BASE}/admin/leads/${submissionId}`, {
    headers: authHeaders(),
  });
  if (res.status === 401) throw new Error("请先登录");
  if (res.status === 403) throw new Error("无权访问顾问后台");
  if (res.status === 404) throw new Error("线索不存在");
  if (!res.ok) throw new Error("加载失败");
  return res.json();
}

export async function updateAdminLeadFollowup(
  submissionId: string,
  payload: { followup_status: FollowupStatus; followup_note?: string }
): Promise<AdminLeadDetail> {
  const res = await fetch(`${API_BASE}/admin/leads/${submissionId}/followup`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  if (res.status === 401) throw new Error("请先登录");
  if (res.status === 403) throw new Error("无权访问顾问后台");
  if (res.status === 404) throw new Error("线索不存在");
  if (res.status === 422) throw new Error("请检查跟进信息");
  if (!res.ok) throw new Error("更新失败");
  return res.json();
}

export type WechatLoginUrlResponse = {
  url: string;
  state: string;
};

export async function getWechatLoginUrl(): Promise<WechatLoginUrlResponse> {
  const res = await fetch(`${API_BASE}/auth/wechat/login-url`);
  if (res.status === 503) throw new Error("微信登录未配置");
  if (!res.ok) throw new Error("获取登录链接失败");
  const data = await res.json();
  // 保存 state 到 sessionStorage 用于 callback 比对
  setOAuthState(data.state);
  return { url: data.url, state: data.state };
}

export async function handleWechatCallback(code: string, state: string): Promise<AuthCallbackResponse> {
  // 先和 sessionStorage 中保存的 state 比对，防 CSRF
  const savedState = getOAuthState();
  if (!savedState || savedState !== state) {
    throw new Error("安全校验失败，请重新登录");
  }
  // 比对通过后清除
  clearOAuthState();

  const params = new URLSearchParams({ code, state });
  const res = await fetch(`${API_BASE}/auth/wechat/callback?${params}`);
  if (!res.ok) throw new Error("微信登录失败");
  const data = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export type AuthUser = {
  id: string;
  nickname: string | null;
  role: string;
};

export type AuthCallbackResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};
