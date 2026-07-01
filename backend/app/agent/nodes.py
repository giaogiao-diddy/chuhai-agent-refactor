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

    # 3. 分支判断
    new_state = decide_branch_from_q5(new_state)

    return new_state
