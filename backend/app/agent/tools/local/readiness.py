from typing import Literal

from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolResult
from app.schemas.readiness import MissingItem, ReadinessResult


class ReadinessCheckInput(BaseModel):
    answers: dict[str, list[str]]
    branch: Literal["experienced", "inexperienced"] | None = None


_MIN_ANSWERS = 8

# score_ready: 生成报告最低门槛
_SCORE_IDS = {"Q5", "Q8", "Q17", "Q19", "Q30", "Q31"}

# report_ready: 高质量诊断额外关键项
_REPORT_EXTRA_IDS = {"Q2a", "Q2b", "Q3a", "Q9", "Q11", "Q15", "Q22", "Q23", "Q28"}

_MISSING_LABELS: dict[str, str] = {
    "Q5": "海外订单占比", "Q8": "目标市场", "Q17": "出海方式",
    "Q19": "试错预算", "Q30": "最想解决的问题", "Q31": "预约咨询意愿",
    "answer_count": "补充企业关键信息",
    "Q2a": "成立年限", "Q2b": "团队人数", "Q3a": "年营收",
    "Q9": "目标市场选择原因", "Q11": "产品优势", "Q15": "交付稳定性",
    "Q22": "新媒体团队", "Q23": "海外社媒经验", "Q28": "外贸团队",
}

_MISSING_REASONS: dict[str, str] = {
    "Q5": "需要确认企业是否有海外经验以确定分支",
    "Q8": "目标市场是评估出海路径的重要参考",
    "Q17": "出海方式是判断路径清晰度的关键",
    "Q19": "预算决定可落地的策略规模",
    "Q30": "最想解决的问题帮助定制诊断方向",
    "Q31": "预约意愿反映企业行动力与线索质量",
    "Q2a": "成立年限反映企业成熟度", "Q2b": "团队人数影响执行能力",
    "Q3a": "年营收是市场选择的重要参考", "Q9": "市场选择原因帮助优化定位",
    "Q11": "产品优势是竞争分析的关键", "Q15": "交付稳定性影响客户信任",
    "Q22": "新媒体团队是出海获客的基础", "Q23": "海外社媒经验影响内容策略",
    "Q28": "外贸团队影响询盘承接能力",
}

_MISSING_ASKS: dict[str, str] = {
    "Q5": "目前海外订单或海外客户占比大概是多少？",
    "Q8": "接下来最想重点开发哪个海外市场？",
    "Q17": "你目前还考虑增加哪些出海方式？例如 TikTok Shop、海外短视频、B2B平台、独立站、展会等。",
    "Q19": "每月能接受的出海试错预算大概是多少？",
    "Q30": "最想让出海顾问帮你解决什么问题？",
    "Q31": "如果报告显示适合出海，是否愿意预约 1V1 咨询？",
    "Q2a": "公司成立多久了？", "Q2b": "目前团队大概多少人？",
    "Q3a": "过去一年营业额大约多少？", "Q9": "为什么选择这个市场？",
    "Q11": "产品最核心的优势是什么？", "Q15": "目前交付能力是否稳定？",
    "Q22": "有没有负责新媒体或短视频的人？", "Q23": "是否做过海外社媒或短视频？",
    "Q28": "目前外贸团队有几个人？",
}


def _check_set(answers: dict, ids: set[str], skip_q5: bool = True) -> list[MissingItem]:
    missing: list[MissingItem] = []
    for qid in ids:
        if skip_q5 and qid == "Q5":
            continue
        if qid not in answers or len(answers.get(qid, [])) == 0:
            missing.append(MissingItem(
                question_id=qid,
                label=_MISSING_LABELS.get(qid, qid),
                reason=_MISSING_REASONS.get(qid, "报告生成需要此项信息"),
                ask=_MISSING_ASKS.get(qid),
            ))
    return missing


def _count_valid(answers: dict) -> int:
    n = 0
    for q_id, selected in answers.items():
        if isinstance(selected, list) and len(selected) > 0:
            n += 1
    return n


def readiness_check_handler(
    inp: ReadinessCheckInput,
    ctx: ToolContext,
) -> ToolResult:
    # 分支判断
    if inp.branch is None or "Q5" not in inp.answers or len(inp.answers.get("Q5", [])) == 0:
        mi = MissingItem(question_id="Q5", label=_MISSING_LABELS["Q5"],
                         reason=_MISSING_REASONS["Q5"], ask=_MISSING_ASKS.get("Q5"))
        return ToolResult(data=ReadinessResult(
            ready=False, score_ready=False, report_ready=False,
            missing_items=[mi], next_questions=["请先确认企业是否有海外经验（Q5）"],
        ))

    if inp.branch == "inexperienced":
        return ToolResult(data=ReadinessResult(
            ready=False, score_ready=False, report_ready=False, unsupported_branch=True,
            next_questions=["深度诊断优先支持已有出海经验企业"],
        ))

    if inp.branch != "experienced":
        mi = MissingItem(question_id="branch", label="分支状态", reason="分支状态无效")
        return ToolResult(data=ReadinessResult(
            ready=False, score_ready=False, report_ready=False, missing_items=[mi],
        ))

    valid_answers = _count_valid(inp.answers)

    # score_ready check
    score_missing = _check_set(inp.answers, _SCORE_IDS)
    score_ready = len(score_missing) == 0 and valid_answers >= _MIN_ANSWERS

    # report_ready check
    report_missing = _check_set(inp.answers, _REPORT_EXTRA_IDS, skip_q5=False)
    report_ready = score_ready and len(report_missing) == 0

    if valid_answers < _MIN_ANSWERS:
        score_missing.append(MissingItem(
            question_id="answer_count", label="补充企业关键信息",
            reason=f"至少需要 {_MIN_ANSWERS} 个有效答案，当前仅 {valid_answers} 个",
        ))

    all_score_missing = score_missing

    if not score_ready:
        nq = [m.ask if m.ask else _MISSING_LABELS.get(m.question_id, m.question_id)
              for m in all_score_missing[:4]]
        return ToolResult(data=ReadinessResult(
            ready=False, score_ready=False, report_ready=False,
            missing_items=all_score_missing, report_missing_items=report_missing,
            next_questions=nq,
        ))

    # score_ready=True but report_ready may be False
    nq = [m.ask if m.ask else _MISSING_LABELS.get(m.question_id, m.question_id)
          for m in report_missing[:3]]
    return ToolResult(data=ReadinessResult(
        ready=True, score_ready=True, report_ready=report_ready,
        missing_items=[], report_missing_items=report_missing,
        next_questions=nq,
    ))
