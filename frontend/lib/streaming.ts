import type { ConversationClientState } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type AgentTraceEvent = {
  type: "trace";
  step: "extract" | "readiness" | "memory_recall" | "dialogue" | "rag_search" | "report_generate" | "report_audit";
  status: "started" | "completed" | "failed";
  elapsed_ms?: number | null;
  summary?: string | null;
};

export type StreamEvent =
  | { type: "delta"; content: string }
  | { type: "done"; state: ConversationClientState }
  | { type: "error"; message: string; state: ConversationClientState }
  | AgentTraceEvent;

export function parseSseLines(input: string): { events: StreamEvent[]; rest: string } {
  const lines = input.split("\n");
  const rest = lines.pop() || "";
  const events: StreamEvent[] = [];

  for (const line of lines) {
    if (!line.startsWith("data: ")) continue;
    const jsonStr = line.slice(6).trim();
    if (!jsonStr) continue;
    try {
      events.push(JSON.parse(jsonStr) as StreamEvent);
    } catch {
      throw new Error(`SSE JSON parse error: ${jsonStr.slice(0, 100)}`);
    }
  }
  return { events, rest };
}

export async function* streamConversation(params: {
  state: ConversationClientState;
  message: string;
}): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_BASE}/conversation/continue-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state: params.state, message: params.message }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`stream request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSseLines(buffer);
    buffer = rest;
    for (const event of events) yield event;
  }

  // stream 结束：处理残留 buffer
  if (buffer.trim()) {
    const { events } = parseSseLines(buffer + "\n");
    for (const event of events) yield event;
  }
}
