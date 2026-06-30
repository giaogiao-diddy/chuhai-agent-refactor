"use client";

import { useCallback, useRef, useState } from "react";
import { startConversation, finishConversation } from "@/lib/api";
import { streamConversation } from "@/lib/streaming";
import type { AgentMessage, ConversationClientState, PublicReportSummary } from "@/lib/api";

export function useStreaming() {
  const [state, setState] = useState<ConversationClientState | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isFinishing, setIsFinishing] = useState(false);
  const [report, setReport] = useState<PublicReportSummary | null>(null);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [usedTemplateReport, setUsedTemplateReport] = useState(false);
  const [wechatQrUrl, setWechatQrUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const startingRef = useRef(false);
  const streamingRef = useRef(false);
  const finishingRef = useRef(false);
  const restartingRef = useRef(false);
  const isCompleted = Boolean(report);

  const start = useCallback(async () => {
    if (startingRef.current) return;
    startingRef.current = true;
    setIsStarting(true);
    setError(null);
    try {
      const data = await startConversation();
      setState(data.state);
      setMessages(data.state.messages);
    } catch {
      setError("启动失败");
    } finally {
      startingRef.current = false;
      setIsStarting(false);
    }
  }, []);

  const send = useCallback(async () => {
    if (report || !input.trim() || streamingRef.current || !state) return;
    setInput("");
    setError(null);
    streamingRef.current = true;
    setIsStreaming(true);
    const userMsg: AgentMessage = { role: "user", content: input.trim() };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    let assistantDraft = "";
    try {
      const gen = streamConversation({ state, message: input.trim() });
      for await (const event of gen) {
        if (event.type === "delta") {
          assistantDraft += event.content;
          setMessages([...nextMessages, { role: "assistant", content: assistantDraft }]);
        } else if (event.type === "done") {
          setState(event.state);
          setMessages(event.state.messages);
        } else if (event.type === "error") {
          setState(event.state);
          setMessages(event.state.messages);
          setError(event.message);
        }
      }
    } catch {
      setMessages(nextMessages);
      setError("请求失败，请重试");
    } finally {
      streamingRef.current = false;
      setIsStreaming(false);
    }
  }, [input, state, messages, report]);

  const finish = useCallback(async () => {
    if (!state || streamingRef.current || finishingRef.current || report) return;
    finishingRef.current = true;
    setIsFinishing(true);
    setError(null);
    try {
      const resp = await finishConversation(state);
      setState(resp.state);
      setMessages(resp.state.messages);
      setReport(resp.report_summary);
      setAssessmentId(resp.assessment_id);
      setUsedTemplateReport(resp.used_template_report);
      setWechatQrUrl(resp.wechat_qr_url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "报告生成失败，请稍后重试");
    } finally {
      finishingRef.current = false;
      setIsFinishing(false);
    }
  }, [state, report]);

  const restart = useCallback(async () => {
    if (restartingRef.current) return;
    restartingRef.current = true;
    setState(null);
    setMessages([]);
    setInput("");
    setError(null);
    setReport(null);
    setAssessmentId(null);
    setUsedTemplateReport(false);
    setWechatQrUrl(null);
    setIsStreaming(false);
    setIsFinishing(false);
    streamingRef.current = false;
    try {
      await start();
    } finally {
      restartingRef.current = false;
    }
  }, [start]);

  return {
    state, messages, input,
    isStarting, isStreaming, isFinishing, isCompleted,
    report, assessmentId, usedTemplateReport, wechatQrUrl, error,
    start, setInput, send, finish, restart,
  };
}
