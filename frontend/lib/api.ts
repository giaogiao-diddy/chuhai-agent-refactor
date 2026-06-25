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
  const res = await fetch(`${API_BASE}/conversation/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
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
  feasibility_score: number;
  display_score: number;
  tag: string;
  tag_explanation: string;
  preliminary_judgment: string;
  strengths: string[];
  risks: string[];
  summary_conclusion: string;
  positioning_assessment: string;
  content_assessment: string;
  conversion_assessment: string;
  dimension_scores: DimensionScore[];
  recommended_path: string;
  risk_reminder: string;
  action_plan_30days: string[];
  consultant_guide: string;
  unlock_hint: string;
};

export type FinishConversationResponse = {
  assessment_id: string;
  state: ConversationClientState;
  user_report: UserReport;
  used_template_report: boolean;
};

export async function finishConversation(
  state: ConversationClientState
): Promise<FinishConversationResponse> {
  const res = await fetch(`${API_BASE}/conversation/finish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
  });
  if (!res.ok) {
    if (res.status === 400) throw new Error("对话信息不足，请先补充企业情况");
    throw new Error("报告生成失败，请稍后重试");
  }
  return res.json();
}
