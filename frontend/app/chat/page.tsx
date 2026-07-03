"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useStreaming } from "@/hooks/useStreaming";
import { getReportDetail, listPublicModelProviders } from "@/lib/api";
import { validateRenderedReport } from "@/lib/reportSafety";
import { listDrafts, deleteDraft, getActiveDraft } from "@/lib/sessionDrafts";
import type { DiagnosisDraft } from "@/lib/sessionDrafts";
import AppShell from "@/components/AppShell";
import DiagnosisProgressPanel from "@/components/DiagnosisProgressPanel";
import AgentTracePanel from "@/components/AgentTracePanel";
import UserReportCard from "@/components/UserReportCard";
import type { UserReport, ModelProviderPublicItem } from "@/lib/api";

export default function ChatPage() {
  const {
    state, messages, input, isStarting, isStreaming, isFinishing, isCompleted,
    report, assessmentId, usedTemplateReport, wechatQrUrl, error, missingItems, nextQuestions,
    selectedProviderId, lockedProviderId, lockedModelName, traceEvents, draftId,
    start, setInput, send, finish, restart, setSelectedProviderId, restoreDraft,
  } = useStreaming();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [fullReport, setFullReport] = useState<UserReport | null>(null);
  const [providers, setProviders] = useState<ModelProviderPublicItem[]>([]);
  const [providersLoaded, setProvidersLoaded] = useState(false);
  const [modelLoadError, setModelLoadError] = useState(false);
  const [drafts, setDrafts] = useState<DiagnosisDraft[]>([]);
  const [draftsLoaded, setDraftsLoaded] = useState(false);
  const [draftRestoreChecked, setDraftRestoreChecked] = useState(false);
  const draftWasRestored = useRef(false);

  const loadDrafts = () => { setDrafts(listDrafts()); };

  useEffect(() => {
    listPublicModelProviders()
      .then(list => { setProviders(list); setModelLoadError(false); })
      .catch(() => { setProviders([]); setModelLoadError(true); })
      .finally(() => setProvidersLoaded(true));
    loadDrafts();
    setDraftsLoaded(true);
  }, []);

  // Step 1: auto-restore active draft on mount (runs first)
  useEffect(() => {
    if (!draftsLoaded || state || isStarting) return;
    const active = getActiveDraft();
    if (active && active.state) {
      draftWasRestored.current = true;
      restoreDraft(active);
      setSelectedProviderId(active.selectedProviderId);
    }
    setDraftRestoreChecked(true);
  }, [draftsLoaded]); // eslint-disable-line react-hooks/exhaustive-deps

  // Step 2: auto-start only if no draft was restored and no conversation exists
  const hasStarted = useRef(false);
  useEffect(() => {
    if (!draftRestoreChecked || draftWasRestored.current) return;
    if (hasStarted.current || isStarting || state || !providersLoaded || providers.length === 0) return;
    hasStarted.current = true;
    const pid = selectedProviderId || providers[0]?.id || null;
    if (!selectedProviderId && pid) setSelectedProviderId(pid);
    start(pid);
  }, [draftRestoreChecked, providersLoaded, providers, state, isStarting, start, selectedProviderId, setSelectedProviderId]);

  const conversationActive = !!(state && !isCompleted);
  const modelLocked = !!(conversationActive && lockedProviderId);

  const handleUnlocked = useCallback(async () => {
    if (!assessmentId) return;
    try {
      const d = await getReportDetail(assessmentId);
      if (d.is_unlocked && d.user_report) setFullReport(d.user_report);
    } catch { /* unlock check silently fails */ }
  }, [assessmentId]);

  const displayReport = fullReport || report;
  const reportSafe = displayReport && validateRenderedReport(displayReport);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, displayReport]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const showFinish = state && state.conversation_round >= 3 && !isCompleted;
  const busy = isStreaming || isFinishing || isStarting;

  const currentProvider = providers.find(p => p.id === lockedProviderId);
  const modelLabel = currentProvider
    ? `${currentProvider.name} / ${lockedModelName || currentProvider.default_model}`
    : lockedModelName || "";

  const noModelAvailable = providersLoaded && providers.length === 0 && !modelLoadError;
  const modelUnavailable = !providersLoaded || noModelAvailable || modelLoadError || !state;
  const modelStatus = modelLocked ? modelLabel : undefined;
  const readiness = state?.readiness ?? null;

  function inputPlaceholder(): string {
    if (isCompleted) return "本次诊断已完成，可重新开始";
    if (!providersLoaded || isStarting) return "正在连接模型...";
    if (modelLoadError) return "模型列表加载失败，请刷新重试";
    if (noModelAvailable) return "请先配置 AI 模型";
    if (!state) return "正在启动诊断...";
    return "输入你的企业信息...";
  }

  return (
    <AppShell title="出海诊断" modelStatus={modelStatus}>
      <div className="chat-layout">
        {/* Left: chat column */}
        <div className="chat-main">
        {modelLoadError && (
          <div className="card" style={{ textAlign: "center", padding: "24px 16px", marginBottom: 16 }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>模型列表加载失败</div>
            <div className="status-msg">请检查网络连接或稍后刷新页面重试。</div>
          </div>
        )}
        {noModelAvailable && (
          <div className="card" style={{ textAlign: "center", padding: "24px 16px", marginBottom: 16 }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>暂无可用的 AI 模型</div>
            <div className="status-msg">请先到模型设置配置可用的模型提供商，然后开始诊断。</div>
            <a href="/settings/models" className="btn btn-primary" style={{ marginTop: 12 }}>前往模型设置 →</a>
          </div>
        )}

        {!modelLocked && !modelLoadError && providers.length > 0 && (
          <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>选择模型：</span>
            <select
              className="select"
              style={{ width: "auto", flex: 1, maxWidth: 300 }}
              value={selectedProviderId || ""}
              onChange={e => {
                const pid = e.target.value || null;
                setSelectedProviderId(pid);
                if (pid) start(pid);
              }}
              disabled={busy || conversationActive}
            >
              {providers.map(p => (
                <option key={p.id} value={p.id}>{p.name} / {p.default_model}</option>
              ))}
            </select>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} style={{
            display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", marginBottom: 10,
          }}>
            <div style={m.role === "user" ? bubble.user : bubble.assistant}>{m.content}</div>
          </div>
        ))}
        {isStarting && <div className="status-msg">正在连接...</div>}
        {error && <div className="error-msg">{error}</div>}
        {missingItems.length > 0 && (
          <div className="card" style={{ background: "var(--color-warning-bg)", marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6, color: "var(--color-warning)" }}>生成报告还缺少：</div>
            {missingItems.map((m, i) => (
              <div key={i} style={{ marginBottom: 6, fontSize: 14 }}>
                <span style={{ fontWeight: 600 }}>{m.label}</span>
                {m.ask && <div style={{ color: "var(--color-text-secondary)", marginTop: 2 }}>{m.ask}</div>}
              </div>
            ))}
          </div>
        )}
        {reportSafe && (
          <>
            <h3 style={{ fontSize: 18, marginBottom: 8 }}>诊断报告</h3>
            <UserReportCard
              report={displayReport}
              usedTemplateReport={usedTemplateReport}
              assessmentId={assessmentId}
              showReportsLink
              onUnlocked={handleUnlocked}
              wechatQrUrl={wechatQrUrl}
            />
          </>
        )}
        {displayReport && !reportSafe && <div className="error-msg">报告内容校验失败，请联系管理员</div>}
        <div ref={bottomRef} />

        {/* Input bar */}
        <div style={{
          position: "sticky", bottom: 0, display: "flex", padding: "12px 0",
          background: "var(--color-bg)", gap: 8, borderTop: "1px solid var(--color-border)", marginTop: 16,
        }}>
          {showFinish && (
            <button className="btn btn-sm" style={{ background: "var(--color-warning)", color: "#fff" }}
              onClick={finish} disabled={busy}>
              {isFinishing ? "生成中..." : "生成报告"}
            </button>
          )}
          {isCompleted && (
            <button className="btn btn-secondary btn-sm" onClick={restart} disabled={busy}>重新开始</button>
          )}
          {readiness?.report_ready && !isCompleted && (
            <span style={{ fontSize: 12, color: "var(--color-success)", alignSelf: "center" }}>信息已齐备</span>
          )}
          <textarea
            className="input"
            style={{ flex: 1, resize: "none", fontFamily: "inherit" }}
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={inputPlaceholder()}
            disabled={busy || isCompleted || modelUnavailable}
            rows={2}
          />
          <button className="btn btn-primary" onClick={send} disabled={busy || isCompleted || !input.trim() || modelUnavailable}>
            {isStreaming ? "..." : "发送"}
          </button>
        </div>
        </div>{/* /.chat-main */}

        {/* Right: diagnosis progress panel */}
        <div className="diagnosis-panel-col">
          <DiagnosisProgressPanel
            state={state}
            missingItems={missingItems}
            nextQuestions={nextQuestions}
          />
          <AgentTracePanel events={traceEvents} />

          {/* Draft manager */}
          <div className="card card-sm" style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: drafts.length > 0 ? 8 : 0 }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>诊断草稿</span>
              <button className="btn btn-secondary btn-sm" onClick={async () => {
                await restart();
                loadDrafts();
              }} disabled={isStreaming || isFinishing} style={{ fontSize: 11 }}>
                + 新建
              </button>
            </div>
            {drafts.length === 0 && (
              <div style={{ fontSize: 12, color: "var(--color-text-muted)", textAlign: "center", padding: "4px 0" }}>
                暂无草稿
              </div>
            )}
            {drafts.map(d => (
              <div key={d.id}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "5px 0", borderBottom: "1px solid var(--color-border)",
                  cursor: "pointer", fontSize: 12,
                  background: d.id === draftId ? "var(--color-primary-light)" : "transparent",
                  borderRadius: 4, paddingLeft: 6, paddingRight: 6,
                }}
                onClick={() => { if (d.id !== draftId && !isStreaming && !isFinishing) { restoreDraft(d); loadDrafts(); } }}
              >
                <div style={{ overflow: "hidden", flex: 1 }}>
                  <div style={{ fontWeight: d.id === draftId ? 600 : 400, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {d.title}
                  </div>
                  <div style={{ color: "var(--color-text-muted)", fontSize: 10 }}>
                    {d.last_active_at?.slice(0, 16).replace("T", " ")}
                  </div>
                </div>
                <button className="btn btn-danger btn-sm" style={{ padding: "2px 6px", fontSize: 10, flexShrink: 0, marginLeft: 6 }}
                  onClick={async e => {
                    e.stopPropagation();
                    if (d.id === draftId && !isStreaming && !isFinishing) { await restart(); loadDrafts(); }
                    else { deleteDraft(d.id); loadDrafts(); }
                  }}>
                  删除
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>{/* /.chat-layout */}
    </AppShell>
  );
}

const bubble = {
  user: {
    maxWidth: "80%", padding: "8px 14px", borderRadius: "16px 16px 4px 16px",
    background: "var(--color-primary)", color: "#fff", fontSize: 15,
    lineHeight: 1.5, whiteSpace: "pre-wrap" as const,
  },
  assistant: {
    maxWidth: "80%", padding: "8px 14px", borderRadius: "16px 16px 16px 4px",
    background: "var(--color-surface)", fontSize: 15, lineHeight: 1.5,
    whiteSpace: "pre-wrap" as const, border: "1px solid var(--color-border)",
  },
};
