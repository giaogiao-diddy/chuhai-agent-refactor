from pydantic import BaseModel, Field


class MissingItem(BaseModel):
    question_id: str
    label: str
    reason: str
    ask: str | None = None


class ReadinessResult(BaseModel):
    ready: bool
    score_ready: bool = False
    report_ready: bool = False
    missing_items: list[MissingItem] = Field(default_factory=list)
    report_missing_items: list[MissingItem] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    unsupported_branch: bool = False


class ReadinessClientState(BaseModel):
    """前端安全 DTO：只包含用户可感知的 readiness 信息，不泄露内部评分/审计/线索字段。"""
    score_ready: bool = False
    report_ready: bool = False
    missing_items: list[MissingItem] = Field(default_factory=list)
    report_missing_items: list[MissingItem] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    answered_count: int = 0

    @classmethod
    def from_readiness_result(cls, r: ReadinessResult, answered_count: int) -> "ReadinessClientState":
        return cls(
            score_ready=r.score_ready,
            report_ready=r.report_ready,
            missing_items=r.missing_items,
            report_missing_items=r.report_missing_items,
            next_questions=r.next_questions,
            answered_count=answered_count,
        )
