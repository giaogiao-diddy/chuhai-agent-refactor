from app.reports.guard import assert_user_report_safe
from app.schemas.audit import ReportAuditResult
from app.schemas.llm import LLMMessage
from app.schemas.report import ReportBundle
from app.services.deepseek_client import DeepSeekClient

SYSTEM_REPORT_AUDIT = """你是报告审计 Agent。检查报告内容质量，只输出短 JSON。

重要：字段完整性已由本地 Pydantic schema 校验完成，不要因"缺少某字段"而打回。
本地已保证 action_plan_30days 正好 4 条、所有报告字段存在。

你只检查：
1. 诊断是否具体（能否看出是针对该企业的个性化判断）
2. 内容是否空泛套话（比如"建议加强品牌建设"但没有具体操作）
3. 用户版是否泄露销售/顾问敏感字段
4. 行动建议是否可执行
5. 各节长度是否大致符合约束（summary≤400字等）

输出短 JSON: {"passed":true/false,"issues":["问题1"],"rewrite_required":true/false,"severity":"pass"/"warning"/"fail"}"""

# 字段缺失类 false positive 模式
_FIELD_MISSING_PATTERNS = [
    "缺少", "缺失", "不存在", "没有 action_plan", "没有 recommended_path",
    "没有 risk_reminder", "没有 sales_followup", "没有 consultant_notes",
    "action_plan_30days", "recommended_path 为空", "risk_reminder 为空",
    "sales_followup 为空", "consultant_notes 为空", "字段缺失",
]


def _filter_field_missing_issues(issues: list[str], bundle: ReportBundle) -> list[str]:
    """过滤字段缺失类误判。如果 Pydantic schema 已保证字段存在，移除这类 issue。"""
    ur = bundle.user_report
    lr = bundle.lead_report
    field_checks = {
        "action_plan": len(ur.action_plan_30days) >= 4,
        "recommended_path": bool(ur.recommended_path),
        "risk_reminder": bool(ur.risk_reminder),
        "sales_followup": bool(lr.sales_followup),
        "consultant_notes": bool(lr.consultant_notes),
        "summary_conclusion": bool(ur.summary_conclusion),
    }
    filtered: list[str] = []
    for issue in issues:
        is_field_missing = any(pat in issue for pat in _FIELD_MISSING_PATTERNS)
        if is_field_missing:
            # 确认对应字段确实存在
            fields_ok = True
            for key, ok in field_checks.items():
                if key in issue and not ok:
                    fields_ok = False
                    break
            if fields_ok:
                continue  # false positive, skip
            # else: field actually missing → keep
        filtered.append(issue)
    return filtered


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
    ai_result = await client.chat_json(
        [LLMMessage(role="system", content=SYSTEM_REPORT_AUDIT),
         LLMMessage(role="user", content=prompt)],
        response_model=ReportAuditResult,
        max_tokens=1500,
        temperature=0.0,
    )

    # Filter field-missing false positives
    if ai_result.issues and not ai_result.passed:
        filtered_issues = _filter_field_missing_issues(ai_result.issues, bundle)
        if filtered_issues != ai_result.issues:
            if not filtered_issues:
                # All field-missing false positives → pass as warning
                return ReportAuditResult(
                    passed=True, issues=ai_result.issues,
                    rewrite_required=False, severity="warning",
                )
            return ReportAuditResult(
                passed=False, issues=filtered_issues,
                rewrite_required=True, severity=ai_result.severity,
            )

    return ai_result
