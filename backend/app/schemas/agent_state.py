from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.audit import ReportAuditResult
from app.schemas.readiness import ReadinessResult
from app.schemas.report import LeadReport, RawAIReport, UserReport
from app.schemas.scoring import ScoringResult
from app.schemas.slots import CompanySlots


class AgentMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


AgentStatus = Literal[
    "active",
    "ready_to_score",
    "generating_report",
    "completed",
    "failed",
    "fallback_questionnaire",
]

AgentBranch = Literal["experienced", "inexperienced"]


class AgentState(BaseModel):
    conversation_id: str | None = None
    user_id: str | None = None
    messages: list[AgentMessage] = Field(default_factory=list)
    slots: CompanySlots = Field(default_factory=CompanySlots)
    answers: dict[str, list[str]] = Field(default_factory=dict)
    branch: AgentBranch | None = None
    status: AgentStatus = "active"
    conversation_round: int = 0
    max_rounds: int = 8
    ai_failure_count: int = 0
    max_ai_failures: int = 2
    validation_errors: list[str] = Field(default_factory=list)
    scoring_result: ScoringResult | None = None
    scoring_error: str | None = None
    raw_report: RawAIReport | None = None
    user_report: UserReport | None = None
    lead_report: LeadReport | None = None
    report_error: str | None = None
    audit_result: ReportAuditResult | None = None
    report_retry_count: int = 0
    max_report_retries: int = 2
    used_template_report: bool = False
    readiness_result: ReadinessResult | None = None
    provider_id: str | None = None
    model_name: str | None = None
    rag_matches: list[dict] | None = None

