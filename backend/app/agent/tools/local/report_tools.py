from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.reports.guard import assert_user_report_safe
from app.reports.splitter import split_report
from app.schemas.agent_state import AgentState
from app.schemas.report import LeadReport, RawAIReport, UserReport
from app.schemas.scoring import ScoringResult
from app.schemas.slots import CompanySlots


# ── report.split ──

class ReportSplitInput(BaseModel):
    raw_report: RawAIReport
    scoring_result: ScoringResult
    slots: CompanySlots | None = None


class ReportSplitOutput(BaseModel):
    user_report: UserReport
    lead_report: LeadReport


def report_split_handler(
    inp: ReportSplitInput,
    ctx: ToolContext,
) -> ToolResult:
    state = AgentState()
    state.scoring_result = inp.scoring_result
    state.slots = inp.slots or CompanySlots()

    bundle = split_report(inp.raw_report, state)

    return ToolResult(data=ReportSplitOutput(
        user_report=bundle.user_report,
        lead_report=bundle.lead_report,
    ))


# ── report.guard ──

class ReportGuardInput(BaseModel):
    user_report: UserReport


class ReportGuardOutput(BaseModel):
    passed: bool


def report_guard_handler(
    inp: ReportGuardInput,
    ctx: ToolContext,
) -> ToolResult:
    try:
        assert_user_report_safe(inp.user_report)
    except ValueError as e:
        return ToolResult(error=ToolError(
            code=ToolErrorCode.PERMANENT,
            message=str(e),
            retryable=False,
        ))

    return ToolResult(data=ReportGuardOutput(passed=True))
