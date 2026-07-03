from app.agent.state_machine import (
    decide_branch_from_q5,
)
from app.schemas.agent_state import AgentState
from app.schemas.extraction import ExtractionResult
from app.schemas.slots import SlotValue
from app.scoring.questionnaire import ALL_QUESTIONS
from app.services.slot_engine import merge_slots


def apply_extraction_result(
    state: AgentState,
    extraction: ExtractionResult,
    min_answer_confidence: float = 0.6,
) -> AgentState:
    new_state = state.model_copy(deep=True)

    # 1. 槽位合并：ExtractedSlot → SlotValue → merge_slots
    incoming_slots: dict[str, SlotValue] = {}
    for field_name, es in extraction.slots.items():
        if es is None:
            continue
        incoming_slots[field_name] = SlotValue(value=es.value, confidence=es.confidence)
    if incoming_slots:
        merged = merge_slots(new_state.slots, incoming_slots, min_confidence=0.6)
        new_state.slots = merged.slots
        if merged.low_confidence_fields:
            new_state.validation_errors.append(
                f"低置信槽位(未合并): {merged.low_confidence_fields}"
            )
        if merged.ignored_fields:
            new_state.validation_errors.append(
                f"忽略槽位: {merged.ignored_fields}"
            )

    # 2. answers 校验并入（含 confidence 过滤 + open_text 拒绝 + branch 隔离）
    q_map = {q.id: q for q in ALL_QUESTIONS}

    # 先推导 Q5 决定的分支，用于后续 branch 隔离判断
    q5_answers = [ea for ea in extraction.answers
                  if ea.question_id == "Q5" and ea.confidence >= min_answer_confidence]
    projected_branch = new_state.branch  # 可能已有 state 分支
    for ea in q5_answers:
        q = q_map.get(ea.question_id)
        if q and q.kind == "single_choice" and len(ea.option_ids) == 1:
            option = ea.option_ids[0]
            if option in ("A", "B", "C"):
                projected_branch = "experienced"
            elif option == "D":
                projected_branch = "inexperienced"

    for ea in extraction.answers:
        if ea.confidence < min_answer_confidence:
            new_state.validation_errors.append(
                f"低置信答案(未写入): {ea.question_id} confidence={ea.confidence}"
            )
            continue
        q = q_map.get(ea.question_id)
        if q is None:
            new_state.validation_errors.append(f"未知题号: {ea.question_id}")
            continue
        if q.kind == "open_text":
            new_state.validation_errors.append(f"开放题不允许进入 answers: {ea.question_id}")
            continue
        if projected_branch == "inexperienced" and q.branch == "experienced":
            new_state.validation_errors.append(
                f"分支不允许: {ea.question_id} 为 experienced 题，当前分支为 inexperienced"
            )
            continue
        valid_ids = {o.id for o in q.options}
        invalid = [oid for oid in ea.option_ids if oid not in valid_ids]
        if invalid:
            new_state.validation_errors.append(
                f"{ea.question_id} 无效选项: {invalid}"
            )
            continue
        if q.kind == "single_choice" and len(ea.option_ids) != 1:
            new_state.validation_errors.append(
                f"{ea.question_id} 是单选题，期望1个选项，实际{len(ea.option_ids)}"
            )
            continue
        new_state.answers[ea.question_id] = ea.option_ids

    # 2.5 Q30 意图确定性补丁：高频率出货/订单增长意图 → Q30 选项
    _apply_q30_intent_patch(new_state, extraction)

    # 3. 分支判断
    new_state = decide_branch_from_q5(new_state)

    return new_state


# ── Q30 intent patch ──

_Q30_INTENT_PATTERNS: dict[str, str] = {
    "出货": "A",     # 判断行业海外有没有机会 → 提高出货量属于市场机会判断
    "订单": "A",
    "客户": "D",     # 给到海外客户画像建议 → 获取客户属于客户画像
    "销量": "A",
    "转化": "A",
}


def _apply_q30_intent_patch(state: AgentState, extraction) -> None:
    """确定性补丁：当用户消息中出现高频率出货/获客意图，且 Q30 尚未被收集时，
    基于意图关键词自动写入 Q30 答案。仅 experienced 分支生效，不覆盖已有答案。
    选项映射以 questionnaire.py Q30 为准：
      A=判断行业海外有没有机会, B=判断哪个国家最适合先做,
      C=选出最适合出海的主推产品, D=给到海外客户画像建议,
      E=不确定，希望顾问帮我整体诊断
    """
    if "Q30" in state.answers:
        return
    branch = state.branch
    if branch == "inexperienced":
        return
    # 从最近消息和抽取文本中收集意图文本
    text_parts: list[str] = []
    for msg in state.messages[-4:]:
        text_parts.append(msg.content)
    if extraction and getattr(extraction, "reasoning_summary", None):
        text_parts.append(str(extraction.reasoning_summary))
    combined = " ".join(text_parts)

    matched_option: str | None = None
    for keyword, option_id in _Q30_INTENT_PATTERNS.items():
        if keyword in combined:
            matched_option = option_id
            break

    if matched_option:
        state.answers["Q30"] = [matched_option]
