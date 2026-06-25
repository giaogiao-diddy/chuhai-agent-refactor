from pydantic import BaseModel, Field, field_validator

from app.schemas.agent_state import AgentBranch, AgentMessage, AgentState, AgentStatus
from app.schemas.report import UserReport
from app.schemas.slots import CompanySlots


class ConversationClientState(BaseModel):
    """API 安全通信模型：不包含 raw_report/user_report/lead_report/scoring_result/audit_result/lead_* 等顾问/内部字段。"""
    messages: list[AgentMessage]
    slots: CompanySlots = Field(default_factory=CompanySlots)
    answers: dict[str, list[str]] = Field(default_factory=dict)
    branch: AgentBranch | None = None
    status: AgentStatus = "active"
    conversation_round: int = 0
    ai_failure_count: int = 0
    validation_errors: list[str] = Field(default_factory=list)
    used_template_report: bool = False
    public_error: str | None = None

    def to_agent_state(self) -> AgentState:
        return AgentState(
            messages=self.messages,
            slots=self.slots,
            branch=self.branch,
            status=self.status,
            conversation_round=self.conversation_round,
            ai_failure_count=self.ai_failure_count,
            validation_errors=self.validation_errors,
            answers=self.answers,
            used_template_report=self.used_template_report,
        )

    @classmethod
    def from_agent_state(cls, state: AgentState) -> "ConversationClientState":
        public_error = None
        if state.report_error:
            public_error = "报告生成过程已自动处理，请查看报告结果"
        elif state.scoring_error:
            public_error = "当前信息不足，系统已生成保守诊断"
        # 清洗 validation_errors：固定安全文案，不回显原始 question_id / option_id / 异常
        safe_errors: list[str] = []
        for e in state.validation_errors:
            if "未知题号" in e:
                safe_errors.append("存在未知题号，已忽略")
            elif "无效选项" in e:
                safe_errors.append("存在无效选项，已忽略")
            elif "单选题" in e:
                safe_errors.append("存在单选题多选，已忽略")
            elif "分支不允许" in e:
                safe_errors.append("存在不适用分支题目，已忽略")
            elif "低置信" in e:
                safe_errors.append("存在低置信信息，已忽略")
            elif "忽略槽位" in e:
                safe_errors.append("存在无法使用的槽位信息，已忽略")
            elif "开放题不允许" in e:
                safe_errors.append("存在开放题答案，已忽略")
            else:
                safe_errors.append("部分内部验证信息已过滤")
        # 去重
        safe_errors = list(dict.fromkeys(safe_errors))
        return cls(
            messages=state.messages,
            slots=state.slots,
            branch=state.branch,
            status=state.status,
            conversation_round=state.conversation_round,
            ai_failure_count=state.ai_failure_count,
            validation_errors=safe_errors,
            answers=state.answers,
            used_template_report=state.used_template_report,
            public_error=public_error,
        )


class ConversationStartResponse(BaseModel):
    state: ConversationClientState
    assistant_message: str


class ConversationContinueRequest(BaseModel):
    state: ConversationClientState
    message: str = Field(min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message 不能为空白字符")
        return v


class ConversationContinueResponse(BaseModel):
    state: ConversationClientState
    assistant_message: str | None
    conversation_round: int
    should_stop: bool


class ConversationStreamRequest(BaseModel):
    state: ConversationClientState
    message: str = Field(min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message 不能为空白字符")
        return v


class ConversationFinishRequest(BaseModel):
    state: ConversationClientState


class ConversationFinishResponse(BaseModel):
    assessment_id: str
    state: ConversationClientState
    user_report: UserReport
    used_template_report: bool
