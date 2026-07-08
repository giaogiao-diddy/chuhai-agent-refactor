"use client";

import { useCallback, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { startConversation, finishConversation, FinishMissingInfoError } from "@/lib/api";
import { streamConversation } from "@/lib/streaming";
import type { AgentTraceEvent } from "@/lib/streaming";
import type { AgentMessage, ConversationClientState, PublicReportSummary, MissingItem } from "@/lib/api";
import {
  createDraftId, makeDraftTitle, saveDraft, deleteDraft,
  setActiveDraftId, getActiveDraft, type DiagnosisDraft,
} from "@/lib/sessionDrafts";

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
  const [missingItems, setMissingItems] = useState<MissingItem[]>([]);
  const [nextQuestions, setNextQuestions] = useState<string[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null);
  const [lockedProviderId, setLockedProviderId] = useState<string | null>(null);
  const [lockedModelName, setLockedModelName] = useState<string | null>(null);
  const [traceEvents, setTraceEvents] = useState<AgentTraceEvent[]>([]);
  const [draftId, setDraftId] = useState<string | null>(null);
  const startingRef = useRef(false);
  const streamingRef = useRef(false);
  const finishingRef = useRef(false);
  const restartingRef = useRef(false);
  const isCompleted = Boolean(report);

  const _saveDraft = useCallback((st: ConversationClientState, pid: string | null, mid: string | null, selPid: string | null, selMid: string | null, did: string) => {
    saveDraft({
      id: did,
      title: makeDraftTitle(st),
      state: st,
      selectedProviderId: selPid,
      lockedProviderId: pid,
      lockedModelName: selMid,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      last_active_at: new Date().toISOString(),
    });
  }, []);

  const start = useCallback(async (providerId?: string | null, modelName?: string | null) => {
    if (startingRef.current) return;
    startingRef.current = true;
    setIsStarting(true);
    setError(null);
    try {
      const data = await startConversation({
        provider_id: providerId || undefined,
        model_name: modelName || undefined,
      });
      setState(data.state);
      setMessages(data.state.messages);
      setLockedProviderId(data.provider_id);
      setLockedModelName(data.model_name);
      const did = createDraftId();
      setDraftId(did);
      setActiveDraftId(did);
      _saveDraft(data.state, data.provider_id, data.model_name, providerId || null, modelName || null, did);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "启动失败");
    } finally {
      startingRef.current = false;
      setIsStarting(false);
    }
  }, [_saveDraft]);

  const send = useCallback(async () => {
    if (report || !input.trim() || streamingRef.current || !state) return;
    setInput("");
    setError(null);
    setMissingItems([]);
    setNextQuestions([]);
    setTraceEvents([]);
    streamingRef.current = true;
    setIsStreaming(true);
    const userMsg: AgentMessage = { role: "user", content: input.trim() };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    let assistantDraft = "";
    let latestState = state;
    try {
      const gen = streamConversation({ state, message: input.trim() });
      for await (const event of gen) {
        if (event.type === "delta") {
          assistantDraft += event.content;
          flushSync(() => {
            setMessages([...nextMessages, { role: "assistant", content: assistantDraft }]);
          });
          // 微延迟让浏览器有时间绘制，实现逐字效果
          if (assistantDraft.length % 3 === 0) {
            await new Promise(r => setTimeout(r, 0));
          }
        } else if (event.type === "done") {
          setState(event.state);
          setMessages(event.state.messages);
          latestState = event.state;
        } else if (event.type === "trace") {
          setTraceEvents(prev => [...prev, event]);
        } else if (event.type === "error") {
          setState(event.state);
          setMessages(event.state.messages);
          setError(event.message);
          latestState = event.state;
        }
      }
      if (draftId && latestState) {
        _saveDraft(latestState, lockedProviderId, lockedModelName, selectedProviderId, lockedModelName, draftId);
      }
    } catch {
      setMessages(nextMessages);
      setError("请求失败，请重试");
    } finally {
      streamingRef.current = false;
      setIsStreaming(false);
    }
  }, [input, state, messages, report, draftId, lockedProviderId, lockedModelName, selectedProviderId, _saveDraft]);

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
      if (draftId) {
        deleteDraft(draftId);
        setDraftId(null);
      }
    } catch (e: unknown) {
      if (e instanceof FinishMissingInfoError) {
        setMissingItems(e.missingItems);
        setNextQuestions(e.nextQuestions);
        setError("信息还不够，请继续补充以下内容");
      } else {
        setError(e instanceof Error ? e.message : "报告生成失败，请稍后重试");
      }
    } finally {
      finishingRef.current = false;
      setIsFinishing(false);
    }
  }, [state, report, draftId]);

  const restart = useCallback(async () => {
    if (restartingRef.current) return;
    restartingRef.current = true;
    if (draftId) { deleteDraft(draftId); }
    setState(null);
    setMessages([]);
    setInput("");
    setError(null);
    setMissingItems([]);
    setNextQuestions([]);
    setReport(null);
    setAssessmentId(null);
    setUsedTemplateReport(false);
    setWechatQrUrl(null);
    setIsStreaming(false);
    setIsFinishing(false);
    setLockedProviderId(null);
    setLockedModelName(null);
    setTraceEvents([]);
    setDraftId(null);
    streamingRef.current = false;
    try {
      await start(selectedProviderId);
    } finally {
      restartingRef.current = false;
    }
  }, [start, selectedProviderId, draftId]);

  const newConversation = useCallback(async () => {
    if (restartingRef.current) return;
    restartingRef.current = true;
    setState(null);
    setMessages([]);
    setInput("");
    setError(null);
    setMissingItems([]);
    setNextQuestions([]);
    setReport(null);
    setAssessmentId(null);
    setUsedTemplateReport(false);
    setWechatQrUrl(null);
    setIsStreaming(false);
    setIsFinishing(false);
    setLockedProviderId(null);
    setLockedModelName(null);
    setTraceEvents([]);
    setDraftId(null);
    streamingRef.current = false;
    try {
      await start(selectedProviderId);
    } finally {
      restartingRef.current = false;
    }
  }, [start, selectedProviderId]);

  const restoreDraft = useCallback((draft: DiagnosisDraft) => {
    setState(draft.state);
    setMessages(draft.state.messages);
    setLockedProviderId(draft.lockedProviderId);
    setLockedModelName(draft.lockedModelName);
    setSelectedProviderId(draft.selectedProviderId);
    setDraftId(draft.id);
    setActiveDraftId(draft.id);
    setReport(null);
    setAssessmentId(null);
    setMissingItems([]);
    setNextQuestions([]);
    setTraceEvents([]);
    setError(null);
    setInput("");
    setUsedTemplateReport(false);
    setWechatQrUrl(null);
  }, []);

  return {
    state, messages, input,
    isStarting, isStreaming, isFinishing, isCompleted,
    report, assessmentId, usedTemplateReport, wechatQrUrl, error,
    missingItems, nextQuestions,
    selectedProviderId, lockedProviderId, lockedModelName, traceEvents, draftId,
    start, setInput, send, finish, restart, newConversation, setSelectedProviderId, restoreDraft,
  };
}
