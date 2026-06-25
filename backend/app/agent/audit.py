from app.reports.guard import assert_user_report_safe
from app.schemas.audit import ReportAuditResult
from app.schemas.llm import LLMMessage
from app.schemas.report import ReportBundle
from app.services.deepseek_client import DeepSeekClient

SYSTEM_REPORT_AUDIT = """你是报告审计 Agent。检查报告质量，只输出 JSON。

检查项：
1. 用户版禁止含 lead_score/lead_priority/sales_followup/consultant_notes/recommended_next_action
2. 用户版禁止含"销售话术""顾问跟进""线索优先级"等敏感词
3. action_plan_30days 正好 4 条
4. 报告必须具体，不能全是空话
5. summary_conclusion/recommended_path/risk_reminder 不得为空
6. 用户版不能出现顾问内部备注
7. LeadReport 必须包含 lead_score/lead_priority/sales_followup

输出 JSON: {"passed": true/false, "issues": ["问题1"], "rewrite_required": true/false, "severity": "pass"/"warning"/"fail"}"""


def validate_report_bundle_locally(bundle: ReportBundle) -> ReportAuditResult:
    issues: list[str] = []

    try:
        assert_user_report_safe(bundle.user_report)
    except ValueError as e:
        issues.append(str(e))

    if len(bundle.user_report.action_plan_30days) != 4:
        issues.append("action_plan_30days 不是 4 条")

    if not bundle.lead_report.sales_followup:
        issues.append("lead_report.sales_followup 为空")

    if not bundle.user_report.summary_conclusion:
        issues.append("summary_conclusion 为空")
    if not bundle.user_report.recommended_path:
        issues.append("recommended_path 为空")
    if not bundle.user_report.risk_reminder:
        issues.append("risk_reminder 为空")

    if issues:
        return ReportAuditResult(
            passed=False, issues=issues, rewrite_required=True, severity="fail"
        )
    return ReportAuditResult(
        passed=True, issues=[], rewrite_required=False, severity="pass"
    )


async def audit_report_bundle(bundle: ReportBundle) -> ReportAuditResult:
    local = validate_report_bundle_locally(bundle)
    if not local.passed:
        return local

    user_text = bundle.user_report.model_dump_json()
    lead_text = bundle.lead_report.model_dump_json()
    prompt = f"审计以下报告:\n用户版(前500字): {user_text[:500]}\n顾问版(前300字): {lead_text[:300]}"

    client = DeepSeekClient()
    return await client.chat_json(
        [LLMMessage(role="system", content=SYSTEM_REPORT_AUDIT),
         LLMMessage(role="user", content=prompt)],
        response_model=ReportAuditResult,
        max_tokens=800,
        temperature=0.0,
    )
