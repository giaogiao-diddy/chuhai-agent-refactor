from app.agent.extraction import extract_from_messages
from app.agent.prompts import OPENING_MESSAGE, SYSTEM_DIALOGUE
from app.agent.audit import audit_report_bundle
from app.agent.reporting import generate_raw_report
from app.agent.state_machine import (
    append_assistant_message,
    decide_branch_from_q5,
    is_ready_to_score,
    register_ai_failure,
    trim_message_history,
)
from app.reports.guard import assert_user_report_safe
from app.reports.splitter import split_report
from app.reports.template_report import build_template_raw_report
from app.schemas.audit import ReportAuditResult
from app.schemas.scoring import DimensionScore, ScoringResult
from app.schemas.agent_state import AgentState
from app.schemas.extraction import ExtractionResult
from app.schemas.llm import LLMMessage
from app.schemas.slots import SlotValue
from app.scoring.answer_scoring import build_scoring_input
from app.scoring.engine import calculate_scoring
from app.scoring.questionnaire import ALL_QUESTIONS
from app.services.deepseek_client import DeepSeekClient
from app.services.slot_engine import merge_slots


async def opening_node(state: AgentState) -> AgentState:
    new_state = state.model_copy(deep=True)
    if not new_state.messages:
        new_state = append_assistant_message(new_state, OPENING_MESSAGE)
    return new_state


def _last_message_is_user(state: AgentState) -> bool:
    if not state.messages:
        return False
    return state.messages[-1].role == "user"


async def dialogue_node(state: AgentState) -> AgentState:
    if not _last_message_is_user(state):
        return state.model_copy(deep=True)

    try:
        client = DeepSeekClient()
        recent = state.messages[-12:]
        llm_messages = [LLMMessage(role="system", content=SYSTEM_DIALOGUE)]
        for msg in recent:
            llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

        response = await client.chat(llm_messages, max_tokens=256, temperature=0.2)
        new_state = state.model_copy(deep=True)
        new_state = append_assistant_message(new_state, response.content)
        return new_state
    except Exception as e:
        return register_ai_failure(state, f"dialogue_node: {e}")


# ── 提取结果应用（纯函数）──────────────────────────────────────

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


async def extract_answers_node(state: AgentState) -> AgentState:
    try:
        extraction = await extract_from_messages(state.messages)
    except Exception as e:
        return register_ai_failure(state, f"extract_answers_node: {e}")

    return apply_extraction_result(state, extraction)


def score_node(state: AgentState) -> AgentState:
    new_state = state.model_copy(deep=True)

    if new_state.branch != "experienced":
        new_state.scoring_error = "当前仅支持 experienced 分支评分"
        new_state.validation_errors.append("score_node: 非 experienced 分支，跳过评分")
        return new_state

    if new_state.validation_errors:
        new_state.scoring_error = "存在 validation_errors，跳过评分"
        return new_state

    if not is_ready_to_score(new_state):
        new_state.scoring_error = "未满足评分条件（需 active + experienced + ≥8答案 + Q5 有效）"
        return new_state

    slots = new_state.slots
    try:
        si = build_scoring_input(
            new_state.answers,
            branch=new_state.branch,
            q1_slots=slots,
            company_name=slots.company_name.value if slots.company_name else None,
            industry=slots.industry.value if slots.industry else None,
            product=slots.main_product.value if slots.main_product else None,
            target_market=slots.target_market.value if slots.target_market else None,
        )
    except Exception as e:
        new_state.scoring_error = str(e)
        new_state.validation_errors.append(f"score_node: build_scoring_input 失败: {e}")
        return new_state

    try:
        result = calculate_scoring(si)
    except Exception as e:
        new_state.scoring_error = str(e)
        new_state.validation_errors.append(f"score_node: calculate_scoring 失败: {e}")
        return new_state

    new_state.scoring_result = result
    new_state.scoring_error = None
    new_state.status = "ready_to_score"
    return new_state


def _apply_template_fallback(new_state: AgentState, reason: str) -> AgentState:
    if new_state.scoring_result is None:
        new_state.scoring_result = ScoringResult(
            feasibility_score=0, lead_score=0, display_score=0,
            tag="观察准备型", tag_explanation="信息不足，使用模板报告",
            preliminary_judgment="信息不足", strengths=[], risks=[],
            dimension_scores=[
                DimensionScore(name=f"{d}_feasibility", raw_score=0, max_score=20, normalized_score=0)
                for d in ["enterprise_base","overseas_validation","product_supply_chain","path_clarity","content_fitness","conversion_readiness","action_readiness"]
            ] + [
                DimensionScore(name=f"{d}_lead", raw_score=0, max_score=20, normalized_score=0)
                for d in ["enterprise_base","overseas_validation","product_supply_chain","path_clarity","content_fitness","conversion_readiness","action_readiness"]
            ],
            lead_priority="P3",
        )
    try:
        raw = build_template_raw_report(new_state)
        bundle = split_report(raw, new_state)
        assert_user_report_safe(bundle.user_report)
        new_state.raw_report = bundle.raw_report
        new_state.user_report = bundle.user_report
        new_state.lead_report = bundle.lead_report
        new_state.used_template_report = True
        new_state.status = "completed"
        new_state.report_error = f"{reason}，已使用模板兜底"
        new_state.audit_result = ReportAuditResult(
            passed=True, issues=["使用模板兜底"], rewrite_required=False, severity="warning",
        )
    except Exception as e:
        new_state.status = "failed"
        new_state.report_error = f"模板兜底也失败: {e}"
    return new_state


async def report_node(state: AgentState) -> AgentState:
    new_state = state.model_copy(deep=True)
    new_state.raw_report = None
    new_state.user_report = None
    new_state.lead_report = None
    new_state.audit_result = None
    new_state.report_error = None
    new_state.used_template_report = False
    new_state.report_retry_count = 0

    # 无 scoring_result → 模板兜底
    if new_state.scoring_result is None:
        return _apply_template_fallback(new_state, "缺少 scoring_result")

    last_error = ""
    for _ in range(new_state.max_report_retries + 1):
        try:
            raw = await generate_raw_report(new_state)
            bundle = split_report(raw, new_state)
            assert_user_report_safe(bundle.user_report)
            audit = await audit_report_bundle(bundle)
            new_state.audit_result = audit

            if audit.passed and not audit.rewrite_required and audit.severity in ("pass", "warning"):
                new_state.raw_report = bundle.raw_report
                new_state.user_report = bundle.user_report
                new_state.lead_report = bundle.lead_report
                new_state.status = "completed"
                return new_state

            new_state.report_retry_count += 1
            last_error = "; ".join(audit.issues)
            new_state.report_error = f"审计未通过(第{new_state.report_retry_count}次): {last_error}"
        except Exception as e:
            new_state.report_retry_count += 1
            last_error = str(e)
            new_state.report_error = f"报告生成异常(第{new_state.report_retry_count}次): {last_error}"

    # 所有重试失败 → 模板兜底
    return _apply_template_fallback(new_state, last_error)


def trim_history_node(state: AgentState) -> AgentState:
    return trim_message_history(state, max_messages=12)
