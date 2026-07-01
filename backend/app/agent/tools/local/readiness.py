from typing import Literal

from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolResult
from app.schemas.readiness import MissingItem, ReadinessResult


class ReadinessCheckInput(BaseModel):
    answers: dict[str, list[str]]
    branch: Literal["experienced", "inexperienced"] | None = None


# 生成报告的最低 answers 数量（含 Q5）
_MIN_ANSWERS = 8

# 报告关键问题
_KEY_IDS = {"Q5", "Q8", "Q17", "Q19", "Q30", "Q31"}

_MISSING_LABELS: dict[str, str] = {
    "Q5": "海外订单占比",
    "Q8": "目标市场",
    "Q17": "出海方式",
    "Q19": "试错预算",
    "Q30": "最想解决的问题",
    "Q31": "预约咨询意愿",
    "answer_count": "补充企业关键信息",
}

_MISSING_REASONS: dict[str, str] = {
    "Q5": "需要确认企业是否有海外经验以确定分支",
    "Q8": "目标市场是评估出海路径的重要参考",
    "Q17": "出海方式是判断路径清晰度的关键",
    "Q19": "预算决定可落地的策略规模",
    "Q30": "最想解决的问题帮助定制诊断方向",
    "Q31": "预约意愿反映企业行动力与线索质量",
}

_MISSING_ASKS: dict[str, str] = {
    "Q5": "目前海外订单或海外客户占比大概是多少？",
    "Q8": "接下来最想重点开发哪个海外市场？",
    "Q17": "你目前还考虑增加哪些出海方式？例如 TikTok Shop、海外短视频、B2B平台、独立站、展会等。",
    "Q19": "每月能接受的出海试错预算大概是多少？",
    "Q30": "最想让出海顾问帮你解决什么问题？",
    "Q31": "如果报告显示适合出海，是否愿意预约 1V1 咨询？",
}


def readiness_check_handler(
    inp: ReadinessCheckInput,
    ctx: ToolContext,
) -> ToolResult:
    missing: list[MissingItem] = []

    # 分支判断
    if inp.branch is None or "Q5" not in inp.answers or len(inp.answers.get("Q5", [])) == 0:
        missing.append(MissingItem(
            question_id="Q5",
            label=_MISSING_LABELS["Q5"],
            reason=_MISSING_REASONS["Q5"],
            ask=_MISSING_ASKS.get("Q5"),
        ))
        return ToolResult(data=ReadinessResult(
            ready=False,
            missing_items=missing,
            next_questions=["请先确认企业是否有海外经验（Q5）"],
        ))

    if inp.branch == "inexperienced":
        return ToolResult(data=ReadinessResult(
            ready=False,
            unsupported_branch=True,
            next_questions=["深度诊断优先支持已有出海经验企业"],
        ))

    # experienced 分支
    if inp.branch != "experienced":
        return ToolResult(data=ReadinessResult(
            ready=False,
            missing_items=[MissingItem(
                question_id="branch",
                label="分支状态",
                reason="分支状态无效",
            )],
        ))

    # 有效 answers 计数
    valid_answers = 0
    for q_id, selected in inp.answers.items():
        if isinstance(selected, list) and len(selected) > 0:
            valid_answers += 1

    # 检查关键问题（无论 answers 数量是否 >= 8）
    for qid in _KEY_IDS:
        if qid == "Q5":
            continue  # Q5 已在前置检查中处理
        if qid not in inp.answers or len(inp.answers.get(qid, [])) == 0:
            missing.append(MissingItem(
                question_id=qid,
                label=_MISSING_LABELS.get(qid, qid),
                reason=_MISSING_REASONS.get(qid, "报告生成需要此项信息"),
                ask=_MISSING_ASKS.get(qid),
            ))

    if valid_answers < _MIN_ANSWERS:
        missing.append(MissingItem(
            question_id="answer_count",
            label="补充企业关键信息",
            reason=f"至少需要 {_MIN_ANSWERS} 个有效答案，当前仅 {valid_answers} 个",
        ))

    if missing:
        return ToolResult(data=ReadinessResult(
            ready=False,
            missing_items=missing,
            next_questions=[
                m.ask if m.ask else _MISSING_LABELS.get(m.question_id, m.question_id)
                for m in missing[:4]
            ],
        ))

    return ToolResult(data=ReadinessResult(ready=True))
