from pydantic import BaseModel

from app.agent.audit import audit_report_bundle, validate_report_bundle_locally
from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.schemas.audit import ReportAuditResult
from app.schemas.report import RawAIReport, LeadReport, ReportBundle, UserReport


class ReportAuditInput(BaseModel):
    user_report: UserReport
    lead_report: LeadReport
    raw_report: RawAIReport


class ReportAuditOutput(BaseModel):
    audit_result: ReportAuditResult


async def report_audit_deepseek_handler(
    inp: ReportAuditInput,
    ctx: ToolContext,
) -> ToolResult:
    bundle = ReportBundle(
        raw_report=inp.raw_report,
        user_report=inp.user_report,
        lead_report=inp.lead_report,
    )
    # 先本地校验
    local = validate_report_bundle_locally(bundle)
    if not local.passed:
        return ToolResult(data=ReportAuditOutput(audit_result=local))

    try:
        ai_audit = await audit_report_bundle(
            bundle,
            client_base_url=ctx.provider_base_url if ctx is not None else None,
            client_api_key=ctx.provider_api_key if ctx is not None else None,
            client_model=ctx.provider_model if ctx is not None else None,
        )
        return ToolResult(data=ReportAuditOutput(audit_result=ai_audit))
    except Exception as e:
        return ToolResult(error=ToolError(
            code=ToolErrorCode.TRANSIENT, message=str(e), retryable=True,
        ))
