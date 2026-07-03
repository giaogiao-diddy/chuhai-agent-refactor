"use client";

import type { ConversationClientState, MissingItem, ReadinessClientState } from "@/lib/api";

type Props = {
  state: ConversationClientState | null;
  missingItems: MissingItem[];
  nextQuestions: string[];
};

const SLOT_LABELS: Record<string, string> = {
  industry: "行业",
  main_product: "产品",
  target_market: "目标市场",
  overseas_experience: "海外经验",
  annual_revenue: "年营收",
  team_size: "团队规模",
  sales_team_size: "外贸团队",
  overseas_order_ratio: "海外订单占比",
  content_capability: "内容能力",
  conversion_channel: "转化渠道",
  monthly_budget: "月预算",
  consultation_intent: "咨询意向",
};

export default function DiagnosisProgressPanel({ state, missingItems, nextQuestions }: Props) {
  const readiness: ReadinessClientState | null | undefined = state?.readiness;
  const slots = state?.slots || {};
  const totalSlots = Object.keys(SLOT_LABELS).length;
  const filledSlots = Object.keys(SLOT_LABELS).filter(k => {
    const v = (slots as Record<string, { value: unknown } | null>)[k];
    return v && v.value !== null && v.value !== undefined && v.value !== "";
  }).length;

  // missingItems/nextQuestions 来自 finish MISSING_INFO，是最新权威数据，优先展示
  const displayMissing = missingItems.length > 0
    ? missingItems
    : readiness?.report_missing_items?.length
      ? readiness.report_missing_items
      : readiness?.missing_items ?? [];

  const displayQuestions = nextQuestions.length > 0
    ? nextQuestions
    : readiness?.next_questions ?? [];

  return (
    <div style={s.panel}>
      {/* Status */}
      <div style={s.section}>
        <div style={s.sectionTitle}>诊断进度</div>
        <div style={s.statRow}>
          <span style={s.statLabel}>已识别答案</span>
          <span style={s.statValue}>{readiness?.answered_count ?? Object.keys(state?.answers || {}).length}</span>
        </div>
        <div style={s.statRow}>
          <span style={s.statLabel}>初步评分</span>
          <span className={`badge ${readiness?.score_ready ? "badge-success" : "badge-warning"}`}>
            {readiness?.score_ready ? "已满足" : "未满足"}
          </span>
        </div>
        <div style={s.statRow}>
          <span style={s.statLabel}>完整报告</span>
          <span className={`badge ${readiness?.report_ready ? "badge-success" : "badge-neutral"}`}>
            {readiness?.report_ready ? "已满足" : "未满足"}
          </span>
        </div>
      </div>

      {/* Company profile */}
      <div style={s.section}>
        <div style={s.sectionTitle}>
          企业画像
          <span style={{ fontWeight: 400, fontSize: 12, color: "var(--color-text-muted)", marginLeft: 6 }}>
            {filledSlots}/{totalSlots}
          </span>
        </div>
        {Object.entries(SLOT_LABELS).map(([key, label]) => {
          const sv = (slots as Record<string, { value: unknown } | null>)[key];
          const hasValue = sv && sv.value !== null && sv.value !== undefined && sv.value !== "";
          return (
            <div key={key} style={s.slotRow}>
              <span style={s.slotLabel}>{label}</span>
              <span style={{ ...s.slotValue, color: hasValue ? "var(--color-text)" : "var(--color-text-muted)" }}>
                {hasValue ? String(sv!.value) : "—"}
              </span>
            </div>
          );
        })}
      </div>

      {/* Missing items */}
      {displayMissing.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>
            还需补充
            <span style={{ fontWeight: 400, fontSize: 12, color: "var(--color-text-muted)", marginLeft: 6 }}>
              {displayMissing.length} 项
            </span>
          </div>
          {displayMissing.slice(0, 6).map((m, i) => (
            <div key={i} style={s.missingRow}>
              <div style={s.missingLabel}>{m.label}</div>
              {m.ask && <div style={s.missingAsk}>{m.ask}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Next questions */}
      {displayQuestions.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>下一步建议</div>
          {displayQuestions.slice(0, 3).map((q, i) => (
            <div key={i} style={s.questionRow}>
              {i + 1}. {q}
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!readiness && missingItems.length === 0 && nextQuestions.length === 0 && (
        <div style={{ ...s.section, textAlign: "center", color: "var(--color-text-muted)", fontSize: 13 }}>
          开始对话后将在此显示诊断进度
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  panel: {
    display: "flex", flexDirection: "column", gap: 12,
    fontSize: 13,
  },
  section: {
    background: "var(--color-surface)", borderRadius: "var(--radius-md)",
    padding: "12px 14px", border: "1px solid var(--color-border)",
  },
  sectionTitle: {
    fontSize: 13, fontWeight: 600, color: "var(--color-text)",
    marginBottom: 8, paddingBottom: 6, borderBottom: "1px solid var(--color-border)",
  },
  statRow: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "3px 0", fontSize: 13,
  },
  statLabel: { color: "var(--color-text-secondary)" },
  statValue: { fontWeight: 600, color: "var(--color-text)" },
  slotRow: {
    display: "flex", justifyContent: "space-between", alignItems: "baseline",
    padding: "2px 0", fontSize: 12,
  },
  slotLabel: { color: "var(--color-text-muted)", flexShrink: 0, marginRight: 8 },
  slotValue: { textAlign: "right", wordBreak: "break-word" },
  missingRow: {
    padding: "5px 0", borderBottom: "1px solid var(--color-border)",
  },
  missingLabel: { fontWeight: 600, fontSize: 12, color: "var(--color-warning)" },
  missingAsk: { fontSize: 12, color: "var(--color-text-secondary)", marginTop: 2 },
  questionRow: {
    padding: "4px 0", fontSize: 12, color: "var(--color-text-secondary)",
    lineHeight: 1.4,
  },
};
