from typing import Any, Literal

from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.scoring.answer_scoring import build_scoring_input
from app.scoring.engine import calculate_scoring
from app.schemas.scoring import ScoringResult


class ScoreCalculateInput(BaseModel):
    answers: dict[str, list[str]]
    branch: Literal["experienced", "inexperienced"]
    q1_slots: Any | None = None


class ScoreCalculateOutput(BaseModel):
    scoring_result: ScoringResult


def score_calculate_handler(
    inp: ScoreCalculateInput,
    ctx: ToolContext,
) -> ToolResult:
    if inp.branch == "inexperienced":
        return ToolResult(error=ToolError(
            code=ToolErrorCode.PERMANENT,
            message="inexperienced 分支不支持评分",
            retryable=False,
        ))

    try:
        scoring_input = build_scoring_input(
            answers=inp.answers,
            branch=inp.branch,
            q1_slots=inp.q1_slots,
        )
        scoring_result = calculate_scoring(scoring_input)
    except (ValueError, TypeError) as e:
        return ToolResult(error=ToolError(
            code=ToolErrorCode.PERMANENT,
            message=str(e),
            retryable=False,
        ))

    return ToolResult(data=ScoreCalculateOutput(scoring_result=scoring_result))
